"""Modules 1-4: foundations, Excel, hotel revenue management, FP&A."""
from __future__ import annotations

import pandas as pd

from ..core import metrics as m
from ..core.checker import Mistake
from ..data import generator as gen
from ..data.loader import data
from .base import Exercise, Lesson, Module, PracticalTask, QuizQuestion as Q


def _row(r: pd.Series) -> pd.Series:
    """A DataFrame row upcasts room-night counts to float; restore ints so text shows 4,642 not 4,642.0."""
    return pd.Series({k: int(v) if "nights" in k and float(v).is_integer() else v for k, v in r.items()},
                     dtype=object, name=r.name)

def money(x, d=0):
    return f"-${abs(x):,.{d}f}" if x < 0 else f"${x:,.{d}f}"


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def _choices4(main: list[str], extra: list[str]) -> list[str]:
    out = list(dict.fromkeys(main))
    for e in extra:
        if len(out) >= 4:
            break
        if e not in out:
            out.append(e)
    return sorted(out)


def _pnl_total(line, col="actual", months=None):
    p = data().pnl
    if months:
        p = p[p.month.isin(months)]
    return float(p[p.line == line][col].sum())


# =================================================================== MODULE 1

def module1() -> Module:
    ds = data()
    rev = _pnl_total("Total revenue")
    ebitda = _pnl_total("EBITDA")
    ni = _pnl_total("Net income")
    pbt = _pnl_total("Profit before tax")
    bs = ds.balance_sheet.set_index("line")
    col = bs.columns[-1]
    assets = float(bs[bs.category == "Asset"][col].sum())
    liabs = float(bs[bs.category == "Liability"][col].sum())
    cf = dict(zip(ds.cash_flow.line, ds.cash_flow.iloc[:, 1]))
    r = ds.retail
    r_ni, r_dep = float(r.net_income.sum()), float(r.depreciation.sum())
    ar0, inv0, ap0 = 40_000.0, 90_000.0, 35_000.0
    ar1, inv1, ap1 = float(r.accounts_receivable.iloc[-1]), float(r.inventory.iloc[-1]), float(r.accounts_payable.iloc[-1])
    r_cfo = m.operating_cash_flow_indirect(r_ni, r_dep, ar1 - ar0, inv1 - inv0, ap1 - ap0)
    jan = r.iloc[0]
    terrace = ds.cases["rooftop_terrace"]
    t_cm = terrace["avg_spend_per_guest"] * (1 - terrace["variable_cost_pct"])
    t_be = m.break_even_units(terrace["monthly_fixed_costs"], terrace["avg_spend_per_guest"],
                              terrace["avg_spend_per_guest"] * terrace["variable_cost_pct"])

    l1 = Lesson(
        id="m1l1", title="The three financial statements",
        concept=f"""
## Three statements, three questions

| Statement | Question it answers | Key lines |
|---|---|---|
| **Income statement** (P&L) | Did we make a profit over the period? | Revenue, expenses, gross profit, EBITDA, operating profit, net profit |
| **Balance sheet** | What do we own and owe at one date? | Assets = Liabilities + Equity |
| **Cash flow statement** | Where did cash come from and go? | Operating, investing, financing cash flows |

**Revenue** is what customers are charged for goods and services delivered in the period.
**Expenses** are the costs of earning that revenue. **Profit = Revenue - Expenses.**

Profit has several levels. Each one answers a different management question:

* **Gross profit** = Revenue - Cost of sales. How profitable is the product itself?
* **EBITDA** = Earnings Before Interest, Tax, Depreciation and Amortisation. It shows how much the
  operation earns before financing and accounting write-downs. In hotels it is close to GOP less
  management fees and fixed charges.
* **Operating profit (EBIT)** = EBITDA - Depreciation and amortisation.
* **Net profit** = profit after interest and tax. This belongs to the owners.

**Assets** are resources the business controls (cash, receivables, buildings). **Liabilities** are
obligations (supplier invoices, loans). **Equity** is the owners' share: what is left after
liabilities. The balance sheet *always* balances because every transaction affects two sides.
""",
        worked_example=f"""
### Worked example: The Aurelia Grand Hotel, FY{gen.YEAR}

| | Amount |
|---|---|
| Total revenue | {money(rev)} |
| EBITDA | {money(ebitda)} |
| Net income | {money(ni)} |
| Cash from operating activities | {money(cf['Cash flow from operating activities'])} |

**Step 1: EBITDA margin** = EBITDA / Revenue = {money(ebitda)} / {money(rev)} = **{pct(ebitda / rev)}**.
About {round(ebitda / rev * 100)} cents of every revenue dollar is left after running the hotel.

**Step 2: Why is net income much lower?** Depreciation ({money(_pnl_total('Depreciation'))}) and interest
({money(_pnl_total('Interest'))}) sit below EBITDA. The hotel is capital-intensive and partly debt-funded.

**Step 3: Why is operating cash flow *higher* than net income?** Depreciation is an expense but not a cash
payment, so it is added back in the cash flow statement.
""",
        guided=Exercise(
            id="m1l1_g", skill="Financial statements",
            prompt=f"FY{gen.YEAR}: total revenue {money(rev)}, profit before tax {money(pbt)}. "
                   "Calculate the **pre-tax profit margin** (as a %).",
            steps=["Margin = profit / revenue.", "Use profit before tax, not EBITDA.",
                   "Convert the decimal to a percentage."],
            expected=pbt / rev, unit="percent",
            hints=["Divide profit before tax by total revenue.",
                   f"{money(pbt)} / {money(rev)} = ?"],
            mistakes=[Mistake(ebitda / rev, "You used EBITDA. The question asks for profit before tax, "
                                            "which is after depreciation and interest."),
                      Mistake(ni / rev, "You used net income (after tax). Use profit before tax.")],
            solution=f"{money(pbt)} / {money(rev)} = {pct(pbt / rev, 2)}"),
        independent=[
            Exercise(
                id="m1l1_i1", skill="Financial statements",
                prompt=f"At 31 Dec {gen.YEAR} the hotel's total assets are {money(assets)} and total "
                       f"liabilities are {money(liabs)}. What is total **equity**?",
                expected=assets - liabs, unit="currency",
                hints=["Assets = Liabilities + Equity. Rearrange it.", "Equity = Assets - Liabilities."],
                mistakes=[Mistake(assets + liabs, "You added. Equity is what is LEFT after liabilities, "
                                                  "so subtract.")],
                solution=f"{money(assets)} - {money(liabs)} = {money(assets - liabs)}"),
            Exercise(
                id="m1l1_i2", skill="Financial statements",
                prompt="A department has revenue of $800,000, cost of sales of $260,000, operating expenses "
                       "(excluding depreciation) of $310,000 and depreciation of $45,000. What is "
                       "**operating profit (EBIT)**?",
                expected=800_000 - 260_000 - 310_000 - 45_000, unit="currency",
                hints=["Gross profit first: revenue - cost of sales.",
                       "EBITDA = gross profit - operating expenses. Then subtract depreciation."],
                mistakes=[Mistake(230_000, "That is EBITDA. Operating profit (EBIT) is after depreciation."),
                          Mistake(540_000, "That is gross profit. Keep going down the P&L.")],
                solution="Gross profit 540,000 - opex 310,000 = EBITDA 230,000 - depreciation 45,000 = "
                         "EBIT $185,000", practical=False),
        ],
        interpretation="""
**What management does with this:** owners look at net income and cash. General managers are judged
on GOP and EBITDA because they control operations but not financing. Lenders watch cash flow
because loans are repaid in cash, not profit. When you present numbers, say which profit level
you mean. "Profit is up" means little until you say which line.
""",
        quiz=[
            Q("m1q1", "Which statement shows the company's position at a single date?",
              ["Income statement", "Balance sheet", "Cash flow statement", "Budget"], 1,
              "The balance sheet is a snapshot at one date. The other two cover a period.",
              "Financial statements"),
            Q("m1q2", "EBITDA is profit before which items?",
              ["Cost of sales and payroll", "Interest, tax, depreciation and amortisation",
               "Revenue and discounts", "Dividends only"], 1,
              "The name says it: Earnings Before Interest, Tax, Depreciation and Amortisation.",
              "Financial statements"),
            Q("m1q3", "A hotel buys a $40,000 kitchen oven with cash. Immediately after, total assets...",
              ["Fall by $40,000", "Rise by $40,000", "Do not change", "Double"], 2,
              "Cash (an asset) falls and equipment (an asset) rises by the same amount. "
              "Nothing hits the P&L until the oven is depreciated.", "Financial statements"),
        ],
        task=PracticalTask(
            "m1t1", "Explain the year in five sentences",
            "Using the FY figures above, write five sentences for a non-finance general manager: one on "
            "revenue, one on EBITDA, one on net income, one on cash, and one on what to watch next year.",
            "1. Revenue: ...\n2. EBITDA: ...\n3. Net income: ...\n4. Cash: ...\n5. Watch next year: ...",
            ["Uses the correct profit level in each sentence", "Quotes at least three numbers",
             "Avoids jargon or explains it", "Ends with an action or a watch-point"]),
    )

    l2 = Lesson(
        id="m1l2", title="Profit vs cash, cost behaviour and break-even",
        concept="""
## Accrual vs cash accounting
Under **accrual accounting** (used by almost every company) revenue is recorded when it is *earned*
and expenses when they are *incurred*, not when cash moves. So a profitable business can run out
of cash:

* Customers who have not paid yet create **accounts receivable**. That is profit without cash.
* Stock bought but not yet sold sits in **inventory**. That is cash out with no expense yet.
* Supplier bills not yet paid create **accounts payable**. That is an expense without cash out yet.

**Working capital** = Receivables + Inventory - Payables. When it *grows*, cash is tied up.

Operating cash flow (indirect method):
`Net income + Depreciation - Increase in receivables - Increase in inventory + Increase in payables`

The **cash conversion cycle** = DSO + DIO - DPO (days). It measures how long cash is tied up.

## Fixed vs variable costs
* **Variable costs** move with volume: laundry per occupied room, food cost per cover, OTA commission.
* **Fixed costs** do not change with volume in the short term: salaried staff, insurance, rent.

**Contribution margin** = Price - Variable cost per unit. Each unit sold *contributes* this amount
toward covering fixed costs. **Break-even units** = Fixed costs / Contribution per unit.
""",
        worked_example=f"""
### Worked example: {gen.RETAIL_NAME} (fictional retailer), January

| | January |
|---|---|
| Net income | {money(jan.net_income)} |
| Depreciation (added back) | {money(jan.depreciation)} |
| Increase in receivables | {money(jan.accounts_receivable - ar0)} |
| Increase in inventory | {money(jan.inventory - inv0)} |
| Change in payables | {money(jan.accounts_payable - ap0)} |
| **Operating cash flow** | **{money(jan.operating_cash_flow)}** |

The retailer made a profit but **lost cash**. It built stock for new stores, and customers paid more
slowly. Payables also fell, so it paid suppliers faster. The P&L looks healthy while the bank
balance shrinks.
""",
        guided=Exercise(
            id="m1l2_g", skill="Financial statements", practical=True,
            prompt=f"{gen.RETAIL_NAME}, full year: net income {money(r_ni)}, depreciation {money(r_dep)}. "
                   f"Receivables rose from {money(ar0)} to {money(ar1)}, inventory from {money(inv0)} to "
                   f"{money(inv1)}, payables changed from {money(ap0)} to {money(ap1)}. "
                   "Calculate **operating cash flow** for the year.",
            steps=[f"Start with net income {money(r_ni)} and add back depreciation {money(r_dep)}.",
                   f"Subtract the increase in receivables ({money(ar1 - ar0)}) and inventory ({money(inv1 - inv0)}).",
                   f"Add the change in payables ({money(ap1 - ap0)}). A decrease is negative."],
            expected=r_cfo, unit="currency",
            hints=["Increases in receivables and inventory USE cash, so subtract them.",
                   "Payables fell, so the change is negative. Adding a negative number reduces cash."],
            mistakes=[Mistake(r_ni + r_dep - (ar1 - ar0) - (inv1 - inv0) - (ap1 - ap0),
                              "Payables went DOWN. A fall in payables uses cash, so add the (negative) "
                              "change instead of subtracting it."),
                      Mistake(r_ni - (ar1 - ar0) - (inv1 - inv0) + (ap1 - ap0),
                              "You forgot to add back depreciation, which is a non-cash expense.")],
            solution=f"{money(r_ni)} + {money(r_dep)} - {money(ar1 - ar0)} - {money(inv1 - inv0)} "
                     f"+ ({money(ap1 - ap0)}) = {money(r_cfo)}"),
        independent=[
            Exercise(
                id="m1l2_i1", skill="Cost behaviour & break-even",
                prompt=f"{terrace['name']}: average spend {money(terrace['avg_spend_per_guest'])} per guest, "
                       f"variable costs {pct(terrace['variable_cost_pct'], 0)} of spend, fixed costs "
                       f"{money(terrace['monthly_fixed_costs'])} per month. How many guests per month are "
                       "needed to **break even**? (Answer to 1 decimal place.)",
                expected=t_be, unit="number", abs_tol=0.6,
                hints=["Contribution per guest = spend x (1 - variable cost %).",
                       f"Contribution = {money(t_cm, 2)}. Now divide fixed costs by it."],
                mistakes=[Mistake(terrace["monthly_fixed_costs"] / terrace["avg_spend_per_guest"],
                                  "You divided by the price. Divide by the contribution per guest, "
                                  "because variable costs must be covered first.")],
                solution=f"{money(terrace['monthly_fixed_costs'])} / {money(t_cm, 2)} = {t_be:,.1f} guests. "
                         "In practice you would plan for 650."),
            Exercise(
                id="m1l2_i2", skill="Financial statements",
                prompt="A supplier business has DSO of 42 days, DIO of 35 days and DPO of 30 days. "
                       "What is its **cash conversion cycle** in days?",
                expected=m.cash_conversion_cycle(42, 35, 30), unit="number",
                hints=["CCC = DSO + DIO - DPO.", "Paying suppliers later (DPO) shortens the cycle."],
                mistakes=[Mistake(107, "You added DPO. Paying suppliers later *reduces* the cycle, so subtract it.")],
                solution="42 + 35 - 30 = 47 days"),
        ],
        interpretation="""
**What management does with this:** if profit is fine but cash is falling, look at working capital.
Chase overdue customers (lower DSO), cut slow-moving stock (lower DIO) and agree better payment
terms (higher DPO). For pricing and staffing decisions, separate fixed from variable costs. Only
variable costs change with the decision, and the contribution margin tells you how fast extra
volume turns into profit.
""",
        quiz=[
            Q("m1q4", "Profit is rising but the bank balance is falling. The MOST likely cause is...",
              ["Depreciation increased", "Receivables and inventory are growing",
               "The tax rate fell", "Revenue was recognised too late"], 1,
              "Growing receivables and inventory tie up cash, even though the sales already count as profit.",
              "Financial statements"),
            Q("m1q5", "Which hotel cost is usually VARIABLE?",
              ["General manager salary", "Property insurance", "Guest amenities per occupied room",
               "Property tax"], 2, "Amenities are consumed per occupied room, so they move with volume.",
              "Cost behaviour & break-even"),
            Q("m1q6", "Price $50, variable cost $30, fixed costs $10,000. Break-even units = ",
              ["200", "333", "500", "1,000"], 2, "Contribution is $20, and 10,000 / 20 = 500 units.",
              "Cost behaviour & break-even"),
        ],
        task=PracticalTask(
            "m1t2", "Why profit is not cash: retailer memo",
            f"Open the retailer data (datasets/retail_harbor_lane_2025.csv, also summarised above). Write a "
            "short memo to the owner explaining why the year's profit is higher than the cash generated, "
            "naming the two biggest causes with numbers and proposing two actions.",
            "To: Owner, Harbor Lane Outfitters\nSubject: Profit vs cash\n\nProfit for the year: ...\n"
            "Cash generated from operations: ...\nMain causes:\n1. ...\n2. ...\nRecommended actions:\n1. ...\n2. ...",
            ["States both profit and operating cash flow", "Identifies inventory build as the largest cause",
             "Mentions slower customer payments (receivables)", "Actions are specific and measurable"]),
    )
    return Module("m1", 1, "Financial Foundations",
                  "Read the three statements, understand profit levels, cash vs profit, cost behaviour "
                  "and break-even.", ["Financial statements", "Cost behaviour & break-even"], [l1, l2],
                  tools=["calculator"])


# =================================================================== MODULE 2

def module2() -> Module:
    l1 = Lesson(
        id="m2l1", title="Formulas, references and model structure",
        concept="""
## How a good model is laid out
Professional models separate four blocks, usually on separate sheets:

1. **Inputs / raw data**: numbers you receive (night audit, P&L export). Never edited by formulas.
2. **Assumptions**: numbers you choose (growth %, rate change, elasticity). Coloured as inputs.
3. **Calculations**: formulas only, no typed numbers.
4. **Outputs**: summary tables, charts and checks for management.

## References
* **Relative** `B2`: when copied one row down it becomes `B3`.
* **Absolute** `$B$2`: never changes when copied. Use it for a single assumption cell or a fixed total.
* **Mixed** `B$2` / `$B2`: locks only the row or only the column. This is useful in two-way tables.

Press **F4** in Excel to cycle through `B2 -> $B$2 -> B$2 -> $B2`.

## Core functions
| Function | What it does | Example |
|---|---|---|
| `SUM` | adds a range | `=SUM(E2:E32)` |
| `SUMIFS` | adds rows meeting conditions | `=SUMIFS(F:F, C:C, "Weekend")` |
| `IF` | chooses between two results | `=IF(D8<B2,"Below","OK")` |
| `IFERROR` | replaces an error with a value | `=IFERROR(D6/D5, 0)` |
| `AVERAGE`, `MIN`, `MAX`, `COUNTIFS` | basic statistics | `=COUNTIFS(E:E, ">=130")` |
""",
        worked_example="""
### Worked example: occupancy column copied down

Raw data has Rooms Sold in column E and Rooms Available in column D. In F2 type `=E2/D2` and copy it
down. Each row divides its own sold by its own available, so relative references are correct here.

Now suppose every row should be divided by the **hotel's fixed 150 rooms** in `Assumptions!B2`.
`=E2/Assumptions!B2` copied down becomes `=E3/Assumptions!B3`, which points at the wrong
(empty) cell and gives **#DIV/0!**. The fix is `=E2/Assumptions!$B$2`.
""",
        guided=Exercise(
            id="m2l1_g", skill="Excel formulas", unit="choice",
            prompt="Cell C2 contains `=B2*$F$1`. You copy it to **C5**. Which formula appears in C5?",
            choices=["=B5*$F$1", "=B5*$F$4", "=B2*$F$1", "=E5*$F$1"], expected=0,
            steps=["Count how many rows you moved: 2 to 5 is 3 rows down.",
                   "Relative parts (B2) move 3 rows. Parts with $ stay put."],
            hints=["Only the part without $ signs moves.", "B2 moves to B5. $F$1 is anchored."],
            solution="=B5*$F$1. The relative B2 moved 3 rows down and the absolute $F$1 stayed fixed."),
        independent=[
            Exercise(
                id="m2l1_i1", skill="Excel formulas",
                prompt="Table: rows (Day type, Revenue): Weekday 12,000 · Weekend 18,500 · Weekday 11,400 · "
                       "Weekend 19,200 · Weekday 10,900. What does "
                       "`=SUMIFS(Revenue, DayType, \"Weekend\")` return?",
                expected=18_500 + 19_200, unit="currency",
                hints=["SUMIFS adds only the rows where the condition is true.",
                       "Add the two weekend values."],
                mistakes=[Mistake(12_000 + 11_400 + 10_900, "You added the weekday rows. The criterion is \"Weekend\"."),
                          Mistake(72_000, "You added every row. SUMIFS filters first.")],
                solution="18,500 + 19,200 = 37,700"),
            Exercise(
                id="m2l1_i2", skill="Excel formulas", unit="choice",
                prompt="D5 (rooms sold) is 0 and D6 (revenue) is 0. What does `=IFERROR(D6/D5,\"n/a\")` show?",
                choices=["0", "#DIV/0!", "n/a", "FALSE"], expected=2,
                hints=["Dividing by zero is an error in Excel.", "IFERROR returns its second argument when there is an error."],
                solution="D6/D5 is #DIV/0!, so IFERROR returns \"n/a\". That is the right display: ADR is "
                         "undefined when nothing is sold, which is not the same as $0."),
            Exercise(
                id="m2l1_i3", skill="Excel formulas", unit="choice",
                prompt="You want to copy `=C4*B1` across a row so that C4 moves but B1 stays fixed. "
                       "The best version is:",
                choices=["=$C$4*B1", "=C4*$B$1", "=C$4*B$1", "=C4*B1"], expected=1,
                hints=["Lock the cell that must not move.", "$B$1 never changes when copied."],
                solution="=C4*$B$1"),
        ],
        interpretation="""
**Why it matters at work:** managers trust models that are easy to audit. Typed numbers inside
formulas ("hard-codes") are the most common cause of wrong forecasts, because when an assumption
changes, the hard-code does not. Keep inputs in one place, colour them, and use references
everywhere else. In interviews you may be asked to explain the difference between `$B$2` and `B2`.
Use the occupancy example above.
""",
        quiz=[
            Q("m2q1", "Which reference stays exactly the same when copied anywhere?",
              ["B2", "$B2", "B$2", "$B$2"], 3, "Both column and row are anchored.", "Excel formulas"),
            Q("m2q2", "Where should a growth-rate assumption live in a well-built model?",
              ["Typed inside each formula", "In a labelled assumptions cell referenced by formulas",
               "In a chart title", "In the raw data sheet"], 1,
              "One input cell, referenced everywhere, makes the model easy to update and audit.",
              "Excel formulas"),
            Q("m2q3", "=SUMIFS(F:F, C:C, \"Weekend\", E:E, \">=130\") adds revenue for nights that are...",
              ["Weekend OR at least 130 sold", "Weekend AND at least 130 sold",
               "Only weekdays", "Every night"], 1, "SUMIFS criteria must ALL be true.", "Excel formulas"),
        ],
        task=PracticalTask(
            "m2t1", "Complete the Excel practice workbook (tasks 1-9)",
            "Open the Excel Workbook Center, create the practice workbook and complete tasks 1-9 in Excel "
            "(or in the in-app Formula Lab if you do not have Excel). Grade your work and note below any "
            "task you got wrong and what you learned from the feedback.",
            "Tasks completed: ...\nMistakes I made and the fix:\n- ...\nOne thing I will remember about references: ...",
            ["All of tasks 1-9 graded", "Each mistake has a written fix", "Uses cell references, not typed numbers"],
            tool="excel_center"),
    )

    l2 = Lesson(
        id="m2l2", title="Lookups, dates, checks and sensitivity tables",
        concept="""
## Lookups
* `XLOOKUP(value, lookup_range, return_range, [if_not_found])` is the modern choice (Excel 2021/365).
* `INDEX(return_range, MATCH(value, lookup_range, 0))` works in every Excel version.
  The `0` means **exact match**. Forget it and MATCH may return a wrong row silently.

## Dates
`DATE(y,m,d)`, `YEAR()`, `MONTH()`, `EOMONTH(date, 0)` (last day of month), `WEEKDAY(date, 2)`
(Mon=1 ... Sun=7). Dates are stored as serial numbers, so `end - start` gives days.

## Data quality and error checking
* **Data validation** restricts inputs (e.g. rate change between -30% and +30%, or a drop-down list).
* **Conditional formatting** highlights exceptions (variances over 5%, occupancy over 95%).
* **Check cells**: e.g. `=ROUND(SUM(monthly) - annual, 2) = 0` should show TRUE. A model with failing
  checks must not be sent to management.

## Scenarios and sensitivity
A **scenario** changes several assumptions together (Base / Upside / Downside). A **sensitivity
table** changes one or two inputs over a range to show how the output responds. Example: RevPAR for
occupancy 70-85% x ADR $400-480.
""",
        worked_example="""
### Worked example: two-way sensitivity of RevPAR

RevPAR = Occupancy x ADR. Build a grid with occupancy down the rows (A3:A5) and ADR across the top
(B2:D2). In B3 type `=$A3*B$2`: the column is locked for occupancy and the row is locked for ADR.
Copy it across and down.

| Occ \\ ADR | $400 | $440 | $480 |
|---|---|---|---|
| 70% | 280 | 308 | 336 |
| 77% | 308 | 338.8 | 369.6 |
| 85% | 340 | 374 | 408 |

Reading it: +7 points of occupancy is worth about the same as +$40 ADR at this level.
""",
        guided=Exercise(
            id="m2l2_g", skill="Excel formulas",
            prompt="In the sensitivity table above, what RevPAR appears for **82% occupancy and $455 ADR**?",
            steps=["RevPAR = Occupancy x ADR.", "Use 0.82 for 82%."],
            expected=0.82 * 455, unit="currency",
            hints=["0.82 x 455"], mistakes=[Mistake(82 * 455, "Use 0.82, not 82.")],
            solution="0.82 x $455 = $373.10"),
        independent=[
            Exercise(
                id="m2l2_i1", skill="Excel formulas", unit="choice",
                prompt="Budget table: A2:A13 = month names (Jan..Dec), C2:C13 = budget ADR. Which formula "
                       "returns March's budget ADR in ANY Excel version?",
                choices=["=INDEX(C2:C13, MATCH(\"Mar\", A2:A13, 0))", "=MATCH(\"Mar\", C2:C13, 0)",
                         "=INDEX(A2:A13, 3)", "=SUMIFS(A2:A13, C2:C13, \"Mar\")"], expected=0,
                hints=["MATCH finds the position; INDEX returns the value at that position."],
                solution="=INDEX(C2:C13, MATCH(\"Mar\", A2:A13, 0))"),
            Exercise(
                id="m2l2_i2", skill="Excel formulas",
                prompt="Cell A2 holds the date 14-Feb-2025. What number does `=DAY(EOMONTH(A2,0))` return?",
                expected=28, unit="number",
                hints=["EOMONTH(date, 0) returns the last day of the same month.", "2025 is not a leap year."],
                mistakes=[Mistake(14, "That is DAY(A2). EOMONTH moves to the month end first."),
                          Mistake(29, "2025 is not a leap year."), Mistake(31, "That's March. Use offset 0.")],
                solution="EOMONTH gives 28-Feb-2025, so DAY returns 28."),
            Exercise(
                id="m2l2_i3", skill="Excel formulas",
                prompt="A check cell holds `=ROUND(SUM(B2:B13)-B14,2)`. Months B2:B13 add up to 1,204,377.40 and "
                       "the annual total in B14 is 1,204,737.40. What does the check show?",
                expected=1_204_377.40 - 1_204_737.40, unit="currency",
                hints=["Sum of months minus the annual figure.", "A non-zero result means the model is broken. "
                                                                  "Here it looks like a transposition (73 vs 37)."],
                solution="1,204,377.40 - 1,204,737.40 = -360.00. The check fails because the annual total was "
                         "keyed with transposed digits."),
        ],
        interpretation="""
**Why it matters at work:** lookups connect budgets, actuals and mappings, and a wrong lookup
(missing the `0` for exact match) is a classic silent error. Sensitivity tables are how analysts answer
"what if?" quickly in meetings. Check cells are what make a reviewer trust your file.
""",
        quiz=[
            Q("m2q4", "What does the 0 in MATCH(\"Mar\", A2:A13, 0) do?",
              ["Starts at row 0", "Requires an exact match", "Returns 0 if not found", "Sorts the range"], 1,
              "0 = exact match. Without it MATCH assumes sorted data and can return a wrong row.",
              "Excel formulas"),
            Q("m2q5", "A model's balance check shows FALSE. You should...",
              ["Send it anyway with a note", "Delete the check", "Find and fix the error before sending",
               "Change the check to always TRUE"], 2, "Checks exist to stop errors reaching decision-makers.",
              "Excel formulas"),
            Q("m2q6", "A scenario differs from a one-way sensitivity because it...",
              ["Changes several related assumptions together", "Uses no formulas",
               "Always shows the worst case", "Only works in Excel 365"], 0,
              "A downside scenario might lower occupancy AND ADR AND raise costs at the same time.",
              "Forecasting & modelling"),
        ],
        task=PracticalTask(
            "m2t2", "Finish the workbook: lookups, flags and fill-down (tasks 10-16)",
            "Complete tasks 10-16 of the practice workbook (Excel or the Formula Lab), including the "
            "fill-down task with absolute references. Grade it, then describe the rate scenario result in task 15 "
            "in one sentence a manager would understand.",
            "Tasks 10-16 status: ...\nTask 15 in plain English: If we raise rates by 5% ...\nWhat the $ signs did in task 16: ...",
            ["Workbook grading shows tasks 10-16 attempted", "Task 15 explained without jargon",
             "Absolute reference explained correctly"], tool="excel_center"),
    )
    return Module("m2", 2, "Excel and Financial Modeling",
                  "Formulas, references, SUMIFS, lookups, dates, validation, checks, scenarios and "
                  "sensitivity, with a graded practice workbook.", ["Excel formulas"], [l1, l2],
                  tools=["excel_center"])


# =================================================================== MODULE 3

def module3() -> Module:
    ds = data()
    mr = ds.monthly_rooms.set_index("month_name")
    rb = ds.rooms_budget.set_index("month_name")
    mar, octo = _row(mr.loc["Mar"]), _row(mr.loc["Oct"])
    mar_occ = m.occupancy(mar.sold_room_nights, mar.available_room_nights)
    mar_adr = m.adr(mar.room_revenue, mar.sold_room_nights)
    mar_revpar = m.revpar(mar.room_revenue, mar.available_room_nights)
    oct_var = m.variance(octo.room_revenue, rb.loc["Oct"].budget_room_revenue)
    ch = ds.channels
    ota = ch[(ch.month == 10) & (ch.channel == "OTA")].iloc[0]
    ota_net_adr = (ota.room_revenue - ota.commission_cost) / ota.room_nights
    pace = ds.pace
    pickup = (pace.ly_actual_sold - pace.ly_on_the_books_same_time)
    fc_rooms = (pace.on_the_books + pickup).clip(upper=pace.rooms_available)
    fc_total = int(fc_rooms.sum())
    fc_rev = float((fc_rooms * pace.otb_adr).sum())
    base_occ, base_adr, new_adr, el = 0.80, 430.0, 430.0 * 1.08, -1.2
    new_occ = m.demand_at_rate(base_occ, base_adr, new_adr, el)
    new_revpar = new_occ * new_adr
    issues = ds.daily_issues
    q4 = ds.monthly_rooms[ds.monthly_rooms.month >= 9]
    q4b = ds.rooms_budget[ds.rooms_budget.month >= 9]

    l1 = Lesson(
        id="m3l1", title="Occupancy, ADR and RevPAR",
        concept="""
## The three core hotel KPIs

| KPI | Formula | Plain English |
|---|---|---|
| **Available room nights** | Rooms x days - out-of-order | How many nights we *could* sell |
| **Occupancy %** | Sold room nights / Available room nights | How full we were |
| **ADR** (Average Daily Rate) | Room revenue / Sold room nights | Average price per sold room |
| **RevPAR** (Revenue per Available Room) | Room revenue / Available room nights | Revenue per room we *had*, sold or not |

**RevPAR = Occupancy x ADR.** It combines volume and price, which is why revenue managers watch it most.

### Edge cases you must handle
* **Zero rooms sold**: occupancy 0% and RevPAR $0, but **ADR is undefined (n/a)**, *not* $0. Averaging
  a $0 ADR into a month would wrongly pull the rate down.
* **Zero available rooms** (hotel closed): all three are undefined. Exclude the day; don't count it as 0%.
* **Missing observation**: never treat blank as zero. Flag it and recover it from the source (night audit).
* **Cancellations / no-shows**: KPIs use rooms actually *sold* (consumed), not gross bookings.
* **Monthly ADR is NOT the average of daily ADRs.** Always divide total revenue by total rooms.
""",
        worked_example=f"""
### Worked example: The Aurelia Grand, March {gen.YEAR}

* Available room nights: {mar.available_room_nights:,} (150 rooms x 31 nights - out-of-order)
* Sold room nights: {mar.sold_room_nights:,}
* Room revenue: {money(mar.room_revenue, 2)}

1. Occupancy = {mar.sold_room_nights:,} / {mar.available_room_nights:,} = **{pct(mar_occ, 2)}**
2. ADR = {money(mar.room_revenue, 2)} / {mar.sold_room_nights:,} = **{money(mar_adr, 2)}**
3. RevPAR = {money(mar.room_revenue, 2)} / {mar.available_room_nights:,} = **{money(mar_revpar, 2)}**
4. Check: {pct(mar_occ, 2)} x {money(mar_adr, 2)} = {money(mar_occ * mar_adr, 2)}. It matches.
""",
        guided=Exercise(
            id="m3l1_g", skill="Hotel KPIs", practical=True,
            prompt=f"October {gen.YEAR}: available room nights {octo.available_room_nights:,}, sold "
                   f"{octo.sold_room_nights:,}, room revenue {money(octo.room_revenue, 2)}. "
                   "Calculate October **RevPAR**.",
            steps=["Identify the denominator: RevPAR uses AVAILABLE room nights.",
                   "Divide room revenue by available room nights.",
                   "Optional check: occupancy x ADR should give the same number."],
            expected=m.revpar(octo.room_revenue, octo.available_room_nights), unit="currency",
            hints=["RevPAR = Room revenue / Available room nights.",
                   f"{money(octo.room_revenue, 2)} / {octo.available_room_nights:,}"],
            mistakes=[Mistake(m.adr(octo.room_revenue, octo.sold_room_nights),
                              "That's ADR (divided by SOLD rooms). RevPAR divides by AVAILABLE rooms.")],
            solution=f"{money(octo.room_revenue, 2)} / {octo.available_room_nights:,} = "
                     f"{money(m.revpar(octo.room_revenue, octo.available_room_nights), 2)}"),
        independent=[
            Exercise(
                id="m3l1_i1", skill="Hotel KPIs", practical=True,
                prompt=f"Using the October numbers above, calculate **occupancy %**.",
                expected=m.occupancy(octo.sold_room_nights, octo.available_room_nights), unit="percent",
                hints=["Sold / available."],
                mistakes=[Mistake(octo.sold_room_nights / (150 * 31),
                                  "You used 150 x 31. Available room nights already exclude out-of-order rooms.")],
                solution=f"{octo.sold_room_nights:,} / {octo.available_room_nights:,} = "
                         f"{pct(m.occupancy(octo.sold_room_nights, octo.available_room_nights), 2)}"),
            Exercise(
                id="m3l1_i2", skill="Hotel KPIs", practical=True,
                prompt=f"Budgeted October room revenue was {money(rb.loc['Oct'].budget_room_revenue, 2)}. "
                       "What is the room revenue **variance** (Actual - Budget)?",
                expected=oct_var.amount, unit="currency",
                hints=["Actual minus budget. Revenue below budget gives a negative (unfavorable) variance."],
                solution=f"{money(octo.room_revenue, 2)} - {money(rb.loc['Oct'].budget_room_revenue, 2)} = "
                         f"{money(oct_var.amount, 2)} ({pct(oct_var.percent)}), unfavorable."),
            Exercise(
                id="m3l1_i3", skill="Hotel KPIs", unit="choice",
                prompt=f"On {issues.iloc[18].date} the property management system was down and the night audit "
                       "shows 0 rooms sold and $0 revenue with 150+ rooms available. What ADR should the report show?",
                choices=["$0.00", "n/a (undefined)", "The month's average ADR", "Yesterday's ADR"], expected=1,
                hints=["ADR divides by rooms SOLD. What is anything divided by zero?"],
                solution="ADR is undefined when nothing is sold, so show n/a. Occupancy (0%) and RevPAR ($0) "
                         "are still valid. Never fill in another day's ADR."),
        ],
        interpretation="""
**What management does with this:** if occupancy is high but ADR is low, the hotel may be
under-pricing: raise rates on peak nights. If ADR is high but occupancy low, the price may be
too high for the demand, or the problem may be distribution. RevPAR shows the combined result,
so a RevPAR gap to budget always needs splitting into an occupancy part and a rate part. Module 4
shows how.
""",
        quiz=[
            Q("m3q1", "150 rooms, 120 sold, room revenue $48,000. RevPAR is...",
              ["$400", "$320", "$480", "$300"], 1, "48,000 / 150 = $320. (ADR would be 48,000 / 120 = $400.)",
              "Hotel KPIs"),
            Q("m3q2", "Monthly ADR should be calculated as...",
              ["Average of the daily ADRs", "Total room revenue / total sold room nights",
               "RevPAR / 30", "Highest daily rate"], 1,
              "Averaging daily ADRs gives every day equal weight regardless of rooms sold.", "Hotel KPIs"),
            Q("m3q3", "Occupancy rose from 70% to 77% and ADR fell from $440 to $400. RevPAR...",
              ["Rose", "Fell", "Stayed the same", "Cannot be calculated"], 2,
              "0.70 x $440 = $308 and 0.77 x $400 = $308. Volume gains exactly offset the lower rate. "
              "Profit may still fall, because more occupied rooms means more variable cost.", "Hotel KPIs"),
        ],
        task=PracticalTask(
            "m3t1", "Monthly KPI table and commentary",
            "Open the Hotel Revenue Management simulator, review the monthly KPI table for the year and write "
            "a three-line commentary: best month by RevPAR, weakest month vs budget, and the main driver "
            "(occupancy or ADR) of the weakest month.",
            "Best RevPAR month: ... (RevPAR $...)\nWeakest vs budget: ... (variance $...)\nMain driver: occupancy / ADR because ...",
            ["Uses RevPAR, not revenue alone, to compare months", "Quantifies the variance",
             "Separates occupancy from rate"], tool="rm_simulator"),
    )
    q4_var = float(q4.room_revenue.sum() - q4b.budget_room_revenue.sum())
    l2 = Lesson(
        id="m3l2", title="Demand, segments, channels, pricing and forecasting",
        concept="""
## Demand patterns
* **Weekday vs weekend**: city luxury hotels sell weekdays to *corporate* guests and weekends to
  *leisure* guests. They are different customers with different price sensitivity.
* **Segments** describe *who* the guest is (Corporate, Transient/individual leisure, Group, Leisure package).
* **Channels** describe *how* they booked (Direct, OTA, GDS, Wholesale). Each channel has a cost.
  **Net ADR** = (Revenue - Commission) / Rooms. A $450 OTA room at 18% commission nets $369.

## Booking pace and pickup forecasting
**On the books (OTB)** = rooms already reserved for a future night. **Pace** compares OTB today with
OTB at the same point last year. A simple, widely used forecast is the **pickup method**:

`Forecast rooms = OTB today + (Last year final - Last year OTB at same days out)`, capped at capacity.

## Price and demand
Raising rates usually reduces rooms sold. **Price elasticity** is the % change in rooms for a 1% price
change. With elasticity -1.2, a +8% rate costs about 9% of volume. This app's simulator uses the
constant-elasticity curve `Occ_new = Occ_base x (Rate_new / Rate_base)^elasticity`. It is a teaching
simplification. Real elasticity differs by night, segment and competitor prices, and it is uncertain.
""",
        worked_example=f"""
### Worked example: why did room revenue fall in Sep-Dec?

Sep-Dec room revenue was {money(q4.room_revenue.sum())} against a budget of
{money(q4b.budget_room_revenue.sum())}, a gap of **{money(q4_var)}**. Breaking it down with the data:

1. **Weekday occupancy fell** while weekends held. The weekday pattern points to corporate demand.
2. **Segment mix**: corporate room nights fell, and transient business moved to **OTAs** at lower rates.
3. **Channel cost**: October OTA room nights were {ota.room_nights:,} vs
   {int(ch[(ch.month == 3) & (ch.channel == 'OTA')].room_nights.iloc[0]):,} in March, so commissions rose
   (an unfavorable expense variance in *Rooms other expenses*).

Root cause: lost corporate demand, partly replaced by expensive, lower-rated OTA business.
""",
        guided=Exercise(
            id="m3l2_g", skill="Revenue management decisions", practical=True,
            prompt=f"October OTA: {ota.room_nights:,} room nights, revenue {money(ota.room_revenue, 2)}, "
                   f"commission {pct(ota.commission_rate, 0)} ({money(ota.commission_cost, 2)}). "
                   "Calculate the OTA **net ADR** after commission.",
            steps=["Gross revenue minus commission = net revenue.",
                   "Divide net revenue by room nights."],
            expected=ota_net_adr, unit="currency",
            hints=["(Revenue - commission) / room nights"],
            mistakes=[Mistake(ota.room_revenue / ota.room_nights, "That is gross ADR. Deduct commission first.")],
            solution=f"({money(ota.room_revenue, 2)} - {money(ota.commission_cost, 2)}) / {ota.room_nights:,} "
                     f"= {money(ota_net_adr, 2)}"),
        independent=[
            Exercise(
                id="m3l2_i1", skill="Revenue management decisions", practical=True,
                prompt="Booking pace for 1-30 January next year (see the RM simulator, 'Pace & forecast' tab, or "
                       "datasets/hotel_booking_pace_jan2026.csv). Using the **pickup method** "
                       "(OTB + last-year pickup, capped at 150 per night), how many room nights are forecast "
                       f"in total? (Total on the books today: {int(pace.on_the_books.sum()):,}; total last-year "
                       f"pickup: {int(pickup.sum()):,}.)",
                expected=fc_total, unit="number", abs_tol=0.5,
                hints=["Per night: OTB + (LY actual - LY OTB). Then cap at 150.",
                       "If no night hits the 150 cap, the total is simply total OTB + total pickup."],
                solution=f"Sum of nightly min(150, OTB + pickup) = {fc_total:,} room nights."),
            Exercise(
                id="m3l2_i2", skill="Revenue management decisions", practical=True,
                prompt="Using each night's forecast rooms x that night's OTB ADR, what is the forecast "
                       "**room revenue** for the 30 nights? (Use the simulator's pace table.)",
                expected=fc_rev, unit="currency", rel_tol=0.002,
                hints=["Revenue per night = forecast rooms x OTB ADR. Add up the 30 nights.",
                       "The simulator shows this total under the pace table, but try it yourself first."],
                solution=f"Sum over nights of forecast rooms x OTB ADR = {money(fc_rev, 2)}. "
                         "This is an estimate; actual pickup may differ from last year."),
            Exercise(
                id="m3l2_i3", skill="Revenue management decisions",
                prompt=f"Base: occupancy {pct(base_occ, 0)}, ADR {money(base_adr)}. You raise the rate by 8% "
                       f"and demand elasticity is {el}. Using Occ_new = Occ x (1.08)^{el}, what is the new **RevPAR**?",
                expected=new_revpar, unit="currency",
                hints=[f"New ADR = {money(base_adr)} x 1.08.", "New occupancy = 0.80 x 1.08^-1.2.",
                       "RevPAR = new occupancy x new ADR."],
                mistakes=[Mistake(base_occ * new_adr, "You raised the price but kept occupancy at 80%. Demand responds to price.")],
                solution=f"Occ = 0.80 x 1.08^-1.2 = {pct(new_occ, 2)}; ADR = {money(new_adr, 2)}; "
                         f"RevPAR = {money(new_revpar, 2)} vs {money(base_occ * base_adr, 2)} before. "
                         "RevPAR falls slightly, but fewer occupied rooms also means lower variable cost."),
            Exercise(
                id="m3l2_i4", skill="Revenue management decisions", unit="choice",
                prompt="Which statement best explains the Sep-Dec room revenue shortfall in the data?",
                choices=["A hotel-wide fall in weekend leisure demand",
                         "Weaker weekday corporate demand, with transient business shifting to OTAs at lower rates",
                         "Too many rooms out of order", "A data error in the budget"], expected=1,
                hints=["Compare weekday and weekend occupancy before and after September.",
                       "Look at the channel table: which channel grew?"],
                solution="Weekday (corporate) occupancy fell; OTA share and discounting rose. Weekends held up."),
        ],
        interpretation="""
**What management does with this:** pace behind last year is an early warning. Act weeks ahead,
not on the day. Options are targeted promotions for weak *weekday* dates, corporate sales calls,
moving share from OTAs to direct (e.g. member rates), and holding rate on strong weekends. Any
pricing recommendation must state its risks: elasticity is an estimate, competitors may react, and
discounting can train guests to wait for deals.
""",
        quiz=[
            Q("m3q4", "OTB for next Tuesday is 90 rooms. Last year OTB at the same point was 95 and final was 120. "
                      "Pickup forecast = ", ["90", "115", "120", "125"], 1, "90 + (120 - 95) = 115.",
              "Revenue management decisions"),
            Q("m3q5", "A segment is ___, a channel is ___.",
              ["how they booked; who the guest is", "who the guest is; how they booked",
               "the room type; the rate code", "the same thing; the same thing"], 1,
              "Segments describe the guest (corporate, group); channels describe the booking route (OTA, direct).",
              "Revenue management decisions"),
            Q("m3q6", "Which is the most responsible way to present a 30-day revenue forecast?",
              ["As a guaranteed number", "With its method, key assumption and a range",
               "Only as a chart", "Rounded to the nearest million"], 1,
              "Forecasts are estimates. Show the method, the main assumption and a sensible range.",
              "Forecasting & modelling"),
        ],
        task=PracticalTask(
            "m3t2", "January pricing recommendation",
            "Use the RM simulator (rate scenarios and pace & forecast tabs). Recommend one pricing action for "
            "January next year, quantify its expected effect on RevPAR, and list two risks.",
            "Recommendation: ...\nEvidence (pace vs last year): ...\nExpected effect: RevPAR from $... to $...\n"
            "Risks:\n1. ...\n2. ...\nHow we will monitor it: ...",
            ["Recommendation is specific (dates/segment/rate)", "Uses pace data as evidence",
             "Quantifies impact with the simulator", "States at least two risks"], tool="rm_simulator"),
    )
    return Module("m3", 3, "Hotel Revenue Management",
                  "Occupancy, ADR, RevPAR, edge cases, segmentation, channels, booking pace, pricing "
                  "and a 30-day forecast for a 150-room hotel.",
                  ["Hotel KPIs", "Revenue management decisions"], [l1, l2], tools=["rm_simulator"])


# =================================================================== MODULE 4

def module4() -> Module:
    ds = data()
    p = ds.pnl
    fy = p.groupby("line", sort=False)[["actual", "budget", "line_type"]].agg(
        {"actual": "sum", "budget": "sum", "line_type": "first"})
    var = {ln: m.variance(r.actual, r.budget, "revenue" if r.line_type == "revenue" else "expense")
           for ln, r in fy.iterrows() if r.line_type in ("revenue", "expense")}
    top3 = m.top_unfavorable(var, 3)
    roe = var["Rooms other expenses"]
    mr = _row(ds.monthly_rooms.set_index("month_name").loc["Oct"])
    rb = _row(ds.rooms_budget.set_index("month_name").loc["Oct"])
    pv = m.price_volume_split(mr.sold_room_nights, mr.room_revenue / mr.sold_room_nights,
                              rb.budget_sold_room_nights, rb.budget_adr)
    pay = ds.payroll
    q4_budget = float(ds.rooms_budget[ds.rooms_budget.month >= 10].budget_room_revenue.sum())

    l1 = Lesson(
        id="m4l1", title="Budgets, variances and flexible budgets",
        concept="""
## Budget, forecast, actual
* **Annual budget**: the plan agreed before the year starts, usually by month. It is the target.
* **Forecast**: the latest best estimate of where the year will land. It is updated monthly or quarterly.
* **Actual**: what happened.

## Variance analysis
**Variance = Actual - Budget.** Whether that is good depends on the line:

| Line type | Actual above budget | Actual below budget |
|---|---|---|
| Revenue | Favorable (F) | Unfavorable (U) |
| Expense | Unfavorable (U) | Favorable (F) |

**Variance %** = Variance / Budget. Report both: $ shows size, % shows how unusual it is.

## Flexible budget
A static budget compares costs at *different* activity levels. If the hotel sold fewer rooms, variable
costs *should* be lower. A **flexible budget** restates the budget at the actual volume:
`Flexible budget = Fixed cost + Variable cost per unit x Actual units`.
The remaining variance (Actual - Flexible budget) is the true **spending (efficiency) variance**.

## Price-volume split of revenue
* **Volume effect** = (Actual units - Budget units) x Budget price
* **Price (rate) effect** = (Actual price - Budget price) x Actual units
* Together they equal the total revenue variance.
""",
        worked_example=f"""
### Worked example: October rooms revenue

| | Actual | Budget |
|---|---|---|
| Sold room nights | {mr.sold_room_nights:,} | {rb.budget_sold_room_nights:,} |
| ADR | {money(mr.room_revenue / mr.sold_room_nights, 2)} | {money(rb.budget_adr, 2)} |
| Room revenue | {money(mr.room_revenue, 2)} | {money(rb.budget_room_revenue, 2)} |

* Volume effect = ({mr.sold_room_nights:,} - {rb.budget_sold_room_nights:,}) x {money(rb.budget_adr, 2)} = **{money(pv['volume'], 2)}**
* Rate effect = ({money(mr.room_revenue / mr.sold_room_nights, 2)} - {money(rb.budget_adr, 2)}) x {mr.sold_room_nights:,} = **{money(pv['price'], 2)}**
* Total = **{money(pv['total'], 2)}**, which matches Actual - Budget.

Story: most of the shortfall is **volume** (rooms not sold), plus a smaller rate effect.
""",
        guided=Exercise(
            id="m4l1_g", skill="Budgeting & variance analysis", practical=True,
            prompt=f"FY *Rooms other expenses* (amenities, laundry, commissions): actual {money(roe.actual)}, "
                   f"budget {money(roe.budget)}. Calculate the **variance %**.",
            steps=["Variance = Actual - Budget.", "Variance % = Variance / Budget.",
                   "For an expense, positive = overspend = Unfavorable."],
            expected=roe.percent, unit="percent",
            hints=[f"({money(roe.actual)} - {money(roe.budget)}) / {money(roe.budget)}"],
            mistakes=[Mistake(-roe.percent, "Sign reversed: it's Actual - Budget."),
                      Mistake((roe.actual - roe.budget) / roe.actual, "Divide by BUDGET, not actual.")],
            solution=f"{money(roe.amount)} / {money(roe.budget)} = {pct(roe.percent, 2)}. Unfavorable: "
                     "costs above plan, mainly OTA commissions."),
        independent=[
            Exercise(
                id="m4l1_i1", skill="Budgeting & variance analysis", unit="choice", practical=True,
                prompt="Use the FP&A Lab's variance table (full year). Which line has the **largest unfavorable "
                       "variance** in dollars?",
                choices=_choices4([k for k, _ in top3], ["Utilities", "Insurance", "Sales & marketing"]),
                expected=_choices4([k for k, _ in top3], ["Utilities", "Insurance", "Sales & marketing"]).index(top3[0][0]),
                hints=["Revenue below budget is unfavorable; expenses above budget are unfavorable.",
                       "Compare absolute dollar amounts, not %."],
                solution=f"{top3[0][0]}: {money(top3[0][1].amount)}. The top 3 are "
                         + ", ".join(f"{k} ({money(v.amount)})" for k, v in top3) + "."),
            Exercise(
                id="m4l1_i2", skill="Budgeting & variance analysis",
                prompt="Housekeeping budget: fixed $42,000 per month + $9.50 per occupied room. Budget volume "
                       "3,900 rooms; actual 3,600 rooms; actual cost $78,900. What is the **flexible budget** "
                       "cost at actual volume?",
                expected=m.flexible_budget(42_000, 9.5, 3_600), unit="currency",
                hints=["Use ACTUAL rooms in the flexible budget.", "42,000 + 9.50 x 3,600"],
                mistakes=[Mistake(m.flexible_budget(42_000, 9.5, 3_900), "That is the static budget (3,900 rooms). "
                                                                       "Flex to the actual 3,600.")],
                solution="42,000 + 9.50 x 3,600 = $76,200. Actual $78,900 is $2,700 Unfavorable vs flexible "
                         "budget. The static budget ($79,050) would wrongly show it as favorable."),
            Exercise(
                id="m4l1_i3", skill="Budgeting & variance analysis",
                prompt="Using the October worked example, a manager asks: how much of the revenue gap is due to "
                       "**rate** (ADR)? Give the rate effect in dollars.",
                expected=pv["price"], unit="currency",
                hints=["(Actual ADR - Budget ADR) x ACTUAL rooms."],
                mistakes=[Mistake((mr.room_revenue / mr.sold_room_nights - rb.budget_adr) * rb.budget_sold_room_nights,
                                  "Multiply by ACTUAL rooms, otherwise volume and rate won't add up to the total.")],
                solution=f"Rate effect = {money(pv['price'], 2)}"),
        ],
        interpretation="""
**What management does with this:** variance commentary should answer *why* and *what next*, not
just repeat the numbers. A good line reads: "Rooms other expenses $X U (+Y%): OTA commissions up
because corporate weekday demand fell and was replaced by OTA business. Action: shift share back to
direct with a member rate; target commission ratio below Z%." Always flex variable costs before
judging a department manager.
""",
        quiz=[
            Q("m4q1", "Payroll: actual $510k, budget $480k. The variance is...",
              ["$30k Favorable", "$30k Unfavorable", "-$30k Favorable", "6.25% Favorable"], 1,
              "Expense above budget = unfavorable. 30 / 480 = 6.25% U.", "Budgeting & variance analysis"),
            Q("m4q2", "Why use a flexible budget?",
              ["To make the budget easier to hit", "To compare costs at the same activity level",
               "To remove fixed costs", "Because auditors require it"], 1,
              "Variable costs should move with volume; flexing isolates real over- or under-spending.",
              "Budgeting & variance analysis"),
            Q("m4q3", "Volume effect + price effect = ",
              ["Budget revenue", "Actual revenue", "Total revenue variance", "Flexible budget"], 2,
              "The split explains the whole variance.", "Budgeting & variance analysis"),
        ],
        task=PracticalTask(
            "m4t1", "Top three unfavorable variances",
            "In the FP&A Lab, open the full-year variance table. For each of the three largest unfavorable "
            "variances write: amount, %, the driver (with evidence) and one action.",
            "1. Line: ... Variance: $... (..%) Driver: ... Action: ...\n2. ...\n3. ...",
            ["Correct three lines identified", "Each has a data-based driver", "Each has a practical action"],
            tool="fpa_lab"),
    )

    rooms_pay = pay[(pay.department == "Rooms") & (pay.month == 7)].iloc[0]
    jul_pay = rooms_pay.headcount_actual * rooms_pay.avg_cost_per_fte_actual + rooms_pay.overtime_hours_actual * gen.OT_RATE
    l2 = Lesson(
        id="m4l2", title="Payroll, revised forecasts and management reporting",
        concept=f"""
## Payroll forecasting
Payroll is usually a hotel's largest cost. Forecast it from its drivers:
`Payroll = Headcount (FTE) x Average cost per FTE + Overtime hours x Overtime rate`.
Variable departments (Rooms, F&B, Spa) flex headcount with occupancy; support departments are
mostly fixed. Watch **overtime**: it is a symptom of vacancies or poor scheduling.

## Building a 12-month operating budget
1. Volume drivers: rooms available, occupancy and ADR by month (seasonality).
2. Revenue: rooms revenue, plus F&B and other revenue per occupied room.
3. Costs: variable costs per occupied room or % of revenue; fixed costs per month; payroll by department.
4. Totals: GOP, EBITDA and checks (12 months add up to the year).

## Revised forecast after a shock
When demand drops unexpectedly, keep the months already closed as **actual**, re-forecast the
remaining months from the new demand level, and **flex variable costs** with it. Fixed costs do not
fall automatically. That is why profit drops faster than revenue (**operating leverage**).

## One-page management report
Headline (one sentence) → KPI table (actual, budget, variance) → 3 key variances with drivers →
outlook and risks → recommended actions. Lead with the answer.
""",
        worked_example=f"""
### Worked example: July Rooms payroll

Rooms department, July actual: {rooms_pay.headcount_actual} FTE x {money(rooms_pay.avg_cost_per_fte_actual, 2)}
+ {rooms_pay.overtime_hours_actual} overtime hours x {money(gen.OT_RATE, 2)} = **{money(jul_pay, 2)}**.
Budget assumed {rooms_pay.overtime_hours_budget} overtime hours. Overtime almost doubled because of
housekeeping vacancies. Filling two vacancies would cost less than the overtime premium.
""",
        guided=Exercise(
            id="m4l2_g", skill="Budgeting & variance analysis", practical=True,
            prompt="Forecast next month's F&B payroll: 57 FTE at an average $3,950 per month, plus 340 "
                   f"overtime hours at {money(gen.OT_RATE, 2)}/hour.",
            steps=["Base pay = FTE x average cost.", "Overtime = hours x rate.", "Add them."],
            expected=57 * 3950 + 340 * gen.OT_RATE, unit="currency",
            hints=["57 x 3,950 = 225,150", f"340 x {gen.OT_RATE:.0f} = {340 * gen.OT_RATE:,.0f}"],
            mistakes=[Mistake(57 * 3950, "You forgot overtime.")],
            solution=f"225,150 + {340 * gen.OT_RATE:,.0f} = {money(57 * 3950 + 340 * gen.OT_RATE)}"),
        independent=[
            Exercise(
                id="m4l2_i1", skill="Forecasting & modelling", practical=True,
                prompt=f"Budgeted room revenue for Oct-Dec is {money(q4_budget, 2)}. At the end of September "
                       "you expect demand to be **12% below budget** for those three months, at budget rates. "
                       "What is the revised Oct-Dec room revenue forecast?",
                expected=q4_budget * 0.88, unit="currency",
                hints=["Revised = budget x (1 - 12%)."],
                mistakes=[Mistake(q4_budget * 0.12, "That's the reduction, not the revised forecast.")],
                solution=f"{money(q4_budget, 2)} x 0.88 = {money(q4_budget * 0.88, 2)}"),
            Exercise(
                id="m4l2_i2", skill="Forecasting & modelling",
                prompt="A department has revenue $1,000,000, variable costs 40% of revenue and fixed costs $350,000. "
                       "If revenue falls 10%, by what **% does profit fall**?",
                expected=((1_000_000 - 400_000 - 350_000) - (900_000 - 360_000 - 350_000)) / (1_000_000 - 400_000 - 350_000),
                unit="percent",
                hints=["Profit before: 1,000,000 - 400,000 - 350,000.",
                       "After: revenue 900,000, variable costs 40% of that, fixed unchanged."],
                mistakes=[Mistake(0.10, "Profit does not fall by the same % as revenue, because fixed costs don't flex.")],
                solution="Before $250,000; after $190,000; fall $60,000 = 24%. That's operating leverage."),
        ],
        interpretation="""
**What management does with this:** a revised forecast is only useful if it triggers action, such as
freezing vacant roles, cutting overtime, reducing variable spend or launching demand-generation.
The management report should make the decision easy: one headline, a few numbers, clear causes,
and specific actions with owners.
""",
        quiz=[
            Q("m4q4", "Which month should stay as ACTUAL in a revised forecast prepared at the end of September?",
              ["October", "September", "December", "None"], 1,
              "Closed months use actuals; only remaining months are re-forecast.", "Forecasting & modelling"),
            Q("m4q5", "The best first line of a management report is...",
              ["A list of every variance", "A one-sentence headline answering 'how did we do and why'",
               "The methodology", "The appendix"], 1, "Lead with the answer.", "Management reporting"),
            Q("m4q6", "Overtime hours doubled while headcount is below budget. The most likely fix is...",
              ["Raise ADR", "Fill vacancies / improve scheduling", "Cut fixed charges", "Ignore it"], 1,
              "Overtime premium usually costs more than filling the role.", "Budgeting & variance analysis"),
        ],
        task=PracticalTask(
            "m4t2", "Revised forecast and one-page management report",
            "In the FP&A Lab: (1) review the 12-month budget, (2) apply a demand decline from October and "
            "export the revised forecast, (3) export the one-page management report and edit its commentary "
            "below.", "Headline: ...\nKPIs vs budget: ...\nKey variances:\n1. ...\n2. ...\n3. ...\n"
                      "Revised outlook: ...\nActions:\n1. ...\n2. ...",
            ["Revised forecast exported", "Report leads with a headline", "Three variances explained",
             "Actions have owners or dates"], tool="fpa_lab"),
    )
    return Module("m4", 4, "FP&A and Budgeting",
                  "Annual budget, actual vs budget, flexible budgets, price/volume variances, payroll, "
                  "revised forecasts and the one-page management report.",
                  ["Budgeting & variance analysis", "Forecasting & modelling", "Management reporting"],
                  [l1, l2], tools=["fpa_lab"])
