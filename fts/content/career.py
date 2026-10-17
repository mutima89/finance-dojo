"""Career Mode: play the course as a career at the fictional Aurelia Grand Hotel.

You start as an intern. Each chapter is one module: finish its two lessons,
then beat the chapter's boss, a three-step decision for the hotel, to earn a
promotion and unlock the next chapter. The capstone project is the final boss.

Every number here is invented for practice, and every answer is computed with
the app's own finance functions in fts.core.metrics. Job titles are ranks in
the game, not qualifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core import metrics as m
from ..core.checker import format_value

START_RANK = "Intern"
FINAL_RANK = "Finance Director"
RANK_NOTE = "Career ranks are part of the game. They are not job titles or qualifications."
HEARTS = 3


@dataclass(frozen=True)
class BossStep:
    question: str
    expected: float
    unit: str                    # number, currency, percent, years
    hint: str
    solution: str
    abs_tol: Optional[float] = None


@dataclass(frozen=True)
class Boss:
    name: str
    emoji: str
    story: str
    steps: tuple[BossStep, ...]
    win_line: str                # what Sofia says when you win


@dataclass(frozen=True)
class Chapter:
    number: int                  # 1-8 = module number, 9 = capstone
    title: str
    rank: str                    # rank you are promoted to when you finish it
    boss: Optional[Boss]         # None for the capstone chapter


def _money(v: float, d: int = 0) -> str:
    return format_value(v, "currency", d)


def _pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f}%"


# ------------------------------------------------------------------ bosses
def _boss1() -> Boss:
    rev, cos, pay, other = 180_000, 54_000, 72_000, 21_000
    gp = m.gross_profit(rev, cos)
    op = gp - pay - other
    rev2 = rev * 1.10
    cos2 = rev2 * (cos / rev)
    op2 = rev2 - cos2 - pay - other
    return Boss(
        "The Monday P&L meeting", "📊",
        f"Sofia drops last month's numbers for The Terrace restaurant on your desk: revenue {_money(rev)}, "
        f"food and drink costs {_money(cos)}, payroll {_money(pay)} and other operating costs {_money(other)}. "
        "\"Walk me through it before the meeting starts.\"",
        (
            BossStep("What was the gross profit?", gp, "currency",
                     "Gross profit is revenue minus the cost of what you sold (food and drink).",
                     f"{_money(rev)} - {_money(cos)} = {_money(gp)}."),
            BossStep("What was the operating profit margin?", op / rev, "percent",
                     "Take payroll and other costs off the gross profit, then divide by revenue.",
                     f"Operating profit = {_money(gp)} - {_money(pay)} - {_money(other)} = {_money(op)}. "
                     f"Margin = {_money(op)} / {_money(rev)} = {_pct(op / rev)}."),
            BossStep("If revenue grows 10%, food costs stay the same share of revenue and payroll and other costs "
                     "stay fixed, what is the new operating profit?", op2, "currency",
                     "Food costs are 30% of revenue, so they grow too. Payroll and other costs don't.",
                     f"Revenue = {_money(rev2)}. Food costs = 30% = {_money(cos2)}. "
                     f"Profit = {_money(rev2)} - {_money(cos2)} - {_money(pay)} - {_money(other)} = {_money(op2)}. "
                     "A 10% sales rise lifts profit by far more than 10%: that's operating leverage."),
        ),
        "Clear and calm. That's exactly how I want the P&L explained. Welcome to the team properly.")


def _boss2() -> Boss:
    rows = [(120, 210), (95, 198), (60, 225)]
    corporate = sum(n * r for n, r in rows)
    leisure, groups, reported = 98_400, 44_990, 199_400
    total = corporate + leisure + groups
    last_week = 186_000
    return Boss(
        "The broken weekly report", "🧮",
        "The weekly revenue spreadsheet is wrong again and the owners meet in an hour. Corporate bookings this "
        "week were 120 room nights at $210, 95 at $198 and 60 at $225. Leisure brought in $98,400 and groups "
        "$44,990. The old report shows a total of $199,400.",
        (
            BossStep("What is the corporate room revenue (what your SUMIFS should return)?", corporate, "currency",
                     "Multiply each row's room nights by its rate, then add the three rows.",
                     " + ".join(f"{n} x ${r}" for n, r in rows) + f" = {_money(corporate)}."),
            BossStep("Your check cell compares the true total with the old report. By how much was the old "
                     "report too low?", total - reported, "currency",
                     "Add corporate, leisure and groups for the true total, then subtract the reported total.",
                     f"True total = {_money(corporate)} + {_money(leisure)} + {_money(groups)} = {_money(total)}. "
                     f"Gap = {_money(total)} - {_money(reported)} = {_money(total - reported)}."),
            BossStep(f"Last week's total was {_money(last_week)}. What is the week-on-week growth?",
                     m.growth_rate(total, last_week), "percent",
                     "Growth = this week / last week - 1.",
                     f"{_money(total)} / {_money(last_week)} - 1 = {_pct(m.growth_rate(total, last_week), 2)}."),
        ),
        "Fixed, checked and on time. The owners didn't even notice there was a problem. Perfect.")


def _boss3() -> Boss:
    rooms, days, sold, revenue = 150, 30, 3_510, 842_400
    avail = m.available_room_nights(rooms, days)
    occ, rate, rp = m.occupancy(sold, avail), m.adr(revenue, sold), m.revpar(revenue, avail)
    return Boss(
        "The RevPAR gap", "🏨",
        f"It's month end. The hotel has {rooms} rooms and the month had {days} days. You sold {sold:,} room "
        f"nights for {_money(revenue)} of room revenue. Sofia wants to know if the problem is rate or volume.",
        (
            BossStep("What was the occupancy?", occ, "percent",
                     "Available room nights = rooms x days. Occupancy = sold / available.",
                     f"Available = {rooms} x {days} = {avail:,}. Occupancy = {sold:,} / {avail:,} = {_pct(occ)}."),
            BossStep("What was the ADR (average daily rate)?", rate, "currency",
                     "ADR divides room revenue by rooms SOLD, not rooms available.",
                     f"{_money(revenue)} / {sold:,} = {_money(rate, 2)}."),
            BossStep("What was the RevPAR?", rp, "currency",
                     "RevPAR divides room revenue by rooms AVAILABLE (or occupancy x ADR).",
                     f"{_money(revenue)} / {avail:,} = {_money(rp, 2)}, the same as {_pct(occ)} x {_money(rate, 2)}."),
        ),
        "Now I can see it: we're full enough, the rate is the lever. Great diagnosis.")


def _boss4() -> Boss:
    actual, budget = 61_800, 58_000
    fixed, per_room, rooms = 7_600, 14.0, 3_900
    flexed = m.flexible_budget(fixed, per_room, rooms)
    v = m.variance(actual, budget, "expense")
    return Boss(
        "The angry housekeeping budget review", "🧹",
        f"The head of housekeeping is worried. Payroll was {_money(actual)} against a budget of {_money(budget)}. "
        f"But the budget was built as {_money(fixed)} fixed plus ${per_room:.2f} per occupied room, and the hotel "
        f"was busier than planned: {rooms:,} occupied rooms.",
        (
            BossStep("By how much was payroll over the original budget?", abs(v.amount), "currency",
                     "Actual minus budget. For a cost, spending more is unfavourable.",
                     f"{_money(actual)} - {_money(budget)} = {_money(v.amount)} over budget (unfavourable)."),
            BossStep("What is the flexible budget at the actual number of occupied rooms?", flexed, "currency",
                     "Re-state the budget at actual activity: fixed + cost per room x actual rooms.",
                     f"{_money(fixed)} + ${per_room:.2f} x {rooms:,} = {_money(flexed)}."),
            BossStep("By how much was actual payroll BELOW the flexible budget?", flexed - actual, "currency",
                     "Compare actual with the flexed budget, not the original one.",
                     f"{_money(flexed)} - {_money(actual)} = {_money(flexed - actual)} favourable. The team "
                     "was efficient; the hotel was just busier."),
        ),
        "You turned a blame meeting into a thank-you. That's real FP&A.")


def _boss5() -> Boss:
    avail, occ, rate = 150 * 91, 0.74, 232
    occ_d, rate_d = 0.70, 225
    sold = avail * occ
    rev = sold * rate
    rev_d = avail * occ_d * rate_d
    return Boss(
        "Next quarter's forecast", "🔮",
        f"The owners want a forecast for the next quarter: {avail:,} available room nights (150 rooms x 91 days). "
        f"Your base case is {_pct(occ, 0)} occupancy at an ADR of {_money(rate)}. The downside case is "
        f"{_pct(occ_d, 0)} at {_money(rate_d)}. Nobody can promise the future, so they want a range.",
        (
            BossStep("How many room nights do you forecast selling in the base case?", sold, "number",
                     "Room nights sold = available room nights x occupancy.",
                     f"{avail:,} x {_pct(occ, 0)} = {sold:,.0f}.", abs_tol=0.6),
            BossStep("What is the base-case room revenue?", rev, "currency",
                     "Room revenue = room nights sold x ADR.",
                     f"{sold:,.0f} x {_money(rate)} = {_money(rev)}."),
            BossStep("How much lower is room revenue in the downside case?", rev - rev_d, "currency",
                     "Work out downside revenue the same way, then subtract it from the base case.",
                     f"Downside = {avail:,} x {_pct(occ_d, 0)} x {_money(rate_d)} = {_money(rev_d)}. "
                     f"Gap = {_money(rev)} - {_money(rev_d)} = {_money(rev - rev_d)}."),
        ),
        "A range with clear drivers. The owners finally understand what could move the number.")


def _boss6() -> Boss:
    price, var, disc = 220, 60, 0.15
    cm, cm2 = price - var, price * (1 - disc) - var
    need = m.discount_volume_needed(price, var, disc)
    return Boss(
        "The big corporate discount", "🤝",
        f"Sales wants to give a large company {_pct(disc, 0)} off our {_money(price)} rate. Each room night "
        f"costs about {_money(var)} to service (cleaning, laundry, amenities). Sofia asks: what does it really cost us?",
        (
            BossStep("What is the contribution per room night today?", cm, "currency",
                     "Contribution = price - variable cost.",
                     f"{_money(price)} - {_money(var)} = {_money(cm)}."),
            BossStep("What is the contribution per room night after the discount?", cm2, "currency",
                     "Take the discount off the price first, then subtract the variable cost.",
                     f"{_money(price)} x {_pct(1 - disc, 0)} = {_money(price * (1 - disc))}; minus {_money(var)} "
                     f"= {_money(cm2)}."),
            BossStep("By what percentage must volume rise for total contribution to stay the same?", need, "percent",
                     "Old contribution / new contribution - 1.",
                     f"{_money(cm)} / {_money(cm2)} - 1 = {_pct(need)}. A {_pct(disc, 0)} discount needs about "
                     f"{_pct(need, 0)} more volume just to stand still."),
        ),
        "That one number changed the whole negotiation. Sales will ask for you by name now.")


def _boss7() -> Boss:
    flows = [-400_000] + [120_000] * 5
    rate = 0.10
    gain = sum(flows[1:])
    return Boss(
        "The pilot renovation decision", "🛠",
        "Before renovating every room, the owners could renovate one pilot floor of 20 rooms for $400,000. "
        "Higher rates on that floor should bring in an extra $120,000 of cash a year for 5 years. The hotel "
        "uses a 10% discount rate. They want a recommendation by Friday.",
        (
            BossStep("What is the total ROI over the 5 years (ignoring timing)?", m.roi(gain, 400_000),
                     "percent",
                     "ROI = (total cash in - investment) / investment.",
                     f"({_money(gain)} - {_money(400_000)}) / {_money(400_000)} = "
                     f"{_pct(m.roi(gain, 400_000), 0)}."),
            BossStep("What is the payback period in years?", m.payback_period(flows), "years",
                     "How long until the yearly cash adds up to the investment?",
                     f"{_money(400_000)} / {_money(120_000)} a year = {m.payback_period(flows):.2f} years."),
            BossStep("What is the NPV at 10%?", m.npv(rate, flows), "currency",
                     "Discount each year's cash by 1.10^year, add them up and subtract the investment.",
                     f"-{_money(400_000)} + {_money(120_000)} x 3.7908 (the 5-year factor at 10%) = "
                     f"{_money(m.npv(rate, flows))}. Positive, so it beats the 10% hurdle, but only just."),
        ),
        "Positive NPV, honest about the thin margin of safety. The board loved the recommendation.")


def _boss8() -> Boss:
    rev, ebitda, ebitda_ly, avail = 4_200_000, 1_092_000, 975_000, 4_500 * 3
    return Boss(
        "Your first board pack", "🧾",
        f"Quarter close. Total revenue was {_money(rev)} and EBITDA {_money(ebitda)}, against {_money(ebitda_ly)} "
        f"in the same quarter last year. The hotel had {avail:,} available room nights. You present first.",
        (
            BossStep("What is the EBITDA margin?", m.margin(ebitda, rev), "percent",
                     "EBITDA / total revenue.",
                     f"{_money(ebitda)} / {_money(rev)} = {_pct(m.margin(ebitda, rev))}."),
            BossStep("By how much did EBITDA grow versus last year?", m.growth_rate(ebitda, ebitda_ly), "percent",
                     "This year / last year - 1.",
                     f"{_money(ebitda)} / {_money(ebitda_ly)} - 1 = {_pct(m.growth_rate(ebitda, ebitda_ly))}."),
            BossStep("What is EBITDA per available room night?", ebitda / avail, "currency",
                     "Divide EBITDA by available room nights, the same way RevPAR divides revenue.",
                     f"{_money(ebitda)} / {avail:,} = {_money(ebitda / avail, 2)}."),
        ),
        "Short, clear, honest. The board asked who wrote it. You're ready for the big one.")


_RANKS = ["Junior Analyst", "Analyst", "Revenue Analyst", "FP&A Analyst", "Senior Analyst",
          "Commercial Finance Analyst", "Finance Manager", "Head of Commercial Finance"]
_BOSSES = [_boss1, _boss2, _boss3, _boss4, _boss5, _boss6, _boss7, _boss8]


def chapters() -> list[Chapter]:
    from .story import NOTES
    out = [Chapter(i + 1, NOTES[i + 1][0], _RANKS[i], b()) for i, b in enumerate(_BOSSES)]
    out.append(Chapter(9, "Final boss: the capstone case", FINAL_RANK, None))
    return out


def rank_for(chapters_done: int) -> str:
    """Rank after finishing this many chapters in a row (0 = just started)."""
    if chapters_done <= 0:
        return START_RANK
    ranks = [c.rank for c in chapters()]
    return ranks[min(chapters_done, len(ranks)) - 1]


def stars_for(hearts_left: int) -> int:
    """3 stars with no lives lost, 2 with one lost, 1 with two lost."""
    return max(0, min(3, hearts_left))
