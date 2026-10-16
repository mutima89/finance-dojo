"""Modules 5-8: modelling, commercial finance, decisions, reporting."""
from __future__ import annotations

from ..core import forecast as fc
from ..core import metrics as m
from ..core.checker import Mistake
from ..data import generator as gen
from ..data.loader import data
from .base import Exercise, Lesson, Module, PracticalTask, QuizQuestion as Q
from .modules_1_4 import money, pct


# =================================================================== MODULE 5

def module5() -> Module:
    a = fc.HotelAssumptions()
    base = fc.hotel_forecast(a)
    y1 = base["Year 1"]
    down = fc.hotel_forecast(a.scaled(**fc.SCENARIOS["Downside"]))["Year 1"]
    a_up = fc.HotelAssumptions(occupancy=tuple(o + 0.01 for o in a.occupancy))
    e_up = fc.hotel_forecast(a_up)["Year 1"]["EBITDA"]

    l1 = Lesson(
        id="m5l1", title="Model architecture and a 3-year hotel forecast",
        concept=f"""
## Driver-based modelling
A good forecast is built from **drivers** you can discuss with operators, not from a single growth %:

`Rooms x 365 = Available room nights` → `x Occupancy = Sold room nights` → `x ADR = Rooms revenue`
→ `+ Ancillary (F&B, spa) as % of rooms revenue = Total revenue`
→ `- Payroll (fixed + per occupied room) - Other operating costs (% of revenue) - Fixed charges = EBITDA`
→ `- Capital expenditure - Increase in working capital = Free cash flow`
→ `Opening cash + Free cash flow = Closing cash`.

## Three-statement concepts
In a full model the **P&L**, **balance sheet** and **cash flow** are linked: net income flows to retained
earnings and to the cash flow; capex adds to fixed assets; working capital lines move the balance
sheet; closing cash on the cash flow equals cash on the balance sheet.

> **Training simplification.** The model in this app links operations → EBITDA → free cash flow → cash.
> It has **no** debt schedule, interest, tax or full balance sheet. It shows how the pieces connect.
> It is not a complete professional three-statement model, which would add those schedules and a
> balancing check.

Default assumptions start from the FY{gen.YEAR} actuals (opening cash and working capital come from
the closing balance sheet). The forward numbers are **illustrative**.
""",
        worked_example=f"""
### Worked example: Year 1 revenue build

| Driver | Value |
|---|---|
| Available room nights | 150 x 365 = {y1['Available room nights']:,.0f} |
| Occupancy | {pct(a.occupancy[0])} → sold {y1['Sold room nights']:,.2f} |
| ADR | {money(a.adr[0])} |
| Rooms revenue | {money(y1['Rooms revenue'])} |
| Ancillary ({pct(a.ancillary_pct_of_rooms, 0)} of rooms) | {money(y1['Ancillary revenue'])} |
| **Total revenue** | **{money(y1['Total revenue'])}** |
""",
        guided=Exercise(
            id="m5l1_g", skill="Forecasting & modelling", practical=True,
            prompt=f"Using the Year 1 table above: payroll = {money(a.payroll_fixed)} fixed + {money(a.payroll_per_occupied_room)} "
                   f"per sold room night; other operating costs = {pct(a.other_opex_pct_revenue)} of total revenue; "
                   f"fixed charges {money(a.fixed_charges)}. Calculate Year 1 **EBITDA**.",
            steps=[f"Payroll = {money(a.payroll_fixed)} + 38 x {y1['Sold room nights']:,.2f}.",
                   f"Other costs = {pct(a.other_opex_pct_revenue)} x total revenue.",
                   "EBITDA = Total revenue - payroll - other costs - fixed charges."],
            expected=y1["EBITDA"], unit="currency", rel_tol=0.0005,
            hints=[f"Payroll = {money(y1['Payroll'])}", f"Other costs = {money(y1['Other operating expenses'])}"],
            mistakes=[Mistake(y1["Total revenue"] - y1["Payroll"] - y1["Other operating expenses"],
                              "You forgot the fixed charges (insurance and property tax).")],
            solution=f"{money(y1['Total revenue'])} - {money(y1['Payroll'])} - {money(y1['Other operating expenses'])} "
                     f"- {money(a.fixed_charges)} = {money(y1['EBITDA'])}"),
        independent=[
            Exercise(
                id="m5l1_i1", skill="Forecasting & modelling", practical=True,
                prompt=f"Year 1 EBITDA is {money(y1['EBITDA'])}. Capex is {pct(a.capex_pct_revenue, 0)} of total revenue "
                       f"({money(y1['Total revenue'])}). Working capital moves from {money(a.opening_nwc)} to "
                       f"{money(y1['Net working capital'])}. What is Year 1 **free cash flow**?",
                expected=y1["Free cash flow"], unit="currency", rel_tol=0.0005,
                hints=["FCF = EBITDA - capex - increase in working capital.",
                       "Working capital went from -355k to about -367k: it became MORE negative, which "
                       "is a decrease, so it adds cash."],
                mistakes=[Mistake(y1["EBITDA"] - y1["Capital expenditure"] + y1["Change in working capital"],
                                  "Sign error on working capital. Subtract the CHANGE (a negative change adds cash).")],
                solution=f"{money(y1['EBITDA'])} - {money(y1['Capital expenditure'])} - ({money(y1['Change in working capital'])}) "
                         f"= {money(y1['Free cash flow'])}"),
            Exercise(
                id="m5l1_i2", skill="Forecasting & modelling",
                prompt=f"Opening cash is {money(a.opening_cash)} and Year 1 free cash flow is {money(y1['Free cash flow'])}. "
                       "What is Year 1 **closing cash** in this simplified model?",
                expected=y1["Closing cash"], unit="currency",
                hints=["Opening + FCF (no financing flows in this simplified model)."],
                solution=f"{money(y1['Closing cash'])}. In reality debt repayments, interest, tax and dividends "
                         "would reduce this."),
        ],
        interpretation="""
**What management does with this:** owners use the 3-year view to decide on capex, debt capacity
and dividends. Because it is driver-based, you can answer "what if occupancy is 2 points lower?" in
seconds and explain *why* the answer changes. Always state that a forecast is an estimate based
on assumptions, not a promise.
""",
        quiz=[
            Q("m5q1", "Which is a DRIVER rather than an output?", ["EBITDA", "Occupancy", "Free cash flow", "Closing cash"],
              1, "Occupancy is an assumption you set; the others are calculated.", "Forecasting & modelling"),
            Q("m5q2", "In a linked model, closing cash on the cash flow statement must equal...",
              ["Net income", "Cash on the balance sheet", "EBITDA", "Opening cash"], 1,
              "This is one of the standard three-statement checks.", "Forecasting & modelling"),
            Q("m5q3", "Capital expenditure appears...",
              ["In EBITDA", "Below EBITDA, as an investing cash outflow", "In revenue", "Nowhere"], 1,
              "Capex is not an operating expense; it is investment (depreciated over time).", "Forecasting & modelling"),
        ],
        task=PracticalTask(
            "m5t1", "Assumptions sheet for the 3-year forecast",
            "Open the Scenario & Sensitivity screen. Write down each Base assumption, where it comes from (FY "
            "actuals or judgement), and how confident you are (high/medium/low).",
            "Assumption | Value | Source | Confidence\nOccupancy Y1 | ... | ... | ...\nADR Y1 | ... | ... | ...\n...",
            ["Every driver listed", "Source stated for each", "Confidence is justified"], tool="scenario"),
    )

    l2 = Lesson(
        id="m5l2", title="Scenarios, sensitivity and model checks",
        concept="""
## Base, upside, downside
* **Base**: most likely view.
* **Upside / Downside**: plausible better or worse cases. Change several linked assumptions together
  (e.g. downside: occupancy -10%, ADR -5%, costs +3%).

## Sensitivity
Change **one** input at a time and see how much the output moves. Rank inputs by impact. That is the
"tornado" logic: spend your time validating the assumptions that matter most.

## Model checks and reconciliation
Professional models carry a **checks** block. Every check should be zero / TRUE:
* Totals = sum of parts (total revenue = rooms + ancillary)
* Identities hold (RevPAR = occupancy x ADR)
* Opening balance of a year = closing balance of the prior year
* Closing cash = opening cash + cash flow
If any check fails, stop and fix the error before you use the model.
""",
        worked_example=f"""
### Worked example: Downside Year 1

Downside multipliers: occupancy x0.90, ADR x0.95, other costs x1.03.
Occupancy {pct(a.occupancy[0])} → {pct(a.occupancy[0] * 0.9, 2)}; ADR {money(a.adr[0])} → {money(a.adr[0] * 0.95, 2)}.
Year 1 EBITDA falls from {money(y1['EBITDA'])} to {money(down['EBITDA'])}
(**{pct(down['EBITDA'] / y1['EBITDA'] - 1)}**) because revenue falls while fixed costs stay.
""",
        guided=Exercise(
            id="m5l2_g", skill="Forecasting & modelling",
            prompt=f"Downside Year 1: occupancy {pct(a.occupancy[0])} x 0.90 and ADR {money(a.adr[0])} x 0.95. "
                   "Calculate downside **RevPAR**.",
            steps=["New occupancy = 0.775 x 0.90.", "New ADR = 445 x 0.95.", "RevPAR = occupancy x ADR."],
            expected=down["RevPAR"], unit="currency",
            hints=[f"{a.occupancy[0] * 0.9:.4f} x {a.adr[0] * 0.95:.2f}"],
            mistakes=[Mistake(y1["RevPAR"], "That's the Base RevPAR. Apply both multipliers.")],
            solution=f"{pct(a.occupancy[0] * 0.9, 2)} x {money(a.adr[0] * 0.95, 2)} = {money(down['RevPAR'], 2)}"),
        independent=[
            Exercise(
                id="m5l2_i1", skill="Forecasting & modelling", practical=True,
                prompt="Use the Scenario & Sensitivity screen (or the model). By how much does Year 1 **EBITDA** change "
                       "if occupancy is **1 percentage point higher** each year, everything else Base?",
                expected=e_up - y1["EBITDA"], unit="currency", rel_tol=0.002,
                hints=["Extra sold rooms = 54,750 x 0.01 = 547.5.",
                       "Each extra room brings ADR x (1 + ancillary %) of revenue, minus $38 payroll and other costs "
                       "at 37.8% of that revenue."],
                solution=f"EBITDA rises by {money(e_up - y1['EBITDA'])}. That is the value of one occupancy point "
                         "and helps prioritise sales effort."),
            Exercise(
                id="m5l2_i2", skill="Forecasting & modelling", unit="choice",
                prompt="A check shows 'Year 2: Opening cash = Year 1 closing cash: difference 250,000'. "
                       "What is the most likely error?",
                choices=["Year 2 opening cash is typed in instead of linked", "ADR is too high",
                         "Occupancy is above 100%", "The tax rate is wrong"], expected=0,
                hints=["Opening balances should be formulas pointing at the prior year's closing balance."],
                solution="A hard-coded opening balance breaks the link between years. Replace it with a reference."),
        ],
        interpretation="""
**What management does with this:** present the Base case with the range (downside to upside), name
the two or three assumptions that drive most of the risk, and say what would have to be true for
the downside to happen. That is far more useful than a single precise-looking number.
""",
        quiz=[
            Q("m5q4", "A one-way sensitivity changes...", ["All inputs at once", "One input at a time",
                                                          "Only costs", "Only the discount rate"], 1,
              "One at a time, so you can see each input's own impact.", "Forecasting & modelling"),
            Q("m5q5", "A model check shows a non-zero difference. You should...",
              ["Round it away", "Investigate and fix before using the model", "Hide the check", "Ignore if small"], 1,
              "Small differences often signal a broken link that will grow.", "Forecasting & modelling"),
            Q("m5q6", "Why does EBITDA fall by a larger % than revenue in the downside?",
              ["Taxes rise", "Fixed costs do not fall with revenue", "Capex rises", "Depreciation rises"], 1,
              "Operating leverage: fixed costs stay while revenue falls.", "Forecasting & modelling"),
        ],
        task=PracticalTask(
            "m5t2", "Scenario summary for the owner",
            "Run Base, Upside and Downside in the Scenario screen and export the results. Summarise in 4-6 lines: "
            "range of Year 1-3 EBITDA, the most sensitive assumption, and whether all model checks pass.",
            "EBITDA range Y1: $... to $...\nMost sensitive assumption: ... because ...\nChecks: all pass / ...\n"
            "What would trigger the downside: ...",
            ["Range quoted from the exported file", "Sensitivity justified", "Check status stated",
             "Downside trigger is concrete"], tool="scenario"),
    )
    return Module("m5", 5, "Financial Modeling and Forecasting",
                  "Driver-based 3-year hotel forecast, cash flow, scenarios, sensitivity and model checks "
                  "(simplified training model, clearly labelled).", ["Forecasting & modelling"], [l1, l2],
                  tools=["scenario"])


# =================================================================== MODULE 6

def module6() -> Module:
    c = data().cases
    pr = c["restaurant_promotion"]
    cm_now = pr["current_price"] - pr["variable_cost_per_cover"]
    contrib_now = cm_now * pr["current_covers_per_month"]
    promo_price = pr["current_price"] * (1 - pr["discount_pct"])
    cm_promo = promo_price - pr["variable_cost_per_cover"]
    contrib_promo = cm_promo * pr["expected_covers_with_promo"] - pr["extra_marketing_cost"]
    need = m.discount_volume_needed(pr["current_price"], pr["variable_cost_per_cover"], pr["discount_pct"])
    ns = c["new_service"]
    ns_cm = ns["price_per_trip"] - ns["variable_cost_per_trip"]
    ns_profit = ns_cm * ns["expected_trips_per_month"] - ns["fixed_costs_per_month"]
    ns_be = m.break_even_units(ns["fixed_costs_per_month"], ns["price_per_trip"], ns["variable_cost_per_trip"])
    ip = c["investment_proposals"]
    A, B = ip["A"]["cash_flows"], ip["B"]["cash_flows"]

    l1 = Lesson(
        id="m6l1", title="Contribution, pricing and discount decisions",
        concept="""
## Think in contribution, not revenue
A promotion that increases revenue can still *reduce* profit. Compare **total contribution**:

`Total contribution = (Price - Variable cost) x Volume - Extra fixed costs (e.g. marketing)`

## How much extra volume does a discount need?
Each discounted unit contributes less, so you need more units just to stand still:

`Required volume increase = Old contribution per unit / New contribution per unit - 1`

At a 40% contribution margin, a 20% discount needs **+100%** volume to break even!

## Also consider
* **Cannibalisation**: guests who would have paid full price now pay less.
* **Incremental profit** = extra contribution - extra costs - contribution lost from cannibalisation.
* Capacity: can the kitchen and staff serve the extra covers?
* Brand: deep discounts can damage a luxury positioning.
""",
        worked_example="""
### Worked example (not the exercise data)

Spa treatment price $200, variable cost $70, 400 treatments/month. Proposed 15% discount, expected
460 treatments.
* Now: (200 - 70) x 400 = **$52,000**
* Promo: price $170, contribution $100 x 460 = **$46,000**. It is worse by $6,000.
* Needed volume: 130 / 100 - 1 = **+30%** (520 treatments). The forecast +15% is not enough.
""",
        guided=Exercise(
            id="m6l1_g", skill="Commercial analysis",
            prompt=f"{pr['name']}: price {money(pr['current_price'])}, variable cost {money(pr['variable_cost_per_cover'])} "
                   f"per cover, {pr['current_covers_per_month']:,} covers per month. What is the **current monthly "
                   "contribution**?",
            steps=["Contribution per cover = price - variable cost.", "Multiply by covers."],
            expected=contrib_now, unit="currency",
            hints=[f"({pr['current_price']:.0f} - {pr['variable_cost_per_cover']:.0f}) x {pr['current_covers_per_month']:,}"],
            mistakes=[Mistake(pr["current_price"] * pr["current_covers_per_month"], "That's revenue. Deduct variable cost.")],
            solution=f"{money(cm_now)} x {pr['current_covers_per_month']:,} = {money(contrib_now)}"),
        independent=[
            Exercise(
                id="m6l1_i1", skill="Commercial analysis", practical=True,
                prompt=f"The promotion gives a {pct(pr['discount_pct'], 0)} discount, is expected to lift covers to "
                       f"{pr['expected_covers_with_promo']:,} and costs {money(pr['extra_marketing_cost'])} in marketing. "
                       "What is monthly contribution **with** the promotion (after marketing)?",
                expected=contrib_promo, unit="currency",
                hints=[f"Promo price = {money(pr['current_price'])} x 0.80 = {money(promo_price, 2)}.",
                       f"Contribution per cover = {money(cm_promo, 2)}; x covers; minus marketing."],
                mistakes=[Mistake(cm_promo * pr["expected_covers_with_promo"], "You forgot the marketing cost.")],
                solution=f"{money(cm_promo, 2)} x {pr['expected_covers_with_promo']:,} - {money(pr['extra_marketing_cost'])} "
                         f"= {money(contrib_promo)} vs {money(contrib_now)} today: {money(contrib_promo - contrib_now)}."),
            Exercise(
                id="m6l1_i2", skill="Commercial analysis",
                prompt="What **% increase in covers** would the discount need just to keep contribution the same "
                       "(ignore the marketing cost)?",
                expected=need, unit="percent",
                hints=["Old contribution per cover / new contribution per cover - 1."],
                mistakes=[Mistake(pr["discount_pct"], "The volume needed is much more than the discount %, because "
                                                       "the discount comes entirely out of contribution.")],
                solution=f"{money(cm_now)} / {money(cm_promo, 2)} - 1 = {pct(need, 1)}. The promotion only expects "
                         f"+{pct(pr['expected_covers_with_promo'] / pr['current_covers_per_month'] - 1, 1)}."),
            Exercise(
                id="m6l1_i3", skill="Commercial analysis", unit="choice",
                prompt="Based on your numbers, what should management do with the promotion as designed?",
                choices=["Approve: revenue goes up", "Reject or redesign: contribution falls",
                         "Approve: covers go up", "Approve: marketing is cheap"], expected=1,
                hints=["Compare total contribution, not revenue or covers."],
                solution="Reject or redesign it, for example by limiting the offer to quiet nights (Mon-Wed) or offering "
                         "a value-add instead of a price cut."),
        ],
        interpretation="""
**What management does with this:** commercial finance's job is to make the trade-off visible
before money is spent. A better recommendation is usually a *redesigned* offer: restrict it to need
periods, add a minimum spend, or bundle a low-cost extra rather than cut price.
""",
        quiz=[
            Q("m6q1", "Price $100, variable cost $60. A 10% discount requires how much more volume to keep contribution equal?",
              ["10%", "20%", "33%", "50%"], 2, "Old CM 40, new CM 30; 40/30 - 1 = 33%.", "Commercial analysis"),
            Q("m6q2", "Cannibalisation means...",
              ["New customers attracted", "Existing full-price customers switching to the discount",
               "Higher costs", "Lower taxes"], 1, "Those guests would have paid full price anyway.", "Commercial analysis"),
            Q("m6q3", "Which metric decides whether a promotion adds profit?",
              ["Revenue", "Covers", "Incremental contribution", "Average check"], 2,
              "Revenue can rise while contribution falls.", "Commercial analysis"),
        ],
        task=PracticalTask(
            "m6t1", "Redesign the promotion",
            "Use the Business Case Evaluator ('Discount decision' tab) to test a redesigned offer (e.g. a smaller "
            "discount or quiet nights only). Record the inputs and the change in contribution, and write a "
            "recommendation.", "Original design: contribution change $...\nRedesign: ...\nInputs: ...\n"
                              "Result: contribution change $...\nRecommendation: ...",
            ["Uses the evaluator with stated inputs", "Compares with original", "Recommendation is specific"],
            tool="business_case"),
    )

    l2 = Lesson(
        id="m6l2", title="New services, investments, payback and ROI",
        concept="""
## Evaluating a new service
1. Contribution per unit = price - variable cost.
2. Monthly profit = contribution x volume - fixed costs.
3. **Break-even volume** = fixed costs / contribution per unit. Compare it with realistic demand.
4. **Margin of safety** = (expected - break-even) / expected.

## Comparing investments
* **Payback period**: years until cumulative cash flow turns positive. Simple, but ignores everything
  after payback and the time value of money.
* **ROI** = (total cash returned - investment) / investment. Also ignores timing.
* **NPV and IRR** (Module 7) fix these weaknesses. Use all of them, but decide with NPV.

## Business case checklist
Objective → options → assumptions (with sources) → financials (contribution, payback, NPV) → risks and
sensitivities → non-financial factors (guest experience, brand, staff) → recommendation.
""",
        worked_example="""
### Worked example: payback

Cash flows: -$500k today, then $150k, $200k, $250k.
Cumulative: -500 → -350 → -150 → +100. Payback happens in year 3: 2 + 150/250 = **2.6 years**.
ROI = (600 - 500) / 500 = **20%** over three years.
""",
        guided=Exercise(
            id="m6l2_g", skill="Commercial analysis",
            prompt=f"{ns['name']}: price {money(ns['price_per_trip'])}, variable cost {money(ns['variable_cost_per_trip'])} "
                   f"per trip, fixed costs {money(ns['fixed_costs_per_month'])} per month. How many trips per month to "
                   "**break even**? (1 decimal)",
            steps=["Contribution per trip = price - variable cost.", "Break-even = fixed costs / contribution."],
            expected=ns_be, unit="number", abs_tol=0.06,
            hints=[f"Contribution = {money(ns_cm)}"],
            solution=f"{money(ns['fixed_costs_per_month'])} / {money(ns_cm)} = {ns_be:.1f} trips"),
        independent=[
            Exercise(
                id="m6l2_i1", skill="Commercial analysis",
                prompt=f"Expected demand is {ns['expected_trips_per_month']} trips per month. What is the expected "
                       "**monthly profit** of the service?",
                expected=ns_profit, unit="currency",
                hints=["Contribution x trips - fixed costs."],
                solution=f"{money(ns_cm)} x {ns['expected_trips_per_month']} - {money(ns['fixed_costs_per_month'])} "
                         f"= {money(ns_profit)}. Margin of safety: "
                         f"{pct(m.margin_of_safety(ns['expected_trips_per_month'], ns_be))}."),
            Exercise(
                id="m6l2_i2", skill="Commercial analysis", practical=True,
                prompt=f"Proposal A ({ip['A']['name']}) cash flows: {', '.join(f'{x:,}' for x in A)}. What is its "
                       "**payback period** in years? (2 decimals)",
                expected=m.payback_period(A), unit="years",
                hints=["Track cumulative cash flow each year.", "Interpolate within the year it turns positive."],
                solution=f"Payback = {m.payback_period(A):.2f} years"),
            Exercise(
                id="m6l2_i3", skill="Commercial analysis", practical=True,
                prompt=f"Proposal B ({ip['B']['name']}) cash flows: {', '.join(f'{x:,}' for x in B)}. "
                       "What is its simple **ROI** over the 5 years?",
                expected=m.roi(sum(B[1:]), -B[0]), unit="percent",
                hints=["ROI = (sum of inflows - investment) / investment."],
                solution=f"({sum(B[1:]):,} - {-B[0]:,}) / {-B[0]:,} = {pct(m.roi(sum(B[1:]), -B[0]))}. "
                         f"Proposal A: {pct(m.roi(sum(A[1:]), -A[0]))}. Module 7 compares them properly with NPV."),
        ],
        interpretation="""
**What management does with this:** a short payback reduces risk; a high NPV creates more value.
When they disagree, explain the trade-off. Also check capacity, guest experience and execution
risk. A finance analyst recommends; management decides.
""",
        quiz=[
            Q("m6q4", "A key weakness of the payback period is that it...",
              ["Is hard to calculate", "Ignores cash flows after payback", "Uses NPV", "Needs a discount rate"], 1,
              "A project paying back fast could still create less value.", "Commercial analysis"),
            Q("m6q5", "Expected volume 160, break-even 118. Margin of safety ≈",
              ["26%", "42%", "74%", "118%"], 0, "(160 - 118) / 160 = 26%.", "Commercial analysis"),
            Q("m6q6", "Which belongs in a business case but is NOT a financial number?",
              ["Payback", "NPV", "Impact on guest experience", "ROI"], 2,
              "Non-financial factors matter and should be stated explicitly.", "Commercial analysis"),
        ],
        task=PracticalTask(
            "m6t2", "One-page business case: new service",
            "Use the Business Case Evaluator to model the airport transfer service. Write a one-page business case "
            "following the checklist above, ending with approve / reject / pilot.",
            "Objective: ...\nAssumptions: ...\nFinancials: contribution ..., break-even ..., monthly profit ...\n"
            "Risks: ...\nNon-financial: ...\nRecommendation: ...",
            ["All checklist sections present", "Numbers match the evaluator", "Clear decision"],
            tool="business_case"),
    )
    return Module("m6", 6, "Commercial Finance and Business Analysis",
                  "Contribution and pricing, discount decisions, CVP and break-even, new services, payback "
                  "and ROI, business cases.", ["Commercial analysis", "Cost behaviour & break-even"], [l1, l2],
                  tools=["business_case", "calculator"])


# =================================================================== MODULE 7

def module7() -> Module:
    c = data().cases
    ip = c["investment_proposals"]
    A, B, r = ip["A"]["cash_flows"], ip["B"]["cash_flows"], ip["discount_rate"]
    ren = c["renovation"]
    flows = ren["cash_flows"]
    ren_npv, ren_irr = m.npv(ren["discount_rate"], flows), m.irr(flows)
    d = dict(ren)
    d["adr_uplift"] = 12.0
    down = gen.renovation_cash_flows(d)
    down_npv = m.npv(ren["discount_rate"], down)

    l1 = Lesson(
        id="m7l1", title="Time value of money, NPV and IRR",
        concept="""
## Plain language first
**A dollar today is worth more than a dollar next year**, because today's dollar can be invested and
earn a return, and because the future is uncertain. To compare money at different times, convert
future amounts into today's money: this is **discounting**.

* **Present value**: PV = Future amount / (1 + r)^t. With r = 10%, $110 next year is worth $100 today.
* **Discount rate (r)**: the return investors require for this level of risk. For a hotel project it
  might be the company's cost of capital. In this course it is *given*.
* **NPV (Net Present Value)** = sum of all discounted cash flows, including the (negative) investment today.
  * NPV > 0: the project earns more than the required return, so it creates value.
  * NPV < 0: it destroys value at that discount rate.
* **IRR (Internal Rate of Return)**: the discount rate at which NPV = 0. It is the project's own return.
  Accept if IRR > required rate. When projects compete, prefer the one with the higher **NPV**.

## Excel note
`=NPV(rate, values)` discounts the **first** value too. For a project with an investment today use
`=CF0 + NPV(rate, CF1:CFn)`. `=IRR(CF0:CFn)` includes the investment.

> Valuations depend on forecasts and a chosen discount rate. They are estimates, never guarantees.
""",
        worked_example="""
### Worked example

Invest $1,000 today; receive $500 at the end of each of 3 years; r = 10%.

| Year | Cash flow | Discount factor 1/(1.1)^t | PV |
|---|---|---|---|
| 0 | -1,000 | 1.0000 | -1,000.00 |
| 1 | 500 | 0.9091 | 454.55 |
| 2 | 500 | 0.8264 | 413.22 |
| 3 | 500 | 0.7513 | 375.66 |
| | | **NPV** | **243.43** |

IRR ≈ **23.4%**: at that rate the PVs add up to exactly zero.
""",
        guided=Exercise(
            id="m7l1_g", skill="Investment appraisal",
            prompt="What is the **present value** of $100,000 received in 3 years at a 9% discount rate?",
            steps=["PV = FV / (1 + r)^t", "(1.09)^3 = 1.295029"],
            expected=m.present_value(100_000, 0.09, 3), unit="currency",
            hints=["100,000 / 1.09^3"], mistakes=[Mistake(100_000 * 1.09 ** 3, "You compounded forward. Divide to discount."),
                                                    Mistake(100_000 / 1.27, "Use (1.09)^3, not 1 + 3 x 9%.")],
            solution=f"100,000 / 1.295029 = {money(m.present_value(100_000, 0.09, 3), 2)}"),
        independent=[
            Exercise(
                id="m7l1_i1", skill="Investment appraisal", practical=True,
                prompt=f"Proposal A ({ip['A']['name']}): cash flows {', '.join(f'{x:,}' for x in A)} (year 0 first). "
                       f"Discount rate {pct(r, 0)}. What is the **NPV**?",
                expected=m.npv(r, A), unit="currency", rel_tol=0.0005, abs_tol=5,
                hints=["Discount each year's cash flow by (1.09)^t and add them, including -1,200,000 at t=0.",
                       "Excel: =-1200000 + NPV(9%, year1:year5)"],
                mistakes=[Mistake(m.excel_npv(r, A), "You discounted the year-0 investment too (Excel NPV trap). "
                                                     "Add CF0 outside NPV().")],
                solution=f"NPV = {money(m.npv(r, A), 2)}"),
            Exercise(
                id="m7l1_i2", skill="Investment appraisal", practical=True,
                prompt=f"Proposal B ({ip['B']['name']}): cash flows {', '.join(f'{x:,}' for x in B)}. What is its **IRR**?",
                expected=m.irr(B), unit="percent", abs_tol=0.0011,
                hints=["Find the rate where NPV = 0 (trial and error, the Business Case Evaluator, or =IRR() in Excel).",
                       "Try 15%, then 20%: is NPV positive or negative?"],
                solution=f"IRR = {pct(m.irr(B), 2)}"),
            Exercise(
                id="m7l1_i3", skill="Investment appraisal", unit="choice",
                prompt=f"A has NPV {money(m.npv(r, A))} and IRR {pct(m.irr(A))}; B has NPV {money(m.npv(r, B))} and IRR "
                       f"{pct(m.irr(B))}. Only one can be funded. Which creates more value?",
                choices=["A, higher NPV", "B, higher IRR", "Neither", "Both equally"],
                expected=0 if m.npv(r, A) > m.npv(r, B) else 1,
                hints=["When projects compete for the same funds, rank by NPV (value created in dollars)."],
                solution="Rank mutually exclusive projects by NPV. IRR favours smaller projects with fast returns."),
        ],
        interpretation="""
**What management does with this:** investment committees ask: does it beat our required return
(NPV > 0), how long until we get our money back (payback), and what if the assumptions are wrong
(sensitivity)? Present all three, recommend on NPV, and be honest about uncertainty.
""",
        quiz=[
            Q("m7q1", "NPV is positive. This means the project...",
              ["Is guaranteed to make money", "Earns more than the discount rate, on these forecasts",
               "Has an IRR below the discount rate", "Pays back in one year"], 1,
              "Positive NPV only holds if the forecasts hold.", "Investment appraisal"),
            Q("m7q2", "As the discount rate rises, NPV of a normal project...", ["Rises", "Falls", "Doesn't change", "Becomes IRR"],
              1, "Future inflows are worth less today.", "Investment appraisal"),
            Q("m7q3", "IRR is the discount rate at which...", ["NPV = 0", "Payback = 1", "ROI = 0", "Cash flow = 0"], 0,
              "By definition.", "Investment appraisal"),
        ],
        task=PracticalTask(
            "m7t1", "Investment committee note: A vs B",
            "Use the Business Case Evaluator ('Compare investments') for proposals A and B. Write a short note with "
            "NPV, IRR, payback for both and your recommendation.",
            "A: NPV $..., IRR ..%, payback .. yrs\nB: NPV $..., IRR ..%, payback .. yrs\nRecommendation: ...\nKey risk: ...",
            ["All three metrics for both", "Recommends on NPV with reasoning", "States a risk"], tool="business_case"),
    )

    l2 = Lesson(
        id="m7l2", title="Renovation project: scenarios, risk and capital allocation",
        concept="""
## Building project cash flows
Only **incremental** cash flows count: the difference between doing the project and not doing it.
For a room renovation:
`Incremental rooms revenue = Revenue with renovation - Revenue without`
`Incremental cash flow = Incremental revenue x Flow-through %` (the share reaching profit after
variable costs). Add any residual value at the end and subtract the investment at the start.

## Risk and uncertainty
* **Scenario analysis**: recompute NPV for a downside (smaller ADR uplift, delays, cost overruns).
* **Sensitivity**: which assumption flips the decision? Find the **break-even uplift** where NPV = 0.
* **Capital allocation**: money is limited, so compare NPV per dollar invested (profitability index)
  and strategic fit.
* **Forecast uncertainty**: the further out the cash flows, the less certain. Never present an NPV
  as a fact; present it as "on these assumptions".
""",
        worked_example=f"""
### Worked example: renovation assumptions

{ren['name']}: capex {money(ren['capex'])}; ADR uplift {money(ren['adr_uplift'])} on a base of {money(ren['base_adr'])};
occupancy uplift {ren['occupancy_uplift_pts'] * 100:.1f} points on {pct(ren['base_occupancy'], 0)}; flow-through
{pct(ren['flow_through'], 0)}; {ren['years']} years; residual value {money(ren['terminal_value_year7'])} in year 7;
discount rate {pct(ren['discount_rate'], 0)}.

Revenue without: 54,750 x {ren['base_occupancy']} x {ren['base_adr']:g} = {money(54750 * ren['base_occupancy'] * ren['base_adr'])}
Revenue with: 54,750 x {ren['base_occupancy'] + ren['occupancy_uplift_pts']:.3f} x {ren['base_adr'] + ren['adr_uplift']:.0f}
= {money(54750 * (ren['base_occupancy'] + ren['occupancy_uplift_pts']) * (ren['base_adr'] + ren['adr_uplift']))}
""",
        guided=Exercise(
            id="m7l2_g", skill="Investment appraisal", practical=True,
            prompt="Using the worked example, what is the **annual incremental cash flow** (years 1-7, before "
                   "residual value)?",
            steps=["Incremental revenue = revenue with - revenue without.", "Multiply by the 70% flow-through."],
            expected=flows[1], unit="currency",
            hints=["Subtract the two revenue figures above, then x 0.70."],
            mistakes=[Mistake(flows[1] / ren["flow_through"], "That's incremental revenue. Apply the 70% flow-through.")],
            solution=f"Annual incremental cash flow = {money(flows[1], 2)}"),
        independent=[
            Exercise(
                id="m7l2_i1", skill="Investment appraisal", practical=True,
                prompt=f"Cash flows: year 0 {money(flows[0])}, years 1-6 {money(flows[1], 2)}, year 7 {money(flows[7], 2)} "
                       f"(includes residual). Discount rate {pct(ren['discount_rate'], 0)}. **NPV**?",
                expected=ren_npv, unit="currency", abs_tol=5, rel_tol=0.0005,
                hints=["Discount each year by 1.10^t and add.", "Or use the Business Case Evaluator."],
                mistakes=[Mistake(m.excel_npv(ren["discount_rate"], flows), "Year-0 investment must not be discounted.")],
                solution=f"NPV = {money(ren_npv, 2)}; IRR = {pct(ren_irr, 2)}"),
            Exercise(
                id="m7l2_i2", skill="Investment appraisal", practical=True,
                prompt="Downside: the ADR uplift is only **$12** (everything else unchanged). What is the downside **NPV**?",
                expected=down_npv, unit="currency", abs_tol=5, rel_tol=0.0005,
                hints=["Recalculate revenue with ADR base + 12, the incremental cash flow, then NPV.",
                       f"Downside annual cash flow = {money(down[1], 2)}"],
                solution=f"Downside NPV = {money(down_npv, 2)}"),
            Exercise(
                id="m7l2_i3", skill="Investment appraisal", unit="choice",
                prompt="Given base and downside NPV, the most responsible recommendation is:",
                choices=["Approve, NPV is guaranteed positive",
                         "Approve with conditions: validate the ADR uplift (e.g. pilot floor) and control capex",
                         "Reject, any risk is unacceptable", "Delay forever"], expected=1,
                hints=["The decision depends heavily on the ADR uplift assumption."],
                solution=("The project creates value in the base case, but it is sensitive to the ADR uplift. "
                          "Recommend approval subject to evidence: renovate a pilot floor and test rates first.")),
        ],
        interpretation="""
**What management does with this:** large capex is approved in stages. A good analyst shows the
base NPV, the downside, the **break-even assumption** (what ADR uplift gives NPV = 0) and a way to
reduce risk (pilot, phasing, fixed-price contracts). That turns a yes/no into a managed decision.
""",
        quiz=[
            Q("m7q4", "Which cash flow should NOT be in a renovation NPV?",
              ["Capex", "Incremental room profit", "Room revenue the hotel earns anyway",
               "Residual value"], 2, "Only incremental cash flows count.", "Investment appraisal"),
            Q("m7q5", "Flow-through of 70% means...",
              ["70% of incremental revenue becomes incremental profit", "70% occupancy", "70% of capex is spent",
               "Costs rise 70%"], 0, "The remaining 30% covers variable costs of the extra business.",
              "Investment appraisal"),
            Q("m7q6", "The best way to reduce the risk of a wrong ADR uplift assumption is to...",
              ["Raise the discount rate to 50%", "Pilot one floor and measure", "Ignore it", "Use IRR instead"], 1,
              "Evidence reduces uncertainty before the full commitment.", "Investment appraisal"),
        ],
        task=PracticalTask(
            "m7t2", "Renovation recommendation with sensitivity",
            "In the Business Case Evaluator ('Renovation' tab), find the ADR uplift at which NPV is about zero. "
            "Write a recommendation for the owner including base NPV, downside NPV, break-even uplift and "
            "conditions.", "Base NPV: $...  IRR: ..%\nDownside NPV ($12 uplift): $...\nBreak-even ADR uplift: $...\n"
                         "Recommendation and conditions: ...\nLimitations of this analysis: ...",
            ["Base and downside quoted", "Break-even uplift found", "Conditions are practical",
             "States that results are estimates"], tool="business_case"),
    )
    return Module("m7", 7, "Financial Decision-Making",
                  "Time value of money, discounting, NPV, IRR, scenario and sensitivity analysis, risk and "
                  "capital allocation for a hotel renovation.", ["Investment appraisal"], [l1, l2],
                  tools=["business_case", "calculator"])


# =================================================================== MODULE 8

def module8() -> Module:
    ds = data()
    q4 = ds.monthly_rooms[ds.monthly_rooms.month >= 10]
    q4b = ds.rooms_budget[ds.rooms_budget.month >= 10]
    revpar_a = m.revpar(q4.room_revenue.sum(), q4.available_room_nights.sum())
    revpar_b = m.revpar(q4b.budget_room_revenue.sum(), q4b.available_room_nights.sum())
    p = ds.pnl
    gop = float(p[p.line == "Gross operating profit (GOP)"].actual.sum())
    rev = float(p[p.line == "Total revenue"].actual.sum())

    l1 = Lesson(
        id="m8l1", title="Dashboards, KPI selection and financial storytelling",
        concept="""
## Choosing KPIs
A good KPI is **relevant** to the decision-maker, **controllable** by them, **comparable** (vs budget,
last year) and **timely**. For a hotel general manager a core set is:
*Occupancy, ADR, RevPAR, Total revenue vs budget, GOP and GOP margin, Payroll % of revenue,
Pace vs last year.*

## Dashboard design
* 4-8 KPIs at the top with actual, budget and variance, colour-coded F/U.
* One trend chart (e.g. RevPAR by month vs budget) and one breakdown (variance by line).
* Same scales and periods throughout; label units; no decoration that hides data.

## Storytelling with numbers: what → why → what next → so what
1. **What happened** (the number vs the benchmark).
2. **Why** (the driver, with evidence).
3. **What might happen next** (forecast, risks).
4. **What we should do** (action, owner, impact).
These are the four questions this whole course trains you to answer.
""",
        worked_example=f"""
### Worked example: a headline

Weak: "Q4 RevPAR was {money(revpar_a, 2)}."
Strong: "Q4 RevPAR was {money(revpar_a, 2)}, {pct(abs(revpar_a / revpar_b - 1))} below budget, because weekday corporate
demand fell and was replaced with discounted OTA business. Pace for January is also behind last year. We
recommend a corporate re-engagement campaign and a direct-booking member rate to recover share."
""",
        guided=Exercise(
            id="m8l1_g", skill="Management reporting", practical=True,
            prompt=f"Q4 (Oct-Dec): actual room revenue {money(q4.room_revenue.sum(), 2)}, available room nights "
                   f"{q4.available_room_nights.sum():,}; budget room revenue {money(q4b.budget_room_revenue.sum(), 2)}, "
                   f"budget available room nights {q4b.available_room_nights.sum():,}. What is the **RevPAR variance %** vs budget?",
            steps=["Actual RevPAR = actual revenue / actual available.", "Budget RevPAR = budget revenue / budget available.",
                   "Variance % = actual / budget - 1."],
            expected=revpar_a / revpar_b - 1, unit="percent",
            hints=[f"Actual RevPAR {money(revpar_a, 2)}; budget RevPAR {money(revpar_b, 2)}."],
            solution=f"{money(revpar_a, 2)} / {money(revpar_b, 2)} - 1 = {pct(revpar_a / revpar_b - 1, 2)}"),
        independent=[
            Exercise(
                id="m8l1_i1", skill="Management reporting",
                prompt=f"FY total revenue {money(rev)}, GOP {money(gop)}. What is the **GOP margin**?",
                expected=gop / rev, unit="percent", hints=["GOP / Total revenue"],
                solution=f"{pct(gop / rev, 2)}"),
            Exercise(
                id="m8l1_i2", skill="Management reporting", unit="choice",
                prompt="Which KPI set is best for a monthly dashboard for the General Manager?",
                choices=["Share price, P/E ratio, dividend yield",
                         "Occupancy, ADR, RevPAR, revenue vs budget, GOP margin, payroll % of revenue",
                         "Number of emails sent, meetings held", "Every line of the P&L"], expected=1,
                hints=["Relevant, controllable, comparable, timely."],
                solution="Operational KPIs the GM controls, compared with budget."),
        ],
        interpretation="""
**What management does with this:** executives scan a dashboard in under a minute. If your headline
and the first KPI row don't tell the story, the report has failed, however correct the numbers.
""",
        quiz=[
            Q("m8q1", "Which is NOT a good KPI property?", ["Relevant", "Controllable", "Comparable", "Ambiguous"], 3,
              "KPIs must be clearly defined.", "Management reporting"),
            Q("m8q2", "The order of a good financial story is...",
              ["Why → what → so what", "What happened → why → what next → what to do",
               "Methodology → data → appendix", "Chart → table → chart"], 1, "Lead with the result.",
              "Management reporting"),
            Q("m8q3", "On a dashboard, colour should mainly be used to...",
              ["Decorate", "Highlight favorable/unfavorable variances", "Match the logo", "Fill space"], 1,
              "Colour should carry meaning.", "Management reporting"),
        ],
        task=PracticalTask(
            "m8t1", "Build and export a management dashboard",
            "Open the Capstone screen, step 6 (dashboard), select your KPIs and export the dashboard image. "
            "Paste your three-sentence headline below.", "Headline (what / why / what next): ...\nKPIs chosen and why: ...",
            ["Dashboard exported", "Headline follows what/why/next", "KPI choice justified"], tool="capstone"),
    )

    l2 = Lesson(
        id="m8l2", title="Recommendations, presenting and interview readiness",
        concept="""
## Writing a recommendation
Structure (fits on one page):
1. **Recommendation** in one sentence, up front.
2. **Why**: 2-3 supporting facts with numbers.
3. **Financial impact** and how it was estimated.
4. **Assumptions and limitations**: what you assumed and what you could not verify.
5. **Risks** and how to monitor or mitigate them.
6. **Next steps**: owner and date.

## Presenting to management
Answer the question asked. Know your three key numbers by heart. When challenged, separate fact
from assumption: "Our data shows X. We are *assuming* Y, and if Y is wrong the impact is Z."
Saying "I don't know, I'll check and come back by Thursday" is better than guessing.

## Interview preparation
Roles: **Revenue Analyst / Assistant Revenue Manager** (pricing, forecasting, channels),
**FP&A Analyst** (budgets, forecasts, variance analysis, reporting) and **Commercial Finance Analyst**
(pricing, business cases, profitability). Expect technical questions (formulas, NPV), case questions
("RevPAR is down 8%, what do you look at?") and behavioural questions. Use **STAR**: Situation, Task,
Action, Result. Your hotel operations and loss-prevention background is an asset: you understand
how the numbers are produced and controlled.

> Completing this training is **not** a professional certification and does **not** guarantee
> employment. It gives you practised skills and work samples to discuss in interviews.
""",
        worked_example="""
### Worked example: assumptions and limitations paragraph

"This forecast assumes January demand follows last year's pickup pattern and that competitor rates
stay stable. It does not include group business still under negotiation. If pickup is 10% weaker, room
revenue would be about $X lower. We will review pace weekly and update the forecast on the 15th."
""",
        guided=Exercise(
            id="m8l2_g", skill="Management reporting", unit="choice",
            prompt="Which executive summary opening is best?",
            choices=["This report was prepared using data from several systems and covers many areas...",
                     "We recommend approving the renovation subject to a one-floor pilot: base NPV is positive, but "
                     "the result depends on achieving the ADR uplift.",
                     "Revenue is a key metric in hotels. There are many ways to analyse revenue.",
                     "Please see the attached 40 tabs."], expected=1,
            steps=["Look for the option that states the recommendation first.", "Does it give the key reason and condition?"],
            hints=["Lead with the answer."], solution="Option 2: recommendation, reason and condition in one sentence."),
        independent=[
            Exercise(
                id="m8l2_i1", skill="Management reporting", unit="choice",
                prompt="The owner asks: 'So we will definitely make $X next year?' The best answer is:",
                choices=["Yes, guaranteed.", "It's our best estimate based on stated assumptions; the range is $A-$B, and the "
                         "main risk is weekday corporate demand.", "No idea.", "Ask the revenue manager."], expected=1,
                hints=["Forecasts are estimates. Give the range and the key risk."],
                solution="Never present a forecast as guaranteed; give the range and the main driver of risk."),
            Exercise(
                id="m8l2_i2", skill="Management reporting", unit="choice",
                prompt="In an interview you're asked 'RevPAR is down 8% vs last year. What do you look at first?' "
                       "The strongest first step is:",
                choices=["Split RevPAR into occupancy and ADR, then by segment/channel and day of week",
                         "Cut prices immediately", "Blame the market", "Check the staff rota"], expected=0,
                hints=["Decompose the KPI before acting."], solution="Decompose: occupancy vs rate, then segment, "
                                                                     "channel, day-of-week and compset."),
        ],
        interpretation="""
**What management does with this:** managers act on recommendations they understand and trust.
Clear structure, honest limitations and a specific next step make your work usable. That is what
hiring managers look for in junior analysts.
""",
        quiz=[
            Q("m8q4", "STAR stands for...", ["Situation, Task, Action, Result", "Strategy, Tactics, Analysis, Review",
                                             "Start, Talk, Answer, Repeat", "Sales, Trends, ADR, RevPAR"], 0,
              "Use it for behavioural questions.", "Management reporting"),
            Q("m8q5", "Which belongs in 'limitations'?",
              ["Our recommendation", "Data we could not verify or factors not modelled", "The company logo", "The NPV formula"], 1,
              "Be transparent about what the analysis cannot tell you.", "Management reporting"),
            Q("m8q6", "Completing this simulator means you are...",
              ["Certified as a revenue manager", "Guaranteed a job", "Practised in core analyst tasks, with work samples to discuss",
               "An accountant"], 2, "It is training, not certification.", "Management reporting"),
        ],
        task=PracticalTask(
            "m8t2", "Interview practice: three answers",
            "Choose three questions from the Interview Questions list (Reference screen): one technical, one case and one "
            "behavioural. Write your answers. For the behavioural question use STAR and draw on your hotel operations "
            "or loss-prevention experience.", "Q1 (technical): ...\nAnswer: ...\n\nQ2 (case): ...\nAnswer: ...\n\n"
                                               "Q3 (behavioural, STAR): ...\nSituation: ...\nTask: ...\nAction: ...\nResult: ...",
            ["Technical answer is accurate", "Case answer decomposes the problem", "STAR structure used",
             "Links past experience to the role"], tool="reference"),
    )
    return Module("m8", 8, "Management Reporting and Job Readiness",
                  "Dashboards, KPI selection, storytelling, writing recommendations, presenting and interview "
                  "preparation. Ends with the capstone project.", ["Management reporting"], [l1, l2],
                  tools=["capstone", "reference"])
