"""Capstone project: junior analyst at The Aurelia Grand Hotel.

Scoring is transparent: every item states its points. Numeric and choice
items are checked automatically. Written items get an automatic STRUCTURE
score (length, numbers quoted, recommendation, risks, assumptions). That is
not a judgement of business quality, and the UI says so. Instructors use the
qualitative rubric in docs/ANSWER_KEY.md for that.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..core import metrics as m
from ..core.checker import check_numeric, format_value
from ..data import generator as gen
from ..data.loader import data

PASS_MARK = 70


@dataclass
class Item:
    id: str
    label: str
    kind: str                     # numeric, choice, text, kpis, export, multi
    points: float
    expected: object = None
    unit: str = "number"
    choices: list[str] = field(default_factory=list)
    rel_tol: Optional[float] = None
    abs_tol: Optional[float] = None
    explanation: str = ""


@dataclass
class Step:
    id: str
    number: int
    title: str
    brief: str
    items: list[Item]

    @property
    def points(self) -> float:
        return sum(i.points for i in self.items)


KPI_OPTIONS = ["Occupancy %", "ADR", "RevPAR", "Total revenue vs budget", "EBITDA vs budget",
               "Payroll % of revenue", "Number of emails sent", "Average guest age", "Share price"]
ESSENTIAL_KPIS = {"Occupancy %", "ADR", "RevPAR", "Total revenue vs budget", "EBITDA vs budget",
                  "Payroll % of revenue"}
IRRELEVANT_KPIS = {"Number of emails sent", "Average guest age", "Share price"}


def _figures():
    ds = data()
    c = ds.capstone_clean
    total_rev = c.room_revenue + c.fb_revenue + c.other_revenue
    b_total_rev = c.budget_room_revenue + c.budget_fb_revenue + c.budget_other_revenue
    ebitda = total_rev - c.payroll - c.other_operating_expenses - c.fees_and_fixed_charges
    b_ebitda = (b_total_rev - c.budget_payroll - c.budget_other_operating_expenses
                - c.budget_fees_and_fixed_charges)
    fy = dict(
        sold=int(c.sold_room_nights.sum()), avail=int(c.available_room_nights.sum()),
        room_rev=float(c.room_revenue.sum()), total_rev=float(total_rev.sum()),
        b_total_rev=float(b_total_rev.sum()), ebitda=float(ebitda.sum()), b_ebitda=float(b_ebitda.sum()))
    q4 = c[c.month >= 10]
    jan = c[c.month == 1].iloc[0]
    fy["jan_fc"] = float(jan.room_revenue * q4.room_revenue.sum() / q4.budget_room_revenue.sum())
    lines = {
        "Room revenue": m.variance(c.room_revenue.sum(), c.budget_room_revenue.sum(), "revenue"),
        "F&B revenue": m.variance(c.fb_revenue.sum(), c.budget_fb_revenue.sum(), "revenue"),
        "Other revenue": m.variance(c.other_revenue.sum(), c.budget_other_revenue.sum(), "revenue"),
        "Payroll": m.variance(c.payroll.sum(), c.budget_payroll.sum(), "expense"),
        "Other operating expenses": m.variance(c.other_operating_expenses.sum(),
                                               c.budget_other_operating_expenses.sum(), "expense"),
        "Fees & fixed charges": m.variance(c.fees_and_fixed_charges.sum(),
                                           c.budget_fees_and_fixed_charges.sum(), "expense"),
    }
    fy["lines"] = lines
    cases = ds.cases
    pr = cases["restaurant_promotion"]
    now = (pr["current_price"] - pr["variable_cost_per_cover"]) * pr["current_covers_per_month"]
    promo = ((pr["current_price"] * (1 - pr["discount_pct"]) - pr["variable_cost_per_cover"])
             * pr["expected_covers_with_promo"] - pr["extra_marketing_cost"])
    fy["promo_delta"] = promo - now
    ren = cases["renovation"]
    fy["ren_npv"] = m.npv(ren["discount_rate"], ren["cash_flows"])
    return fy


def steps() -> list[Step]:
    f = _figures()
    months = list(gen.MONTHS)
    worst = max(((k, v) for k, v in f["lines"].items() if not v.favorable), key=lambda kv: abs(kv[1].amount))[0]
    line_names = list(f["lines"].keys())
    return [
        Step("c1", 1, "Clean and validate the data",
             "Open the raw capstone data (table on this screen, or datasets/capstone_raw_data.csv). It contains "
             "deliberate data-quality problems. Find them and fix them: remove duplicates; rebuild a missing sold "
             "room nights value from revenue / reported ADR; correct a value keyed in thousands; replace an impossible "
             "value (sold > available) with sold = revenue / reported ADR.",
             [Item("c1_dup", "How many duplicate rows are there?", "numeric", 2, 1, abs_tol=0),
              Item("c1_missing", "Which month is missing sold room nights?", "choice", 2,
                   months.index(gen.CAPSTONE_ISSUES["missing_sold_month"]), choices=months),
              Item("c1_thousands", "Which month's room revenue is in thousands?", "choice", 2,
                   months.index(gen.CAPSTONE_ISSUES["thousands_month"]), choices=months),
              Item("c1_impossible", "Which month has impossible occupancy (sold > available)?", "choice", 2,
                   months.index(gen.CAPSTONE_ISSUES["impossible_occupancy_month"]), choices=months),
              Item("c1_rev", "Corrected full-year ROOM revenue ($)", "numeric", 2, f["room_rev"], "currency",
                   abs_tol=2.0, explanation="Remove the duplicate June row and multiply August by 1,000.")]),
        Step("c2", 2, "Calculate the required KPIs",
             "Using the cleaned data, calculate full-year KPIs.",
             [Item("c2_occ", "Full-year occupancy %", "numeric", 5, f["sold"] / f["avail"], "percent"),
              Item("c2_adr", "Full-year ADR ($)", "numeric", 5, f["room_rev"] / f["sold"], "currency"),
              Item("c2_revpar", "Full-year RevPAR ($)", "numeric", 5, f["room_rev"] / f["avail"], "currency")]),
        Step("c3", 3, "Build a forecast",
             "Forecast next January's ROOM revenue by applying the Q4 (Oct-Dec) actual-to-budget ratio for room "
             "revenue to this January's actual room revenue: Forecast = Jan actual x (Q4 actual / Q4 budget). Then "
             "explain the method and one limitation.",
             [Item("c3_fc", "Forecast January room revenue ($)", "numeric", 6, f["jan_fc"], "currency", rel_tol=0.001),
              Item("c3_text", "Method and limitation (2-4 sentences)", "text", 4,
                   explanation="Structure check: mentions method, an assumption/limitation, at least one number.")]),
        Step("c4", 4, "Explain budget variances",
             "Compare actual with budget for the six capstone lines (room, F&B and other revenue; payroll; other "
             "operating expenses; fees & fixed charges).",
             [Item("c4_total", "Full-year TOTAL revenue variance, Actual - Budget ($)", "numeric", 5,
                   f["total_rev"] - f["b_total_rev"], "currency", abs_tol=2.0),
              Item("c4_worst", "Largest unfavorable variance", "choice", 5, line_names.index(worst), choices=line_names),
              Item("c4_text", "Explain the two biggest unfavorable variances and their drivers", "text", 5)]),
        Step("c5", 5, "Evaluate two commercial decisions",
             "Decision A: the Sunset Bistro 20% promotion (Module 6). Decision B: the guest-room renovation (Module 7).",
             [Item("c5_a_num", "A: change in monthly contribution ($)", "numeric", 4, f["promo_delta"], "currency"),
              Item("c5_a_dec", "A: decision", "choice", 3, 1,
                   choices=["Approve as designed", "Reject or redesign (e.g. quiet nights only)"]),
              Item("c5_b_num", "B: renovation NPV at 10% ($)", "numeric", 4, f["ren_npv"], "currency",
                   rel_tol=0.0005, abs_tol=5),
              Item("c5_b_dec", "B: decision", "choice", 4, 1,
                   choices=["Reject: too risky", "Approve subject to a pilot floor and capex control",
                            "Approve: NPV is guaranteed"])]),
        Step("c6", 6, "Prepare a management dashboard",
             "Choose the KPIs for the General Manager's dashboard and export it as an image.",
             [Item("c6_kpis", "KPI selection", "kpis", 6),
              Item("c6_export", "Dashboard exported", "export", 4)]),
        Step("c7", 7, "Write a one-page executive recommendation",
             "150-450 words. Lead with the recommendation, support it with numbers, state assumptions/limitations "
             "and risks, and give next steps.",
             [Item("c7_text", "Executive recommendation", "text", 15)]),
        Step("c8", 8, "Simulated management meeting",
             "The executive committee questions your recommendation. Choose the best response to each question.",
             [Item(f"c8_q{i}", q, "choice", 2, ans, choices=opts, explanation=why)
              for i, (q, opts, ans, why) in enumerate(MEETING, 1)]),
    ]


MEETING = [
    ("General Manager: 'Why is room revenue below budget in the last quarter?'",
     ["The market collapsed", "Weekday corporate demand fell and was replaced by lower-rated OTA business; weekends held",
      "Housekeeping was slow", "The budget was wrong"], 1,
     "Evidence-based driver: weekday occupancy and channel mix."),
    ("Owner: 'Can you guarantee the renovation returns at least 10%?'",
     ["Yes, guaranteed", "No. On our assumptions NPV at 10% is positive, but it depends mainly on the ADR uplift; "
      "a pilot floor reduces that risk", "I don't know", "Ask the contractor"], 1,
     "Never guarantee; give the assumption it depends on and a mitigation."),
    ("Director of Finance: 'Payroll is over budget even though occupancy was under. What would you check?'",
     ["Nothing, payroll is fixed", "Split into headcount, average cost and overtime; flex variable departments to occupancy",
      "Cut all salaries", "Raise ADR"], 1, "Decompose the variance into its drivers."),
    ("Director of Sales: 'Should we cut rates 15% across the board in January?'",
     ["Yes, volume solves everything", "No. Target weak weekday dates and the corporate segment, protect strong "
      "weekends, and test with the elasticity scenario", "Raise rates 15%", "Close the hotel"], 1,
     "Targeted actions beat blanket discounts; quantify first."),
    ("Owner: 'What is the single most important action for next quarter?'",
     ["Recover weekday corporate demand and shift transient share from OTA to direct",
      "Change the logo", "Stop all capex forever", "Hire more managers"], 0,
     "Addresses the main driver of the shortfall and channel cost."),
]


# --------------------------------------------------------------- scoring

def text_structure_score(text: str, points: float) -> tuple[float, list[str]]:
    """Transparent structural checks (not a judgement of quality)."""
    t = (text or "").strip()
    words = len(re.findall(r"\b\w+\b", t))
    nums = len(re.findall(r"\d[\d,\.]*%?", t))
    low = t.lower()
    checks = [
        ("Length 40+ words" if points < 10 else "Length 150-450 words",
         words >= 40 if points < 10 else 150 <= words <= 450),
        ("Quotes at least 3 numbers", nums >= 3),
        ("Gives a recommendation or action", any(k in low for k in ("recommend", "propose", "should", "action"))),
        ("Mentions risk", "risk" in low),
        ("States assumptions or limitations", any(k in low for k in ("assum", "limitation", "estimate", "uncertain"))),
    ]
    if points < 10:
        checks = checks[:3] + [("Mentions an assumption, limitation or driver",
                                any(k in low for k in ("assum", "limitation", "because", "driver", "due to")))]
    per = points / len(checks)
    score = sum(per for _, ok in checks if ok)
    return round(score, 2), [("✔ " if ok else "✘ ") + name for name, ok in checks]


def score_item(item: Item, answer) -> tuple[float, str]:
    if answer is None or answer == "" or answer == []:
        return 0.0, "Not answered."
    if item.kind == "numeric":
        r = check_numeric(str(answer), float(item.expected), item.unit, item.abs_tol, item.rel_tol)
        if r.correct:
            return item.points, "Correct."
        return 0.0, f"{r.message} {r.diagnosis or ''}".strip()
    if item.kind == "choice":
        try:
            ok = int(answer) == int(item.expected)
        except (TypeError, ValueError):
            return 0.0, "Not answered."
        return (item.points, "Correct. " + item.explanation) if ok else (0.0, "Not the best answer. " + item.explanation)
    if item.kind == "text":
        s, notes = text_structure_score(str(answer), item.points)
        return s, "Structure check: " + "; ".join(notes)
    if item.kind == "kpis":
        chosen = set(answer)
        good = len(chosen & ESSENTIAL_KPIS)
        bad = len(chosen & IRRELEVANT_KPIS)
        s = max(0.0, item.points * good / len(ESSENTIAL_KPIS) - 2.0 * bad)
        return round(s, 2), (f"{good} of {len(ESSENTIAL_KPIS)} essential KPIs selected"
                             + (f"; {bad} irrelevant KPI(s) cost points" if bad else ""))
    if item.kind == "export":
        return (item.points, "Dashboard exported.") if answer else (0.0, "Export the dashboard image.")
    return 0.0, ""


def score_all(answers: dict) -> dict:
    """answers: item id -> answer. Returns per-step and total scores."""
    out, total, possible = [], 0.0, 0.0
    for st in steps():
        s_score = 0.0
        details = []
        for it in st.items:
            pts, msg = score_item(it, answers.get(it.id))
            s_score += pts
            details.append((it, pts, msg))
        out.append((st, round(s_score, 2), details))
        total += s_score
        possible += st.points
    total = round(total, 2)
    return {"steps": out, "total": total, "possible": possible, "passed": total >= PASS_MARK}


def expected_display(item: Item) -> str:
    if item.kind == "numeric":
        return format_value(float(item.expected), item.unit)
    if item.kind == "choice":
        return item.choices[int(item.expected)]
    if item.kind == "kpis":
        return ", ".join(sorted(ESSENTIAL_KPIS))
    return "See rubric"
