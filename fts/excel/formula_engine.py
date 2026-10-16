"""A small Excel formula interpreter.

Why it exists: the student may not have Excel, and openpyxl cannot
calculate formulas. This engine evaluates the subset of Excel used in the
course (arithmetic, comparisons, SUM/SUMIFS/IF/IFERROR/XLOOKUP/INDEX/MATCH,
date and statistical functions) so the app can

* run the in-app "Formula Lab" exercises, and
* grade a practice workbook even if it was never opened in Excel.

It is not a full Excel implementation. Unsupported functions return
#NAME? and the student is told which function is unsupported.
"""
from __future__ import annotations

import datetime as _dt
import math
import re
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from ..core import metrics as _m

EXCEL_EPOCH = _dt.datetime(1899, 12, 30)


class ExcelError(Exception):
    """Excel error value (#DIV/0!, #N/A, ...). Used as a value, and raised
    internally to short-circuit evaluation."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail

    def __repr__(self):
        return self.code

    def __eq__(self, other):
        return isinstance(other, ExcelError) and other.code == self.code

    def __hash__(self):
        return hash(self.code)


DIV0, NA, VALUE, REF, NAME, NUM = "#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?", "#NUM!"


# ------------------------------------------------------------ references

def col_to_num(col: str) -> int:
    n = 0
    for ch in col.upper():
        n = n * 26 + ord(ch) - 64
    return n


def num_to_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


_CELL = r"\$?[A-Za-z]{1,3}\$?\d+"
_SHEET = r"(?:'[^']+'|[A-Za-z_][A-Za-z0-9_\.]*)!"
TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<string>"(?:[^"]|"")*")
  | (?P<ref>(?:%(sheet)s)?(?:%(cell)s(?::%(cell)s)?|\$?[A-Za-z]{1,3}:\$?[A-Za-z]{1,3}))(?![A-Za-z0-9_(])
  | (?P<number>\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)
  | (?P<func>[A-Za-z_][A-Za-z0-9_\.]*)\s*\(
  | (?P<bool>TRUE|FALSE|true|false)(?![A-Za-z0-9_(])
  | (?P<op><=|>=|<>|[-+*/^&=<>%%(),;:])
    """ % {"sheet": _SHEET, "cell": _CELL},
    re.VERBOSE,
)


@dataclass
class Tok:
    kind: str
    text: str
    pos: int


def tokenize(formula: str) -> list[Tok]:
    s = formula[1:] if formula.startswith("=") else formula
    out, i = [], 0
    while i < len(s):
        mt = TOKEN_RE.match(s, i)
        if not mt:
            raise ExcelError(NAME, f"Cannot read the formula near '{s[i:i + 10]}'.")
        kind = mt.lastgroup
        if kind != "ws":
            text = mt.group(kind)
            out.append(Tok(kind, text, i))
            if kind == "func":
                out.append(Tok("op", "(", mt.end() - 1))
        i = mt.end()
    return out


def shift_formula(formula: str, d_row: int, d_col: int) -> str:
    """Copy a formula d_row rows down / d_col columns right, the way Excel's
    fill handle does: relative parts move, $-anchored parts stay."""
    body = formula[1:] if formula.startswith("=") else formula

    def shift_cell(c: str) -> str:
        mt = re.match(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)", c)
        cabs, col, rabs, row = mt.groups()
        if not cabs:
            n = col_to_num(col) + d_col
            if n < 1:
                raise ExcelError(REF, "The copied reference moves off the sheet.")
            col = num_to_col(n)
        if not rabs:
            r = int(row) + d_row
            if r < 1:
                raise ExcelError(REF, "The copied reference moves off the sheet.")
            row = str(r)
        return f"{cabs}{col.upper()}{rabs}{row}"

    out = []
    for t in tokenize(body):
        if t.kind == "ref":
            sheet, ref = _split_sheet(t.text)
            parts = ref.split(":")
            if re.fullmatch(_CELL, parts[0]):
                parts = [shift_cell(p) for p in parts]
            out.append((sheet + "!" if sheet else "") + ":".join(parts))
        else:
            out.append(t.text)
    text = "".join(out)
    return "=" + text


def _split_sheet(ref: str) -> tuple[str | None, str]:
    if "!" in ref:
        sheet, r = ref.rsplit("!", 1)
        return sheet, r
    return None, ref


def _unquote_sheet(s: str | None) -> str | None:
    if s and s.startswith("'") and s.endswith("'"):
        return s[1:-1].replace("''", "'")
    return s


def parse_cell(ref: str) -> tuple[int, int]:
    mt = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", ref)
    if not mt:
        raise ExcelError(REF, f"'{ref}' is not a cell reference.")
    return int(mt.group(2)), col_to_num(mt.group(1))


class Range:
    """A rectangular block of already-evaluated values (rows x cols)."""

    def __init__(self, rows: list[list[Any]]):
        self.rows = rows

    @property
    def shape(self):
        return len(self.rows), (len(self.rows[0]) if self.rows else 0)

    def flat(self) -> list[Any]:
        return [v for r in self.rows for v in r]

    def vector(self) -> list[Any]:
        h, w = self.shape
        if h == 1:
            return list(self.rows[0])
        if w == 1:
            return [r[0] for r in self.rows]
        raise ExcelError(VALUE, "Expected a single row or column.")


# ---------------------------------------------------------------- parser

class Parser:
    """Recursive-descent parser producing a tiny AST of tuples."""

    def __init__(self, tokens: list[Tok]):
        self.t, self.i = tokens, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, text=None):
        tok = self.peek()
        if tok is None or (text is not None and tok.text != text):
            want = f"'{text}'" if text else "more input"
            raise ExcelError(NAME, f"Formula is incomplete: expected {want}.")
        self.i += 1
        return tok

    def parse(self):
        if not self.t:
            raise ExcelError(VALUE, "The formula is empty.")
        node = self.comparison()
        if self.peek() is not None:
            raise ExcelError(NAME, f"Unexpected '{self.peek().text}' in the formula. "
                                   "Check brackets and commas.")
        return node

    def comparison(self):
        node = self.concat()
        while self.peek() and self.peek().text in ("=", "<>", "<", ">", "<=", ">="):
            op = self.take().text
            node = ("bin", op, node, self.concat())
        return node

    def concat(self):
        node = self.additive()
        while self.peek() and self.peek().text == "&":
            self.take()
            node = ("bin", "&", node, self.additive())
        return node

    def additive(self):
        node = self.term()
        while self.peek() and self.peek().text in ("+", "-"):
            op = self.take().text
            node = ("bin", op, node, self.term())
        return node

    def term(self):
        node = self.power()
        while self.peek() and self.peek().text in ("*", "/"):
            op = self.take().text
            node = ("bin", op, node, self.power())
        return node

    def power(self):
        node = self.unary()
        while self.peek() and self.peek().text == "^":
            self.take()
            node = ("bin", "^", node, self.unary())
        return node

    def unary(self):
        if self.peek() and self.peek().text in ("-", "+"):
            op = self.take().text
            node = self.unary()
            return ("neg", node) if op == "-" else node
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while self.peek() and self.peek().text == "%":
            self.take()
            node = ("bin", "/", node, ("num", 100.0))
        return node

    def primary(self):
        tok = self.take()
        if tok.kind == "number":
            return ("num", float(tok.text))
        if tok.kind == "string":
            return ("str", tok.text[1:-1].replace('""', '"'))
        if tok.kind == "bool":
            return ("bool", tok.text.upper() == "TRUE")
        if tok.kind == "ref":
            return ("ref", tok.text)
        if tok.kind == "func":
            name = tok.text.upper()
            self.take("(")
            args = []
            if self.peek() and self.peek().text == ")":
                self.take(")")
                return ("func", name, args)
            while True:
                if self.peek() and self.peek().text in (",", ";"):
                    args.append(("missing",))
                else:
                    args.append(self.comparison())
                nxt = self.take()
                if nxt.text == ")":
                    break
                if nxt.text not in (",", ";"):
                    raise ExcelError(NAME, f"Expected ',' or ')' in {name}().")
            return ("func", name, args)
        if tok.text == "(":
            node = self.comparison()
            self.take(")")
            return node
        raise ExcelError(NAME, f"Unexpected '{tok.text}' in the formula.")


# -------------------------------------------------------------- engine

def to_serial(v):
    if isinstance(v, _dt.datetime):
        return (v - EXCEL_EPOCH).total_seconds() / 86400
    if isinstance(v, _dt.date):
        return float((_dt.datetime(v.year, v.month, v.day) - EXCEL_EPOCH).days)
    return v


def from_serial(n: float) -> _dt.date:
    return (EXCEL_EPOCH + _dt.timedelta(days=int(n))).date()


class Engine:
    """Evaluate formulas against a dict-based workbook:
    ``{sheet_name: {"A1": value_or_formula, ...}}``."""

    def __init__(self, sheets: dict[str, dict[str, Any]], default_sheet: str | None = None):
        self.sheets = {name: {k.upper(): v for k, v in cells.items()} for name, cells in sheets.items()}
        self.default_sheet = default_sheet or next(iter(self.sheets), "Sheet1")
        self._cache: dict[tuple[str, str], Any] = {}
        self._visiting: set[tuple[str, str]] = set()
        self.unsupported: set[str] = set()

    # --- public API
    def evaluate(self, formula: str, sheet: str | None = None) -> Any:
        """Evaluate a formula string; returns a value or an ExcelError."""
        sheet = sheet or self.default_sheet
        try:
            ast = Parser(tokenize(formula)).parse()
            val = self._eval(ast, sheet)
            if isinstance(val, Range):
                h, w = val.shape
                if (h, w) == (1, 1):
                    val = val.rows[0][0]
                else:
                    raise ExcelError(VALUE, "The formula returns a range, not a single value.")
            return 0.0 if val is None else val
        except ExcelError as e:
            return e
        except RecursionError:
            return ExcelError(REF, "The formula is too deeply nested or circular.")

    def cell_value(self, sheet: str, coord: str) -> Any:
        key = (sheet, coord.upper().replace("$", ""))
        if key in self._cache:
            return self._cache[key]
        if key in self._visiting:
            raise ExcelError(REF, f"Circular reference at {sheet}!{coord}.")
        if sheet not in self.sheets:
            raise ExcelError(REF, f"There is no sheet called '{sheet}'.")
        raw = self.sheets[sheet].get(key[1])
        if isinstance(raw, str) and raw.startswith("="):
            self._visiting.add(key)
            try:
                v = self.evaluate(raw, sheet)
            finally:
                self._visiting.discard(key)
        else:
            v = to_serial(raw)
        self._cache[key] = v
        return v

    def set_cell(self, sheet: str, coord: str, value: Any) -> None:
        self.sheets.setdefault(sheet, {})[coord.upper()] = value
        self._cache.clear()

    def max_row(self, sheet: str) -> int:
        rows = [parse_cell(c)[0] for c in self.sheets.get(sheet, {})]
        return max(rows) if rows else 1

    # --- internals
    def _range(self, ref: str, sheet: str) -> Range | Any:
        sh, r = _split_sheet(ref)
        sheet = _unquote_sheet(sh) or sheet
        if sheet not in self.sheets:
            raise ExcelError(REF, f"There is no sheet called '{sheet}'.")
        if ":" in r:
            a, b = r.split(":")
            if re.fullmatch(r"\$?[A-Za-z]{1,3}", a):     # whole columns, e.g. A:A
                r1, c1 = 1, col_to_num(a.replace("$", ""))
                r2, c2 = self.max_row(sheet), col_to_num(b.replace("$", ""))
            else:
                r1, c1 = parse_cell(a)
                r2, c2 = parse_cell(b)
            r1, r2 = sorted((r1, r2))
            c1, c2 = sorted((c1, c2))
            return Range([[self.cell_value(sheet, f"{num_to_col(c)}{rr}") for c in range(c1, c2 + 1)]
                          for rr in range(r1, r2 + 1)])
        return self.cell_value(sheet, r.replace("$", ""))

    def _eval(self, node, sheet):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "str":
            return node[1]
        if kind == "bool":
            return node[1]
        if kind == "missing":
            return None
        if kind == "ref":
            v = self._range(node[1], sheet)
            if isinstance(v, ExcelError):
                raise v
            return v
        if kind == "neg":
            return -_num(self._scalar(self._eval(node[1], sheet)))
        if kind == "bin":
            return self._binary(node[1], self._scalar(self._eval(node[2], sheet)),
                                self._scalar(self._eval(node[3], sheet)))
        if kind == "func":
            return self._call(node[1], node[2], sheet)
        raise ExcelError(VALUE)

    @staticmethod
    def _scalar(v):
        if isinstance(v, Range):
            h, w = v.shape
            if (h, w) == (1, 1):
                v = v.rows[0][0]
            else:
                raise ExcelError(VALUE, "A range was used where a single value was expected.")
        if isinstance(v, ExcelError):
            raise v
        return v

    @staticmethod
    def _binary(op, a, b):
        if op == "&":
            return _text(a) + _text(b)
        if op in ("=", "<>", "<", ">", "<=", ">="):
            x, y = _cmp_key(a), _cmp_key(b)
            if type(x) is not type(y):
                # Excel orders numbers < text < booleans
                order = {float: 0, str: 1, bool: 2}
                x, y = order[type(x)], order[type(y)]
            return {"=": x == y, "<>": x != y, "<": x < y, ">": x > y,
                    "<=": x <= y, ">=": x >= y}[op]
        a, b = _num(a), _num(b)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise ExcelError(DIV0, "Division by zero.")
            return a / b
        if op == "^":
            try:
                return a ** b
            except (OverflowError, ZeroDivisionError):
                raise ExcelError(NUM)
        raise ExcelError(VALUE)

    def _call(self, name, args, sheet):
        if name.startswith("_XLFN."):
            name = name[6:]
        if name in LAZY:
            return LAZY[name](self, args, sheet)
        fn = FUNCS.get(name)
        if fn is None:
            self.unsupported.add(name)
            raise ExcelError(NAME, f"The function {name}() is not supported in this training app.")
        vals = [self._eval(a, sheet) for a in args]
        return fn(*vals)


# ------------------------------------------------------------ coercion

def _num(v) -> float:
    if isinstance(v, ExcelError):
        raise v
    if v is None or v == "":
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (_dt.date, _dt.datetime)):
        return float(to_serial(v))
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise ExcelError(VALUE, f"'{v}' is text, not a number.")


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _cmp_key(v):
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return str(v).lower()


def _truthy(v) -> bool:
    if isinstance(v, str):
        if v.upper() in ("TRUE", "FALSE"):
            return v.upper() == "TRUE"
        raise ExcelError(VALUE, "IF needs a TRUE/FALSE test, not text.")
    return bool(_num(v))


def _numbers(args: Iterable, *, strict_scalars=True) -> list[float]:
    """Numbers from arguments the way SUM sees them: ranges contribute only
    numeric cells; typed scalars must be numbers."""
    out = []
    for a in args:
        if isinstance(a, Range):
            for v in a.flat():
                if isinstance(v, ExcelError):
                    raise v
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(float(v))
        elif a is None:
            continue
        else:
            out.append(_num(a))
    return out


def _as_range(v) -> Range:
    return v if isinstance(v, Range) else Range([[v]])


# ------------------------------------------------------------- criteria

def _criterion(crit) -> Callable[[Any], bool]:
    if isinstance(crit, Range):
        crit = crit.rows[0][0]
    if isinstance(crit, (int, float)) and not isinstance(crit, bool):
        return lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) == float(crit)
    s = _text(crit)
    mt = re.match(r"^(<=|>=|<>|<|>|=)?(.*)$", s, re.S)
    op, rhs = mt.group(1) or "=", mt.group(2)
    try:
        rnum = float(rhs)
        is_num = True
    except ValueError:
        is_num = False
    if is_num:
        def f(v):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return op == "<>"
            x = float(v)
            return {"=": x == rnum, "<>": x != rnum, "<": x < rnum, ">": x > rnum,
                    "<=": x <= rnum, ">=": x >= rnum}[op]
        return f
    pattern = "^" + re.escape(rhs.lower()).replace(r"\*", ".*").replace(r"\?", ".") + "$"
    rx = re.compile(pattern, re.S)

    def g(v):
        t = _text(v).lower()
        hit = bool(rx.match(t))
        if op == "=":
            return hit if rhs != "" else (v is None or v == "")
        if op == "<>":
            return not hit if rhs != "" else not (v is None or v == "")
        x, y = t, rhs.lower()
        return {"<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op]
    return g


def _ifs_mask(pairs) -> list[bool]:
    if len(pairs) % 2:
        raise ExcelError(VALUE, "Criteria must come in range/criterion pairs.")
    mask = None
    for rng, crit in zip(pairs[::2], pairs[1::2]):
        vals = _as_range(rng).flat()
        f = _criterion(crit)
        m = [f(v) for v in vals]
        if mask is None:
            mask = m
        elif len(m) != len(mask):
            raise ExcelError(VALUE, "All criteria ranges must be the same size.")
        else:
            mask = [a and b for a, b in zip(mask, m)]
    return mask or []


def f_sumifs(sum_range, *pairs):
    vals = _as_range(sum_range).flat()
    mask = _ifs_mask(pairs)
    if len(mask) != len(vals):
        raise ExcelError(VALUE, "Sum range and criteria range must be the same size.")
    return sum(float(v) for v, k in zip(vals, mask)
               if k and isinstance(v, (int, float)) and not isinstance(v, bool))


def f_sumif(rng, crit, sum_range=None):
    return f_sumifs(sum_range if sum_range is not None else rng, rng, crit)


def f_countifs(*pairs):
    return float(sum(_ifs_mask(pairs)))


def f_averageifs(avg_range, *pairs):
    vals = _as_range(avg_range).flat()
    mask = _ifs_mask(pairs)
    sel = [float(v) for v, k in zip(vals, mask) if k and isinstance(v, (int, float))]
    if not sel:
        raise ExcelError(DIV0, "No cells meet the criteria.")
    return sum(sel) / len(sel)


# ------------------------------------------------------------- lookups

def _find(value, vec, approximate=False):
    key = _cmp_key(value)
    if not approximate:
        for i, v in enumerate(vec):
            if v is None:
                continue
            k = _cmp_key(v)
            if type(k) is type(key) and k == key:
                return i
            if isinstance(key, str) and isinstance(k, str):
                rx = "^" + re.escape(key).replace(r"\*", ".*").replace(r"\?", ".") + "$"
                if re.match(rx, k):
                    return i
        raise ExcelError(NA, f"'{_text(value)}' was not found.")
    best = None
    for i, v in enumerate(vec):
        k = _cmp_key(v)
        if type(k) is type(key) and k <= key:
            best = i
        elif type(k) is type(key) and k > key:
            break
    if best is None:
        raise ExcelError(NA, f"No value less than or equal to '{_text(value)}'.")
    return best


def f_xlookup(value, lookup, ret, if_not_found=None, match_mode=None):
    lk = _as_range(lookup).vector()
    rr = _as_range(ret)
    try:
        i = _find(value, lk)
    except ExcelError:
        if if_not_found is not None:
            return if_not_found
        raise
    h, w = rr.shape
    return rr.rows[i][0] if w == 1 and h > 1 else rr.rows[0][i] if h == 1 else rr.rows[i][0]


def f_match(value, lookup, mtype=1.0):
    vec = _as_range(lookup).vector()
    mtype = 1.0 if mtype is None else _num(mtype)
    return float(_find(value, vec, approximate=(mtype == 1)) + 1)


def f_index(rng, row, col=None):
    r = _as_range(rng)
    h, w = r.shape
    row = int(_num(row)) if row is not None else 0
    col = int(_num(col)) if col is not None else 0
    if h == 1 and col == 0:
        row, col = 1, row
    if col == 0:
        col = 1
    if not (1 <= row <= h and 1 <= col <= w):
        raise ExcelError(REF, "INDEX position is outside the range.")
    return r.rows[row - 1][col - 1]


def f_vlookup(value, table, col, approx=True):
    t = _as_range(table)
    col = int(_num(col))
    if col < 1 or col > t.shape[1]:
        raise ExcelError(REF, "VLOOKUP column number is outside the table.")
    exact = approx is not None and not _truthy(approx)
    i = _find(value, [r[0] for r in t.rows], approximate=not exact)
    return t.rows[i][col - 1]


# -------------------------------------------------------- misc functions

def f_round(x, digits=0, mode="half"):
    x, d = _num(x), int(_num(digits))
    q = 10 ** d
    if mode == "up":
        return math.copysign(math.ceil(abs(x) * q - 1e-9) / q, x)
    if mode == "down":
        return math.copysign(math.floor(abs(x) * q + 1e-9) / q, x)
    return math.copysign(math.floor(abs(x) * q + 0.5 + 1e-9) / q, x)


def f_iferror_lazy(eng: Engine, args, sheet):
    if len(args) != 2:
        raise ExcelError(VALUE, "IFERROR needs 2 arguments.")
    try:
        v = eng._eval(args[0], sheet)
        if isinstance(v, Range) and v.shape == (1, 1):
            v = v.rows[0][0]
        if isinstance(v, ExcelError):
            raise v
        return v
    except ExcelError:
        return eng._eval(args[1], sheet)


def f_if_lazy(eng: Engine, args, sheet):
    if not 2 <= len(args) <= 3:
        raise ExcelError(VALUE, "IF needs 2 or 3 arguments.")
    test = eng._scalar(eng._eval(args[0], sheet))
    if _truthy(test):
        return eng._eval(args[1], sheet)
    return eng._eval(args[2], sheet) if len(args) == 3 else False


def f_date(y, mth, d):
    y, mth, d = int(_num(y)), int(_num(mth)), int(_num(d))
    y += (mth - 1) // 12
    mth = (mth - 1) % 12 + 1
    base = _dt.date(y, mth, 1) + _dt.timedelta(days=d - 1)
    return float(to_serial(base))


def f_eomonth(start, months):
    d = from_serial(_num(start))
    total = d.month - 1 + int(_num(months))
    y, mth = d.year + total // 12, total % 12 + 1
    nxt = _dt.date(y + (mth == 12), mth % 12 + 1, 1)
    return float(to_serial(nxt - _dt.timedelta(days=1)))


def f_weekday(serial, rtype=1):
    d = from_serial(_num(serial))
    rtype = 1 if rtype is None else int(_num(rtype))
    py = d.weekday()          # Mon=0
    if rtype == 1:
        return float((py + 1) % 7 + 1)   # Sun=1
    if rtype == 2:
        return float(py + 1)             # Mon=1
    if rtype == 3:
        return float(py)                 # Mon=0
    raise ExcelError(NUM)


def _avg(*a):
    n = _numbers(a)
    if not n:
        raise ExcelError(DIV0, "AVERAGE of no numbers.")
    return sum(n) / len(n)


def _stdev(*a):
    n = _numbers(a)
    if len(n) < 2:
        raise ExcelError(DIV0, "STDEV needs at least two numbers.")
    return statistics.stdev(n)


def _npv(rate, *a):
    return _m.excel_npv(_num(rate), _numbers(a))


def _irr(values, guess=None):
    r = _m.irr(_numbers([values]))
    if r is None:
        raise ExcelError(NUM, "IRR has no solution for these cash flows.")
    return r


def _sumproduct(*ranges):
    rs = [_as_range(r).flat() for r in ranges]
    if len({len(r) for r in rs}) != 1:
        raise ExcelError(VALUE, "SUMPRODUCT ranges must be the same size.")
    total = 0.0
    for vals in zip(*rs):
        p = 1.0
        for v in vals:
            p *= v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
        total += p
    return total


def _kth(fn):
    def inner(rng, k):
        vals = sorted(_numbers([rng]), reverse=(fn == "large"))
        k = int(_num(k))
        if not 1 <= k <= len(vals):
            raise ExcelError(NUM)
        return vals[k - 1]
    return inner


def _pmt(rate, nper, pv, fv=0, typ=0):
    rate, nper, pv = _num(rate), _num(nper), _num(pv)
    fv, typ = _num(fv or 0), _num(typ or 0)
    if rate == 0:
        return -(pv + fv) / nper
    f = (1 + rate) ** nper
    return -(rate * (pv * f + fv)) / ((1 + rate * typ) * (f - 1))


def _and(*a):
    vals = [v for x in a for v in (x.flat() if isinstance(x, Range) else [x]) if v is not None]
    return all(_truthy(v) for v in vals)


def _or(*a):
    vals = [v for x in a for v in (x.flat() if isinstance(x, Range) else [x]) if v is not None]
    return any(_truthy(v) for v in vals)


FUNCS: dict[str, Callable] = {
    "SUM": lambda *a: sum(_numbers(a)),
    "AVERAGE": _avg,
    "MIN": lambda *a: min(_numbers(a) or [0.0]),
    "MAX": lambda *a: max(_numbers(a) or [0.0]),
    "COUNT": lambda *a: float(len(_numbers(a))),
    "COUNTA": lambda *a: float(sum(1 for x in a for v in (_as_range(x).flat())
                                  if v is not None and v != "")),
    "MEDIAN": lambda *a: statistics.median(_numbers(a)),
    "STDEV": _stdev, "STDEV.S": _stdev,
    "LARGE": _kth("large"), "SMALL": _kth("small"),
    "ROUND": lambda x, d=0: f_round(x, d), "ROUNDUP": lambda x, d=0: f_round(x, d, "up"),
    "ROUNDDOWN": lambda x, d=0: f_round(x, d, "down"),
    "ABS": lambda x: abs(_num(x)),
    "SUMIF": f_sumif, "SUMIFS": f_sumifs, "COUNTIF": f_countifs, "COUNTIFS": f_countifs,
    "AVERAGEIFS": f_averageifs, "SUMPRODUCT": _sumproduct,
    "XLOOKUP": f_xlookup, "MATCH": f_match, "INDEX": f_index, "VLOOKUP": f_vlookup,
    "AND": _and, "OR": _or, "NOT": lambda x: not _truthy(x),
    "DATE": f_date, "YEAR": lambda s: float(from_serial(_num(s)).year),
    "MONTH": lambda s: float(from_serial(_num(s)).month),
    "DAY": lambda s: float(from_serial(_num(s)).day),
    "WEEKDAY": f_weekday, "EOMONTH": f_eomonth,
    "NPV": _npv, "IRR": _irr, "PMT": _pmt,
    "ISBLANK": lambda v: v is None or v == "",
    "ISNUMBER": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}
LAZY = {"IF": f_if_lazy, "IFERROR": f_iferror_lazy}


def functions_used(formula: str) -> set[str]:
    try:
        return {t.text.upper().replace("_XLFN.", "") for t in tokenize(formula) if t.kind == "func"}
    except ExcelError:
        return set()


def has_absolute_ref(formula: str) -> bool:
    try:
        return any(t.kind == "ref" and "$" in t.text for t in tokenize(formula))
    except ExcelError:
        return False


def display(v) -> str:
    if isinstance(v, ExcelError):
        return v.code
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if not v.is_integer() else f"{v:,.0f}"
    return "" if v is None else str(v)
