"""Real-life mini challenges ("quests") and everyday hooks for each lesson.

Each challenge is a one-minute puzzle from everyday life that uses the same
formula as a work skill (break-even, RevPAR, variance, NPV...). The numbers are
generated, so every day brings new ones; the answer is always computed with the
app's own finance functions in fts.core.metrics. All scenarios and prices are
made up for practice.
"""
from __future__ import annotations

import datetime as dt
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

from ..core import metrics as m
from ..core.checker import format_value


@dataclass(frozen=True)
class Challenge:
    id: str
    emoji: str
    title: str
    story: str
    question: str
    expected: float
    unit: str                     # number, currency, percent, years
    hint: str
    solution: str
    skill: str
    lesson_id: str
    work_link: str                # how the same maths shows up at work
    abs_tol: Optional[float] = None


def _money(v: float, d: int = 2) -> str:
    return format_value(v, "currency", d)


def _pct(v: float, d: int = 1) -> str:
    return f"{v * 100:.{d}f}%"


# ---------------------------------------------------------------- templates
def coffee_cart(r: random.Random) -> Challenge:
    fixed = r.choice([180, 200, 240, 260, 300])
    price = r.choice([3.5, 4.0, 4.5])
    var = r.choice([1.1, 1.25, 1.4])
    units = math.ceil(m.break_even_units(fixed, price, var))
    return Challenge(
        "coffee_cart", "☕", "Weekend coffee cart",
        f"You run a coffee cart at the Saturday market. Stall rent and gear cost {_money(fixed, 0)} per day. "
        f"Each coffee sells for {_money(price)} and the beans, milk and cup cost {_money(var)}.",
        "How many coffees must you sell to break even? Round up to a whole coffee.",
        units, "number",
        "Each coffee adds price minus variable cost to cover the rent. Divide the fixed cost by that amount.",
        f"Contribution per coffee = {_money(price)} - {_money(var)} = {_money(price - var)}. "
        f"Break-even = {_money(fixed, 0)} / {_money(price - var)} = {fixed / (price - var):.1f}, "
        f"so you need {units} coffees.",
        "Cost behaviour & break-even", "m1l2",
        "A hotel restaurant uses the same sum to decide how many covers a new menu must sell.",
        abs_tol=0.5)


def gym_per_visit(r: random.Random) -> Challenge:
    fee = r.choice([29.99, 35.0, 39.99, 45.0, 49.0])
    visits = r.choice([4, 5, 6, 8, 10, 12])
    per = fee / visits
    return Challenge(
        "gym_per_visit", "🏋️", "What does a gym visit really cost?",
        f"Your gym costs {_money(fee)} a month. This month you went {visits} times.",
        "What did each visit cost you?",
        per, "currency",
        "Total money paid divided by the number of times you actually used it.",
        f"{_money(fee)} / {visits} visits = {_money(per)} per visit.",
        "Hotel KPIs", "m3l1",
        "This is ADR thinking: room revenue divided by rooms actually sold.")


def cinema_occupancy(r: random.Random) -> Challenge:
    seats = r.choice([80, 120, 150, 200])
    shows = r.choice([3, 4, 5])
    avail = seats * shows
    sold = r.randint(int(avail * 0.35), int(avail * 0.9))
    occ = m.occupancy(sold, avail)
    return Challenge(
        "cinema_occupancy", "🎬", "How full was the cinema?",
        f"A cinema screen has {seats} seats and ran {shows} showings on Friday. It sold {sold:,} tickets in total.",
        "What was the occupancy for the day, as a percentage?",
        occ, "percent",
        "Available seats = seats x showings. Occupancy = tickets sold / available seats.",
        f"Available = {seats} x {shows} = {avail:,} seats. Occupancy = {sold:,} / {avail:,} = {_pct(occ)}.",
        "Hotel KPIs", "m3l1",
        "Hotels measure occupancy the same way: rooms sold / rooms available.")


def restaurant_revpat(r: random.Random) -> Challenge:
    tables = r.choice([12, 15, 18, 20, 24])
    turns = r.choice([2, 3])
    available = tables * turns
    revenue = r.randint(18, 40) * 100 + r.choice([0, 50])
    rev = m.revpar(revenue, available)
    return Challenge(
        "restaurant_revpat", "🍝", "Revenue per available table",
        f"Your favourite restaurant has {tables} tables and can seat each table {turns} times on a Friday night. "
        f"Friday's food revenue was {_money(revenue, 0)}.",
        "What was the revenue per available table slot?",
        rev, "currency",
        "Count every table slot it could have sold, used or not, then divide revenue by that.",
        f"Slots = {tables} x {turns} = {available}. Revenue per slot = {_money(revenue, 0)} / {available} "
        f"= {_money(rev)}.",
        "Hotel KPIs", "m3l1",
        "This is RevPAR: room revenue divided by rooms available, sold or not.")


def grocery_variance(r: random.Random) -> Challenge:
    budget = r.choice([350, 400, 450, 500])
    actual = budget + r.choice([-60, -35, -20, 25, 40, 75, 90])
    v = m.variance(actual, budget, "expense")
    word = "unfavourable (you overspent)" if not v.favorable else "favourable (you underspent)"
    return Challenge(
        "grocery_variance", "🛒", "Grocery budget check-in",
        f"You budgeted {_money(budget, 0)} for groceries this month and actually spent {_money(actual, 0)}.",
        "What is the variance, actual minus budget, in dollars? (Use a minus sign if you spent less.)",
        v.amount, "currency",
        "Variance = actual - budget. For a cost, spending more than budget is unfavourable.",
        f"{_money(actual, 0)} - {_money(budget, 0)} = {_money(v.amount, 0)}, which is {word}.",
        "Budgeting & variance analysis", "m4l1",
        "FP&A teams flag every cost line like this each month: actual vs budget, F or U.")


def phone_bill(r: random.Random) -> Challenge:
    old = r.choice([25.0, 30.0, 40.0, 45.0, 55.0])
    new = old + r.choice([2.5, 3.0, 4.5, 5.0, 7.5])
    g = m.growth_rate(new, old)
    return Challenge(
        "phone_bill", "📱", "Your phone bill went up",
        f"Your phone plan went from {_money(old)} to {_money(new)} a month.",
        "By what percentage did it go up?",
        g, "percent",
        "Change divided by the old amount.",
        f"({_money(new)} - {_money(old)}) / {_money(old)} = {_pct(g)}.",
        "Forecasting & modelling", "m5l1",
        "Forecasters apply growth rates like this to last year's numbers to build next year's.")


def savings_goal(r: random.Random) -> Challenge:
    pv = r.choice([1000, 1500, 2000, 2500, 3000])
    rate = r.choice([0.03, 0.04, 0.05])
    years = r.choice([2, 3, 4, 5])
    fv = m.future_value(pv, rate, years)
    return Challenge(
        "savings_goal", "🐷", "Let your savings grow",
        f"You put {_money(pv, 0)} in a savings account that pays {rate * 100:.0f}% a year, compounded yearly, "
        f"and leave it for {years} years.",
        "How much will be in the account at the end?",
        fv, "currency",
        "Future value = today's amount x (1 + rate) to the power of the number of years.",
        f"{_money(pv, 0)} x (1 + {rate:.2f})^{years} = {_money(fv)}.",
        "Investment appraisal", "m7l1",
        "Discounting is this in reverse: NPV turns future cash back into today's money.")


def side_hustle_npv(r: random.Random) -> Challenge:
    cost = r.choice([1200, 1500, 1800, 2000])
    inflow = r.choice([600, 700, 800, 900])
    rate = r.choice([0.08, 0.10, 0.12])
    flows = [-cost, inflow, inflow, inflow]
    v = m.npv(rate, flows)
    return Challenge(
        "side_hustle_npv", "📷", "Is the camera worth it?",
        f"You could buy a {_money(cost, 0)} camera today and earn {_money(inflow, 0)} a year from photo gigs for "
        f"3 years. Money you don't spend could earn {rate * 100:.0f}% a year elsewhere.",
        "What is the NPV of buying the camera?",
        v, "currency",
        "Discount each year's income by (1 + rate)^year, add them up, then subtract today's cost.",
        "NPV = -{c} + {i}/{a:.2f} + {i}/{a:.2f}^2 + {i}/{a:.2f}^3 = {v}. {verdict}".format(
            c=_money(cost, 0), i=_money(inflow, 0), a=1 + rate, v=_money(v),
            verdict="Positive, so it beats the alternative (an estimate, not a guarantee)." if v > 0 else
            "Negative, so the alternative is better on these numbers."),
        "Investment appraisal", "m7l1",
        "Hotels run exactly this test before spending on a renovation.")


def solar_payback(r: random.Random) -> Challenge:
    cost = r.choice([4000, 5000, 6000, 7500])
    saving = r.choice([800, 900, 1000, 1200, 1500])
    pb = m.payback_period([-cost] + [saving] * 20)
    return Challenge(
        "solar_payback", "☀️", "When do solar panels pay for themselves?",
        f"Solar panels for a house cost {_money(cost, 0)} and cut the power bill by {_money(saving, 0)} a year.",
        "How many years until the savings repay the cost?",
        pb, "years",
        "Payback = up-front cost / yearly saving (when the saving is the same every year).",
        f"{_money(cost, 0)} / {_money(saving, 0)} per year = {pb:.2f} years.",
        "Commercial analysis", "m6l2",
        "Managers ask \"when do we get our money back?\" about every new service or machine.")


def pizza_discount(r: random.Random) -> Challenge:
    price = r.choice([12.0, 14.0, 15.0, 16.0])
    var = r.choice([4.0, 5.0, 6.0])
    disc = r.choice([0.10, 0.15, 0.20])
    up = m.discount_volume_needed(price, var, disc)
    new_price = price * (1 - disc)
    return Challenge(
        "pizza_discount", "🍕", "The 'buy more, pay less' pizza deal",
        f"A pizzeria sells pizzas for {_money(price)}; ingredients and box cost {_money(var)}. "
        f"The owner wants a {disc * 100:.0f}% discount.",
        "By what percentage must pizza sales rise just to earn the same total profit as before?",
        up, "percent",
        "Compare profit per pizza before and after the discount: old margin / new margin - 1.",
        f"Before: {_money(price)} - {_money(var)} = {_money(price - var)} per pizza. After: {_money(new_price)} - "
        f"{_money(var)} = {_money(new_price - var)}. Needed uplift = {_money(price - var)} / "
        f"{_money(new_price - var)} - 1 = {_pct(up)}.",
        "Commercial analysis", "m6l1",
        "Revenue managers test every room-rate discount this way before launching it.")


def lemonade_margin(r: random.Random) -> Challenge:
    price = r.choice([2.0, 2.5, 3.0])
    var = r.choice([0.6, 0.75, 0.9])
    cm = m.contribution_margin_ratio(price, var)
    return Challenge(
        "lemonade_margin", "🍋", "Lemonade stand margin",
        f"Your niece sells lemonade at {_money(price)} a cup. Lemons, sugar and cups cost {_money(var)} per cup.",
        "What is the contribution margin as a percentage of the price?",
        cm, "percent",
        "(Price - variable cost) / price.",
        f"({_money(price)} - {_money(var)}) / {_money(price)} = {_pct(cm)}.",
        "Commercial analysis", "m6l1",
        "Finance teams quote contribution margins for every product and service line.")


def followers_cagr(r: random.Random) -> Challenge:
    start = r.choice([800, 1000, 1200, 1500])
    years = r.choice([2, 3])
    growth = r.choice([0.25, 0.35, 0.5, 0.6])
    end = round(start * (1 + growth) ** years, -1)
    c = m.cagr(start, end, years)
    return Challenge(
        "followers_cagr", "📈", "How fast is the account growing?",
        f"A friend's small-business account grew from {start:,} to {end:,.0f} followers in {years} years.",
        "What is the compound annual growth rate (CAGR)?",
        c, "percent",
        "CAGR = (end / start) ^ (1 / years) - 1.",
        f"({end:,.0f} / {start:,})^(1/{years}) - 1 = {_pct(c)}.",
        "Forecasting & modelling", "m5l1",
        "Analysts quote CAGR to compare growth across years, hotels or markets.")


def grade_average(r: random.Random) -> Challenge:
    scores = [r.randint(55, 95) for _ in range(3)]
    weights = r.choice([(0.2, 0.3, 0.5), (0.25, 0.25, 0.5), (0.3, 0.3, 0.4)])
    avg = m.weighted_average(scores, weights)
    return Challenge(
        "grade_average", "🎓", "Your weighted course grade",
        f"Your course grade is: quiz {scores[0]} ({weights[0] * 100:.0f}%), project {scores[1]} "
        f"({weights[1] * 100:.0f}%) and exam {scores[2]} ({weights[2] * 100:.0f}%).",
        "What is your final weighted grade?",
        avg, "number",
        "Multiply each score by its weight and add them up (Excel: SUMPRODUCT).",
        f"{scores[0]} x {weights[0]} + {scores[1]} x {weights[1]} + {scores[2]} x {weights[2]} = {avg:.2f}.",
        "Excel formulas", "m2l1",
        "SUMPRODUCT does the same for a hotel's weighted average rate across segments.",
        abs_tol=0.06)


TEMPLATES: list[Callable[[random.Random], Challenge]] = [
    coffee_cart, gym_per_visit, cinema_occupancy, restaurant_revpat, grocery_variance, phone_bill,
    savings_goal, side_hustle_npv, solar_payback, pizza_discount, lemonade_margin, followers_cagr, grade_average,
]

QUESTS_PER_DAY = 3


def daily_quests(day: dt.date) -> list[Challenge]:
    """Three different challenges for the given day, the same all day long."""
    r = random.Random(day.toordinal() * 7919)
    picks = r.sample(TEMPLATES, QUESTS_PER_DAY)
    return [t(random.Random(f"{day.isoformat()}:{i}")) for i, t in enumerate(picks)]


def practice_challenge(day: dt.date, n: int) -> Challenge:
    """Endless practice: the n-th extra challenge of the day."""
    r = random.Random(f"practice:{day.isoformat()}:{n}")
    return r.choice(TEMPLATES)(r)


# ----------------------------------------------------------- lesson hooks
# key idea (the one sentence to remember) and an everyday version of the topic
LESSON_HOOKS: dict[str, tuple[str, str]] = {
    "m1l1": ("Three reports, three questions: did we make money (P&L), what do we own and owe (balance sheet), "
             "and where did the cash go (cash flow)?",
             "Your payslip is a mini P&L, your bank balance minus your card debt is a balance sheet, and your "
             "banking app's history is your cash flow statement."),
    "m1l2": ("Profit is not cash, and every sale must first cover its own variable cost before it helps pay "
             "the fixed costs.",
             "A food truck owner knows how many tacos pay the weekly pitch fee. That number is break-even."),
    "m2l1": ("Inputs in one place, calculations that point at them, and outputs that only read results: "
             "a model you can trust.",
             "A trip budget sheet where you change the hotel price once and every total updates is a model."),
    "m2l2": ("Lookups find, checks catch errors, and sensitivity tables show which input moves the answer most.",
             "Comparing flights in a table by date and price, then seeing how the total changes, is a lookup "
             "plus a sensitivity."),
    "m3l1": ("RevPAR = Occupancy x ADR. It rewards filling rooms and charging well at the same time.",
             "A cinema that's half full at full price can earn the same as one that's full at half price."),
    "m3l2": ("Charge more when demand is high, protect rooms for the best segments, and sell through the "
             "cheapest channel that fills them.",
             "Concert tickets and flights get pricier as the date gets closer and seats run out."),
    "m4l1": ("Variance = actual - budget. Say whether it's favourable, then say why it happened.",
             "Overspending your grocery budget is an unfavourable variance. The 'why' is the useful part."),
    "m4l2": ("Payroll is usually the biggest cost, and a revised forecast tells managers where the year will "
             "really land.",
             "Halfway through the month you check your spending and adjust: that's a revised forecast."),
    "m5l1": ("A forecast is drivers (rooms, occupancy, rate) times assumptions, rolled forward and checked.",
             "Planning next year's rent and bills from this year plus expected price rises is a driver forecast."),
    "m5l2": ("Always show base, upside and downside, and say which assumption matters most.",
             "Planning a trip with a 'what if flights cost 20% more?' line is scenario thinking."),
    "m6l1": ("Contribution (price - variable cost) decides discounts. A discount needs more volume to pay "
             "for itself.",
             "A '20% off' pizza deal only works for the shop if enough extra pizzas sell."),
    "m6l2": ("Payback says when you get your money back; ROI says how much you get back overall.",
             "Solar panels that save on the power bill have a payback period, just like a hotel spa upgrade."),
    "m7l1": ("Money today is worth more than money later. NPV above zero means the project beats the "
             "alternative, on these estimates.",
             "Would you take $100 today or $105 next year? Your answer reveals your discount rate."),
    "m7l2": ("Good investment decisions look at NPV, risk and the downside, not only the best case.",
             "Buying a used car vs a new one: compare total cost, risk of repairs and resale value."),
    "m8l1": ("A dashboard shows few KPIs, each tied to a decision. Lead with the message, not the data.",
             "A fitness app shows steps, sleep and heart rate on one screen, not 40 numbers."),
    "m8l2": ("Answer first, then three reasons, then the risk and the next step. Keep it short.",
             "Asking your manager for a day off works best with the answer first and a plan to cover your work."),
}
