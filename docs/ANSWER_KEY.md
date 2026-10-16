# Instructor answer key

Finance & Commercial Training Simulator. All data is fictional. Answers are generated from the same code the app uses to check students, and selected values are verified by independent hand calculations in the automated tests (`tests/test_content.py`).

Tolerance: percentages ±0.06 percentage points; currency ±$0.60 or 0.05%; numbers ±0.01 or 0.05% unless noted. Equivalent formats (75%, 0.75, 75) are accepted.

## Module 1: Financial Foundations

### The three financial statements

**Guided `m1l1_g`** (Financial statements)

> FY2025: total revenue $25,699,378, profit before tax $2,259,074. Calculate the **pre-tax profit margin** (as a %).

- **Answer:** 8.79%
- **Working:** $2,259,074 / $25,699,378 = 8.79%
- **Common wrong answers:** 27.8%: You used EBITDA. The question asks for profit before tax, which is after depreciation and interest.; 6.6%: You used net income (after tax). Use profit before tax.

**Independent `m1l1_i1`** (Financial statements)

> At 31 Dec 2025 the hotel's total assets are $66,004,305 and total liabilities are $30,150,000. What is total **equity**?

- **Answer:** $35,854,305.00
- **Working:** $66,004,305 - $30,150,000 = $35,854,305
- **Common wrong answers:** $96,154,305.00: You added. Equity is what is LEFT after liabilities, so subtract.

**Independent `m1l1_i2`** (Financial statements)

> A department has revenue of $800,000, cost of sales of $260,000, operating expenses (excluding depreciation) of $310,000 and depreciation of $45,000. What is **operating profit (EBIT)**?

- **Answer:** $185,000.00
- **Working:** Gross profit 540,000 - opex 310,000 = EBITDA 230,000 - depreciation 45,000 = EBIT $185,000
- **Common wrong answers:** $230,000.00: That is EBITDA. Operating profit (EBIT) is after depreciation.; $540,000.00: That is gross profit. Keep going down the P&L.

**Quiz**

1. Which statement shows the company's position at a single date? → **Balance sheet**. The balance sheet is a snapshot at one date. The other two cover a period.
2. EBITDA is profit before which items? → **Interest, tax, depreciation and amortisation**. The name says it: Earnings Before Interest, Tax, Depreciation and Amortisation.
3. A hotel buys a $40,000 kitchen oven with cash. Immediately after, total assets... → **Do not change**. Cash (an asset) falls and equipment (an asset) rises by the same amount. Nothing hits the P&L until the oven is depreciated.

**Practical task: Explain the year in five sentences.** Marking checklist: Uses the correct profit level in each sentence; Quotes at least three numbers; Avoids jargon or explains it; Ends with an action or a watch-point

### Profit vs cash, cost behaviour and break-even

**Guided `m1l2_g`** (Financial statements, practical)

> Harbor Lane Outfitters, full year: net income $432,847, depreciation $60,000. Receivables rose from $40,000 to $129,068, inventory from $90,000 to $354,000, payables changed from $35,000 to $28,975. Calculate **operating cash flow** for the year.

- **Answer:** $133,754.00
- **Working:** $432,847 + $60,000 - $89,068 - $264,000 + (-$6,025) = $133,754
- **Common wrong answers:** $145,804.00: Payables went DOWN. A fall in payables uses cash, so add the (negative) change instead of subtracting it.; $73,754.00: You forgot to add back depreciation, which is a non-cash expense.

**Independent `m1l2_i1`** (Cost behaviour & break-even)

> Skyline rooftop terrace (small commercial project): average spend $42 per guest, variable costs 34% of spend, fixed costs $18,000 per month. How many guests per month are needed to **break even**? (Answer to 1 decimal place.)

- **Answer:** 649.35
- **Working:** $18,000 / $27.72 = 649.4 guests. In practice you would plan for 650.
- **Common wrong answers:** 428.57: You divided by the price. Divide by the contribution per guest, because variable costs must be covered first.

**Independent `m1l2_i2`** (Financial statements)

> A supplier business has DSO of 42 days, DIO of 35 days and DPO of 30 days. What is its **cash conversion cycle** in days?

- **Answer:** 47.00
- **Working:** 42 + 35 - 30 = 47 days
- **Common wrong answers:** 107.00: You added DPO. Paying suppliers later *reduces* the cycle, so subtract it.

**Quiz**

1. Profit is rising but the bank balance is falling. The MOST likely cause is... → **Receivables and inventory are growing**. Growing receivables and inventory tie up cash, even though the sales already count as profit.
2. Which hotel cost is usually VARIABLE? → **Guest amenities per occupied room**. Amenities are consumed per occupied room, so they move with volume.
3. Price $50, variable cost $30, fixed costs $10,000. Break-even units =  → **500**. Contribution is $20, and 10,000 / 20 = 500 units.

**Practical task: Why profit is not cash: retailer memo.** Marking checklist: States both profit and operating cash flow; Identifies inventory build as the largest cause; Mentions slower customer payments (receivables); Actions are specific and measurable

## Module 2: Excel and Financial Modeling

### Formulas, references and model structure

**Guided `m2l1_g`** (Excel formulas)

> Cell C2 contains `=B2*$F$1`. You copy it to **C5**. Which formula appears in C5?

- **Answer:** =B5*$F$1
- **Working:** =B5*$F$1. The relative B2 moved 3 rows down and the absolute $F$1 stayed fixed.

**Independent `m2l1_i1`** (Excel formulas)

> Table: rows (Day type, Revenue): Weekday 12,000 · Weekend 18,500 · Weekday 11,400 · Weekend 19,200 · Weekday 10,900. What does `=SUMIFS(Revenue, DayType, "Weekend")` return?

- **Answer:** $37,700.00
- **Working:** 18,500 + 19,200 = 37,700
- **Common wrong answers:** $34,300.00: You added the weekday rows. The criterion is "Weekend".; $72,000.00: You added every row. SUMIFS filters first.

**Independent `m2l1_i2`** (Excel formulas)

> D5 (rooms sold) is 0 and D6 (revenue) is 0. What does `=IFERROR(D6/D5,"n/a")` show?

- **Answer:** n/a
- **Working:** D6/D5 is #DIV/0!, so IFERROR returns "n/a". That is the right display: ADR is undefined when nothing is sold, which is not the same as $0.

**Independent `m2l1_i3`** (Excel formulas)

> You want to copy `=C4*B1` across a row so that C4 moves but B1 stays fixed. The best version is:

- **Answer:** =C4*$B$1
- **Working:** =C4*$B$1

**Quiz**

1. Which reference stays exactly the same when copied anywhere? → **$B$2**. Both column and row are anchored.
2. Where should a growth-rate assumption live in a well-built model? → **In a labelled assumptions cell referenced by formulas**. One input cell, referenced everywhere, makes the model easy to update and audit.
3. =SUMIFS(F:F, C:C, "Weekend", E:E, ">=130") adds revenue for nights that are... → **Weekend AND at least 130 sold**. SUMIFS criteria must ALL be true.

**Practical task: Complete the Excel practice workbook (tasks 1-9).** Marking checklist: All of tasks 1-9 graded; Each mistake has a written fix; Uses cell references, not typed numbers

### Lookups, dates, checks and sensitivity tables

**Guided `m2l2_g`** (Excel formulas)

> In the sensitivity table above, what RevPAR appears for **82% occupancy and $455 ADR**?

- **Answer:** $373.10
- **Working:** 0.82 x $455 = $373.10
- **Common wrong answers:** $37,310.00: Use 0.82, not 82.

**Independent `m2l2_i1`** (Excel formulas)

> Budget table: A2:A13 = month names (Jan..Dec), C2:C13 = budget ADR. Which formula returns March's budget ADR in ANY Excel version?

- **Answer:** =INDEX(C2:C13, MATCH("Mar", A2:A13, 0))
- **Working:** =INDEX(C2:C13, MATCH("Mar", A2:A13, 0))

**Independent `m2l2_i2`** (Excel formulas)

> Cell A2 holds the date 14-Feb-2025. What number does `=DAY(EOMONTH(A2,0))` return?

- **Answer:** 28.00
- **Working:** EOMONTH gives 28-Feb-2025, so DAY returns 28.
- **Common wrong answers:** 14.00: That is DAY(A2). EOMONTH moves to the month end first.; 29.00: 2025 is not a leap year.; 31.00: That's March. Use offset 0.

**Independent `m2l2_i3`** (Excel formulas)

> A check cell holds `=ROUND(SUM(B2:B13)-B14,2)`. Months B2:B13 add up to 1,204,377.40 and the annual total in B14 is 1,204,737.40. What does the check show?

- **Answer:** -$360.00
- **Working:** 1,204,377.40 - 1,204,737.40 = -360.00. The check fails because the annual total was keyed with transposed digits.

**Quiz**

1. What does the 0 in MATCH("Mar", A2:A13, 0) do? → **Requires an exact match**. 0 = exact match. Without it MATCH assumes sorted data and can return a wrong row.
2. A model's balance check shows FALSE. You should... → **Find and fix the error before sending**. Checks exist to stop errors reaching decision-makers.
3. A scenario differs from a one-way sensitivity because it... → **Changes several related assumptions together**. A downside scenario might lower occupancy AND ADR AND raise costs at the same time.

**Practical task: Finish the workbook: lookups, flags and fill-down (tasks 10-16).** Marking checklist: Workbook grading shows tasks 10-16 attempted; Task 15 explained without jargon; Absolute reference explained correctly

## Module 3: Hotel Revenue Management

### Occupancy, ADR and RevPAR

**Guided `m3l1_g`** (Hotel KPIs, practical)

> October 2025: available room nights 4,639, sold 3,704, room revenue $1,626,712.66. Calculate October **RevPAR**.

- **Answer:** $350.66
- **Working:** $1,626,712.66 / 4,639 = $350.66
- **Common wrong answers:** $439.18: That's ADR (divided by SOLD rooms). RevPAR divides by AVAILABLE rooms.

**Independent `m3l1_i1`** (Hotel KPIs, practical)

> Using the October numbers above, calculate **occupancy %**.

- **Answer:** 79.84%
- **Working:** 3,704 / 4,639 = 79.84%
- **Common wrong answers:** 79.7%: You used 150 x 31. Available room nights already exclude out-of-order rooms.

**Independent `m3l1_i2`** (Hotel KPIs, practical)

> Budgeted October room revenue was $1,752,334.00. What is the room revenue **variance** (Actual - Budget)?

- **Answer:** -$125,621.34
- **Working:** $1,626,712.66 - $1,752,334.00 = -$125,621.34 (-7.2%), unfavorable.

**Independent `m3l1_i3`** (Hotel KPIs)

> On 2025-01-19 the property management system was down and the night audit shows 0 rooms sold and $0 revenue with 150+ rooms available. What ADR should the report show?

- **Answer:** n/a (undefined)
- **Working:** ADR is undefined when nothing is sold, so show n/a. Occupancy (0%) and RevPAR ($0) are still valid. Never fill in another day's ADR.

**Quiz**

1. 150 rooms, 120 sold, room revenue $48,000. RevPAR is... → **$320**. 48,000 / 150 = $320. (ADR would be 48,000 / 120 = $400.)
2. Monthly ADR should be calculated as... → **Total room revenue / total sold room nights**. Averaging daily ADRs gives every day equal weight regardless of rooms sold.
3. Occupancy rose from 70% to 77% and ADR fell from $440 to $400. RevPAR... → **Stayed the same**. 0.70 x $440 = $308 and 0.77 x $400 = $308. Volume gains exactly offset the lower rate. Profit may still fall, because more occupied rooms means more variable cost.

**Practical task: Monthly KPI table and commentary.** Marking checklist: Uses RevPAR, not revenue alone, to compare months; Quantifies the variance; Separates occupancy from rate

### Demand, segments, channels, pricing and forecasting

**Guided `m3l2_g`** (Revenue management decisions, practical)

> October OTA: 1,110 room nights, revenue $516,872.39, commission 18% ($93,037.03). Calculate the OTA **net ADR** after commission.

- **Answer:** $381.83
- **Working:** ($516,872.39 - $93,037.03) / 1,110 = $381.83
- **Common wrong answers:** $465.65: That is gross ADR. Deduct commission first.

**Independent `m3l2_i1`** (Revenue management decisions, practical)

> Booking pace for 1-30 January next year (see the RM simulator, 'Pace & forecast' tab, or datasets/hotel_booking_pace_jan2026.csv). Using the **pickup method** (OTB + last-year pickup, capped at 150 per night), how many room nights are forecast in total? (Total on the books today: 1,934; total last-year pickup: 917.)

- **Answer:** 2,851.00
- **Working:** Sum of nightly min(150, OTB + pickup) = 2,851 room nights.

**Independent `m3l2_i2`** (Revenue management decisions, practical)

> Using each night's forecast rooms x that night's OTB ADR, what is the forecast **room revenue** for the 30 nights? (Use the simulator's pace table.)

- **Answer:** $1,158,245.71
- **Working:** Sum over nights of forecast rooms x OTB ADR = $1,158,245.71. This is an estimate; actual pickup may differ from last year.

**Independent `m3l2_i3`** (Revenue management decisions)

> Base: occupancy 80%, ADR $430. You raise the rate by 8% and demand elasticity is -1.2. Using Occ_new = Occ x (1.08)^-1.2, what is the new **RevPAR**?

- **Answer:** $338.75
- **Working:** Occ = 0.80 x 1.08^-1.2 = 72.94%; ADR = $464.40; RevPAR = $338.75 vs $344.00 before. RevPAR falls slightly, but fewer occupied rooms also means lower variable cost.
- **Common wrong answers:** $371.52: You raised the price but kept occupancy at 80%. Demand responds to price.

**Independent `m3l2_i4`** (Revenue management decisions)

> Which statement best explains the Sep-Dec room revenue shortfall in the data?

- **Answer:** Weaker weekday corporate demand, with transient business shifting to OTAs at lower rates
- **Working:** Weekday (corporate) occupancy fell; OTA share and discounting rose. Weekends held up.

**Quiz**

1. OTB for next Tuesday is 90 rooms. Last year OTB at the same point was 95 and final was 120. Pickup forecast =  → **115**. 90 + (120 - 95) = 115.
2. A segment is ___, a channel is ___. → **who the guest is; how they booked**. Segments describe the guest (corporate, group); channels describe the booking route (OTA, direct).
3. Which is the most responsible way to present a 30-day revenue forecast? → **With its method, key assumption and a range**. Forecasts are estimates. Show the method, the main assumption and a sensible range.

**Practical task: January pricing recommendation.** Marking checklist: Recommendation is specific (dates/segment/rate); Uses pace data as evidence; Quantifies impact with the simulator; States at least two risks

## Module 4: FP&A and Budgeting

### Budgets, variances and flexible budgets

**Guided `m4l1_g`** (Budgeting & variance analysis, practical)

> FY *Rooms other expenses* (amenities, laundry, commissions): actual $2,397,937, budget $2,119,337. Calculate the **variance %**.

- **Answer:** 13.15%
- **Working:** $278,600 / $2,119,337 = 13.15%. Unfavorable: costs above plan, mainly OTA commissions.
- **Common wrong answers:** -13.1%: Sign reversed: it's Actual - Budget.; 11.6%: Divide by BUDGET, not actual.

**Independent `m4l1_i1`** (Budgeting & variance analysis, practical)

> Use the FP&A Lab's variance table (full year). Which line has the **largest unfavorable variance** in dollars?

- **Answer:** Rooms revenue
- **Working:** Rooms revenue: -$662,016. The top 3 are Rooms revenue (-$662,016), Rooms other expenses ($278,600), Food & beverage revenue (-$171,821).

**Independent `m4l1_i2`** (Budgeting & variance analysis)

> Housekeeping budget: fixed $42,000 per month + $9.50 per occupied room. Budget volume 3,900 rooms; actual 3,600 rooms; actual cost $78,900. What is the **flexible budget** cost at actual volume?

- **Answer:** $76,200.00
- **Working:** 42,000 + 9.50 x 3,600 = $76,200. Actual $78,900 is $2,700 Unfavorable vs flexible budget. The static budget ($79,050) would wrongly show it as favorable.
- **Common wrong answers:** $79,050.00: That is the static budget (3,900 rooms). Flex to the actual 3,600.

**Independent `m4l1_i3`** (Budgeting & variance analysis)

> Using the October worked example, a manager asks: how much of the revenue gap is due to **rate** (ADR)? Give the rate effect in dollars.

- **Answer:** -$25,271.34
- **Working:** Rate effect = -$25,271.34
- **Common wrong answers:** -$26,806.45: Multiply by ACTUAL rooms, otherwise volume and rate won't add up to the total.

**Quiz**

1. Payroll: actual $510k, budget $480k. The variance is... → **$30k Unfavorable**. Expense above budget = unfavorable. 30 / 480 = 6.25% U.
2. Why use a flexible budget? → **To compare costs at the same activity level**. Variable costs should move with volume; flexing isolates real over- or under-spending.
3. Volume effect + price effect =  → **Total revenue variance**. The split explains the whole variance.

**Practical task: Top three unfavorable variances.** Marking checklist: Correct three lines identified; Each has a data-based driver; Each has a practical action

### Payroll, revised forecasts and management reporting

**Guided `m4l2_g`** (Budgeting & variance analysis, practical)

> Forecast next month's F&B payroll: 57 FTE at an average $3,950 per month, plus 340 overtime hours at $38.00/hour.

- **Answer:** $238,070.00
- **Working:** 225,150 + 12,920 = $238,070
- **Common wrong answers:** $225,150.00: You forgot overtime.

**Independent `m4l2_i1`** (Forecasting & modelling, practical)

> Budgeted room revenue for Oct-Dec is $4,603,799.00. At the end of September you expect demand to be **12% below budget** for those three months, at budget rates. What is the revised Oct-Dec room revenue forecast?

- **Answer:** $4,051,343.12
- **Working:** $4,603,799.00 x 0.88 = $4,051,343.12
- **Common wrong answers:** $552,455.88: That's the reduction, not the revised forecast.

**Independent `m4l2_i2`** (Forecasting & modelling)

> A department has revenue $1,000,000, variable costs 40% of revenue and fixed costs $350,000. If revenue falls 10%, by what **% does profit fall**?

- **Answer:** 24.00%
- **Working:** Before $250,000; after $190,000; fall $60,000 = 24%. That's operating leverage.
- **Common wrong answers:** 10.0%: Profit does not fall by the same % as revenue, because fixed costs don't flex.

**Quiz**

1. Which month should stay as ACTUAL in a revised forecast prepared at the end of September? → **September**. Closed months use actuals; only remaining months are re-forecast.
2. The best first line of a management report is... → **A one-sentence headline answering 'how did we do and why'**. Lead with the answer.
3. Overtime hours doubled while headcount is below budget. The most likely fix is... → **Fill vacancies / improve scheduling**. Overtime premium usually costs more than filling the role.

**Practical task: Revised forecast and one-page management report.** Marking checklist: Revised forecast exported; Report leads with a headline; Three variances explained; Actions have owners or dates

## Module 5: Financial Modeling and Forecasting

### Model architecture and a 3-year hotel forecast

**Guided `m5l1_g`** (Forecasting & modelling, practical)

> Using the Year 1 table above: payroll = $6,200,000 fixed + $38 per sold room night; other operating costs = 37.8% of total revenue; fixed charges $1,080,000. Calculate Year 1 **EBITDA**.

- **Answer:** $7,432,531.01
- **Working:** $26,245,850 - $7,812,388 - $9,920,931 - $1,080,000 = $7,432,531
- **Common wrong answers:** $8,512,531.01: You forgot the fixed charges (insurance and property tax).

**Independent `m5l1_i1`** (Forecasting & modelling, practical)

> Year 1 EBITDA is $7,432,531. Capex is 4% of total revenue ($26,245,850). Working capital moves from -$355,522 to -$367,442. What is Year 1 **free cash flow**?

- **Answer:** $6,394,616.91
- **Working:** $7,432,531 - $1,049,834 - (-$11,920) = $6,394,617
- **Common wrong answers:** $6,370,777.12: Sign error on working capital. Subtract the CHANGE (a negative change adds cash).

**Independent `m5l1_i2`** (Forecasting & modelling)

> Opening cash is $3,979,827 and Year 1 free cash flow is $6,394,617. What is Year 1 **closing cash** in this simplified model?

- **Answer:** $10,374,443.91
- **Working:** $10,374,444. In reality debt repayments, interest, tax and dividends would reduce this.

**Quiz**

1. Which is a DRIVER rather than an output? → **Occupancy**. Occupancy is an assumption you set; the others are calculated.
2. In a linked model, closing cash on the cash flow statement must equal... → **Cash on the balance sheet**. This is one of the standard three-statement checks.
3. Capital expenditure appears... → **Below EBITDA, as an investing cash outflow**. Capex is not an operating expense; it is investment (depreciated over time).

**Practical task: Assumptions sheet for the 3-year forecast.** Marking checklist: Every driver listed; Source stated for each; Confidence is justified

### Scenarios, sensitivity and model checks

**Guided `m5l2_g`** (Forecasting & modelling)

> Downside Year 1: occupancy 77.5% x 0.90 and ADR $445 x 0.95. Calculate downside **RevPAR**.

- **Answer:** $294.87
- **Working:** 69.75% x $422.75 = $294.87
- **Common wrong answers:** $344.88: That's the Base RevPAR. Apply both multipliers.

**Independent `m5l2_i1`** (Forecasting & modelling, practical)

> Use the Scenario & Sensitivity screen (or the model). By how much does Year 1 **EBITDA** change if occupancy is **1 percentage point higher** each year, everything else Base?

- **Answer:** $189,839.11
- **Working:** EBITDA rises by $189,839. That is the value of one occupancy point and helps prioritise sales effort.

**Independent `m5l2_i2`** (Forecasting & modelling)

> A check shows 'Year 2: Opening cash = Year 1 closing cash: difference 250,000'. What is the most likely error?

- **Answer:** Year 2 opening cash is typed in instead of linked
- **Working:** A hard-coded opening balance breaks the link between years. Replace it with a reference.

**Quiz**

1. A one-way sensitivity changes... → **One input at a time**. One at a time, so you can see each input's own impact.
2. A model check shows a non-zero difference. You should... → **Investigate and fix before using the model**. Small differences often signal a broken link that will grow.
3. Why does EBITDA fall by a larger % than revenue in the downside? → **Fixed costs do not fall with revenue**. Operating leverage: fixed costs stay while revenue falls.

**Practical task: Scenario summary for the owner.** Marking checklist: Range quoted from the exported file; Sensitivity justified; Check status stated; Downside trigger is concrete

## Module 6: Commercial Finance and Business Analysis

### Contribution, pricing and discount decisions

**Guided `m6l1_g`** (Commercial analysis)

> Sunset Bistro two-course promotion: price $68, variable cost $26 per cover, 2,400 covers per month. What is the **current monthly contribution**?

- **Answer:** $100,800.00
- **Working:** $42 x 2,400 = $100,800
- **Common wrong answers:** $163,200.00: That's revenue. Deduct variable cost.

**Independent `m6l1_i1`** (Commercial analysis, practical)

> The promotion gives a 20% discount, is expected to lift covers to 2,950 and costs $3,500 in marketing. What is monthly contribution **with** the promotion (after marketing)?

- **Answer:** $80,280.00
- **Working:** $28.40 x 2,950 - $3,500 = $80,280 vs $100,800 today: -$20,520.
- **Common wrong answers:** $83,780.00: You forgot the marketing cost.

**Independent `m6l1_i2`** (Commercial analysis)

> What **% increase in covers** would the discount need just to keep contribution the same (ignore the marketing cost)?

- **Answer:** 47.89%
- **Working:** $42 / $28.40 - 1 = 47.9%. The promotion only expects +22.9%.
- **Common wrong answers:** 20.0%: The volume needed is much more than the discount %, because the discount comes entirely out of contribution.

**Independent `m6l1_i3`** (Commercial analysis)

> Based on your numbers, what should management do with the promotion as designed?

- **Answer:** Reject or redesign: contribution falls
- **Working:** Reject or redesign it, for example by limiting the offer to quiet nights (Mon-Wed) or offering a value-add instead of a price cut.

**Quiz**

1. Price $100, variable cost $60. A 10% discount requires how much more volume to keep contribution equal? → **33%**. Old CM 40, new CM 30; 40/30 - 1 = 33%.
2. Cannibalisation means... → **Existing full-price customers switching to the discount**. Those guests would have paid full price anyway.
3. Which metric decides whether a promotion adds profit? → **Incremental contribution**. Revenue can rise while contribution falls.

**Practical task: Redesign the promotion.** Marking checklist: Uses the evaluator with stated inputs; Compares with original; Recommendation is specific

### New services, investments, payback and ROI

**Guided `m6l2_g`** (Commercial analysis)

> Airport limousine transfer: price $145, variable cost $62 per trip, fixed costs $9,800 per month. How many trips per month to **break even**? (1 decimal)

- **Answer:** 118.07
- **Working:** $9,800 / $83 = 118.1 trips

**Independent `m6l2_i1`** (Commercial analysis)

> Expected demand is 160 trips per month. What is the expected **monthly profit** of the service?

- **Answer:** $3,480.00
- **Working:** $83 x 160 - $9,800 = $3,480. Margin of safety: 26.2%.

**Independent `m6l2_i2`** (Commercial analysis, practical)

> Proposal A (Spa expansion (4 treatment rooms)) cash flows: -1,200,000, 260,000, 300,000, 330,000, 350,000, 360,000. What is its **payback period** in years? (2 decimals)

- **Answer:** 3.89 years
- **Working:** Payback = 3.89 years

**Independent `m6l2_i3`** (Commercial analysis, practical)

> Proposal B (Meeting room conversion) cash flows: -800,000, 240,000, 240,000, 230,000, 220,000, 200,000. What is its simple **ROI** over the 5 years?

- **Answer:** 41.25%
- **Working:** (1,130,000 - 800,000) / 800,000 = 41.2%. Proposal A: 33.3%. Module 7 compares them properly with NPV.

**Quiz**

1. A key weakness of the payback period is that it... → **Ignores cash flows after payback**. A project paying back fast could still create less value.
2. Expected volume 160, break-even 118. Margin of safety ≈ → **26%**. (160 - 118) / 160 = 26%.
3. Which belongs in a business case but is NOT a financial number? → **Impact on guest experience**. Non-financial factors matter and should be stated explicitly.

**Practical task: One-page business case: new service.** Marking checklist: All checklist sections present; Numbers match the evaluator; Clear decision

## Module 7: Financial Decision-Making

### Time value of money, NPV and IRR

**Guided `m7l1_g`** (Investment appraisal)

> What is the **present value** of $100,000 received in 3 years at a 9% discount rate?

- **Answer:** $77,218.35
- **Working:** 100,000 / 1.295029 = $77,218.35
- **Common wrong answers:** $129,502.90: You compounded forward. Divide to discount.; $78,740.16: Use (1.09)^3, not 1 + 3 x 9%.

**Independent `m7l1_i1`** (Investment appraisal, practical)

> Proposal A (Spa expansion (4 treatment rooms)): cash flows -1,200,000, 260,000, 300,000, 330,000, 350,000, 360,000 (year 0 first). Discount rate 9%. What is the **NPV**?

- **Answer:** $27,780.78
- **Working:** NPV = $27,780.78
- **Common wrong answers:** $25,486.95: You discounted the year-0 investment too (Excel NPV trap). Add CF0 outside NPV().

**Independent `m7l1_i2`** (Investment appraisal, practical)

> Proposal B (Meeting room conversion): cash flows -800,000, 240,000, 240,000, 230,000, 220,000, 200,000. What is its **IRR**?

- **Answer:** 13.17%
- **Working:** IRR = 13.17%

**Independent `m7l1_i3`** (Investment appraisal)

> A has NPV $27,781 and IRR 9.8%; B has NPV $85,629 and IRR 13.2%. Only one can be funded. Which creates more value?

- **Answer:** B, higher IRR
- **Working:** Rank mutually exclusive projects by NPV. IRR favours smaller projects with fast returns.

**Quiz**

1. NPV is positive. This means the project... → **Earns more than the discount rate, on these forecasts**. Positive NPV only holds if the forecasts hold.
2. As the discount rate rises, NPV of a normal project... → **Falls**. Future inflows are worth less today.
3. IRR is the discount rate at which... → **NPV = 0**. By definition.

**Practical task: Investment committee note: A vs B.** Marking checklist: All three metrics for both; Recommends on NPV with reasoning; States a risk

### Renovation project: scenarios, risk and capital allocation

**Guided `m7l2_g`** (Investment appraisal, practical)

> Using the worked example, what is the **annual incremental cash flow** (years 1-7, before residual value)?

- **Answer:** $836,251.50
- **Working:** Annual incremental cash flow = $836,251.50
- **Common wrong answers:** $1,194,645.00: That's incremental revenue. Apply the 70% flow-through.

**Independent `m7l2_i1`** (Investment appraisal, practical)

> Cash flows: year 0 -$4,500,000, years 1-6 $836,251.50, year 7 $1,736,251.50 (includes residual). Discount rate 10%. **NPV**?

- **Answer:** $33,064.85
- **Working:** NPV = $33,064.85; IRR = 10.20%
- **Common wrong answers:** $30,058.95: Year-0 investment must not be discounted.

**Independent `m7l2_i2`** (Investment appraisal, practical)

> Downside: the ADR uplift is only **$12** (everything else unchanged). What is the downside **NPV**?

- **Answer:** -$1,412,946.83
- **Working:** Downside NPV = -$1,412,946.83

**Independent `m7l2_i3`** (Investment appraisal)

> Given base and downside NPV, the most responsible recommendation is:

- **Answer:** Approve with conditions: validate the ADR uplift (e.g. pilot floor) and control capex
- **Working:** The project creates value in the base case, but it is sensitive to the ADR uplift. Recommend approval subject to evidence: renovate a pilot floor and test rates first.

**Quiz**

1. Which cash flow should NOT be in a renovation NPV? → **Room revenue the hotel earns anyway**. Only incremental cash flows count.
2. Flow-through of 70% means... → **70% of incremental revenue becomes incremental profit**. The remaining 30% covers variable costs of the extra business.
3. The best way to reduce the risk of a wrong ADR uplift assumption is to... → **Pilot one floor and measure**. Evidence reduces uncertainty before the full commitment.

**Practical task: Renovation recommendation with sensitivity.** Marking checklist: Base and downside quoted; Break-even uplift found; Conditions are practical; States that results are estimates

## Module 8: Management Reporting and Job Readiness

### Dashboards, KPI selection and financial storytelling

**Guided `m8l1_g`** (Management reporting, practical)

> Q4 (Oct-Dec): actual room revenue $4,207,423.43, available room nights 13,774; budget room revenue $4,603,799.00, budget available room nights 13,800. What is the **RevPAR variance %** vs budget?

- **Answer:** -8.44%
- **Working:** $305.46 / $333.61 - 1 = -8.44%

**Independent `m8l1_i1`** (Management reporting)

> FY total revenue $25,699,378, GOP $8,988,806. What is the **GOP margin**?

- **Answer:** 34.98%
- **Working:** 34.98%

**Independent `m8l1_i2`** (Management reporting)

> Which KPI set is best for a monthly dashboard for the General Manager?

- **Answer:** Occupancy, ADR, RevPAR, revenue vs budget, GOP margin, payroll % of revenue
- **Working:** Operational KPIs the GM controls, compared with budget.

**Quiz**

1. Which is NOT a good KPI property? → **Ambiguous**. KPIs must be clearly defined.
2. The order of a good financial story is... → **What happened → why → what next → what to do**. Lead with the result.
3. On a dashboard, colour should mainly be used to... → **Highlight favorable/unfavorable variances**. Colour should carry meaning.

**Practical task: Build and export a management dashboard.** Marking checklist: Dashboard exported; Headline follows what/why/next; KPI choice justified

### Recommendations, presenting and interview readiness

**Guided `m8l2_g`** (Management reporting)

> Which executive summary opening is best?

- **Answer:** We recommend approving the renovation subject to a one-floor pilot: base NPV is positive, but the result depends on achieving the ADR uplift.
- **Working:** Option 2: recommendation, reason and condition in one sentence.

**Independent `m8l2_i1`** (Management reporting)

> The owner asks: 'So we will definitely make $X next year?' The best answer is:

- **Answer:** It's our best estimate based on stated assumptions; the range is $A-$B, and the main risk is weekday corporate demand.
- **Working:** Never present a forecast as guaranteed; give the range and the main driver of risk.

**Independent `m8l2_i2`** (Management reporting)

> In an interview you're asked 'RevPAR is down 8% vs last year. What do you look at first?' The strongest first step is:

- **Answer:** Split RevPAR into occupancy and ADR, then by segment/channel and day of week
- **Working:** Decompose: occupancy vs rate, then segment, channel, day-of-week and compset.

**Quiz**

1. STAR stands for... → **Situation, Task, Action, Result**. Use it for behavioural questions.
2. Which belongs in 'limitations'? → **Data we could not verify or factors not modelled**. Be transparent about what the analysis cannot tell you.
3. Completing this simulator means you are... → **Practised in core analyst tasks, with work samples to discuss**. It is training, not certification.

**Practical task: Interview practice: three answers.** Marking checklist: Technical answer is accurate; Case answer decomposes the problem; STAR structure used; Links past experience to the role

## Module 2 Excel workbook

| # | Cell | Model formula | Expected value |
|---|---|---|---|
| 1 | Exercises!D5 | `=SUM('Raw Data'!E2:E32)` | 3,071.00 |
| 2 | Exercises!D6 | `=SUM('Raw Data'!F2:F32)` | $1,188,419.86 |
| 3 | Exercises!D7 | `=SUM('Raw Data'!D2:D32)` | 4,641.00 |
| 4 | Exercises!D8 | `=D5/D7` | 66.2% |
| 5 | Exercises!D9 | `=IFERROR(D6/D5,0)` | $386.98 |
| 6 | Exercises!D10 | `=D6/D7` | $256.07 |
| 7 | Exercises!D11 | `=SUMIFS('Raw Data'!F2:F32,'Raw Data'!C2:C32,"Weekend")` | $405,599.36 |
| 8 | Exercises!D12 | `=SUMIFS('Raw Data'!E2:E32,'Raw Data'!C2:C32,"Weekday")` | 2,101.00 |
| 9 | Exercises!D13 | `=D11/SUMIFS('Raw Data'!E2:E32,'Raw Data'!C2:C32,"Weekend")` | $418.14 |
| 10 | Exercises!D14 | `=INDEX(Budget!C2:C13,MATCH("Jan",Budget!A2:A13,0))` | $385.00 |
| 11 | Exercises!D15 | `=D9-D14` | $1.98 |
| 12 | Exercises!D16 | `=IF(D8<Budget!B2,"Below budget","On or above budget")` | On or above budget |
| 13 | Exercises!D17 | `=COUNTIFS('Raw Data'!E2:E32,">=130")` | 0.00 |
| 14 | Exercises!D18 | `=AVERAGEIFS('Raw Data'!E2:E32,'Raw Data'!C2:C32,"Weekday")` | 95.50 |
| 15 | Exercises!D19 | `=D6*(1+Assumptions!B4)*(1+Assumptions!B4)^Assumptions!B5` | $1,176,879.62 |
| 16 | Raw Data!I2 | `=F2/SUM($F$2:$F$32)` | per row: F_n / SUM(F2:F32) |

Accepted alternatives: XLOOKUP instead of INDEX/MATCH (task 10); SUMIF/SUMPRODUCT for SUMIFS tasks; COUNTIF for task 13.

## Capstone

Pass mark 70/100. Numeric and choice items are auto-scored; written items get an automatic structure score. Instructors should also judge quality with the rubric below.

| Step | Item | Points | Expected |
|---|---|---|---|
| 1. Clean and validate the data | How many duplicate rows are there? | 2 | 1.00 |
| 1. Clean and validate the data | Which month is missing sold room nights? | 2 | Mar |
| 1. Clean and validate the data | Which month's room revenue is in thousands? | 2 | Aug |
| 1. Clean and validate the data | Which month has impossible occupancy (sold > available)? | 2 | Oct |
| 1. Clean and validate the data | Corrected full-year ROOM revenue ($) | 2 | $18,444,817.88 |
| 2. Calculate the required KPIs | Full-year occupancy % | 5 | 77.3% |
| 2. Calculate the required KPIs | Full-year ADR ($) | 5 | $437.90 |
| 2. Calculate the required KPIs | Full-year RevPAR ($) | 5 | $338.33 |
| 3. Build a forecast | Forecast January room revenue ($) | 6 | $1,086,099.88 |
| 3. Build a forecast | Method and limitation (2-4 sentences) | 4 | See rubric |
| 4. Explain budget variances | Full-year TOTAL revenue variance, Actual - Budget ($) | 5 | -$882,654.12 |
| 4. Explain budget variances | Largest unfavorable variance | 5 | Room revenue |
| 4. Explain budget variances | Explain the two biggest unfavorable variances and their drivers | 5 | See rubric |
| 5. Evaluate two commercial decisions | A: change in monthly contribution ($) | 4 | -$20,520.00 |
| 5. Evaluate two commercial decisions | A: decision | 3 | Reject or redesign (e.g. quiet nights only) |
| 5. Evaluate two commercial decisions | B: renovation NPV at 10% ($) | 4 | $33,064.85 |
| 5. Evaluate two commercial decisions | B: decision | 4 | Approve subject to a pilot floor and capex control |
| 6. Prepare a management dashboard | KPI selection | 6 | ADR, EBITDA vs budget, Occupancy %, Payroll % of revenue, RevPAR, Total revenue vs budget |
| 6. Prepare a management dashboard | Dashboard exported | 4 | See rubric |
| 7. Write a one-page executive recommendation | Executive recommendation | 15 | See rubric |
| 8. Simulated management meeting | General Manager: 'Why is room revenue below budget in the last quarter?' | 2 | Weekday corporate demand fell and was replaced by lower-rated OTA business; weekends held |
| 8. Simulated management meeting | Owner: 'Can you guarantee the renovation returns at least 10%?' | 2 | No. On our assumptions NPV at 10% is positive, but it depends mainly on the ADR uplift; a pilot floor reduces that risk |
| 8. Simulated management meeting | Director of Finance: 'Payroll is over budget even though occupancy was under. What would you check?' | 2 | Split into headcount, average cost and overtime; flex variable departments to occupancy |
| 8. Simulated management meeting | Director of Sales: 'Should we cut rates 15% across the board in January?' | 2 | No. Target weak weekday dates and the corporate segment, protect strong weekends, and test with the elasticity scenario |
| 8. Simulated management meeting | Owner: 'What is the single most important action for next quarter?' | 2 | Recover weekday corporate demand and shift transient share from OTA to direct |

### Qualitative rubric for written work (instructor use)

- **Executive recommendation (15):** recommendation first (3); supported by 3+ correct numbers (3); drivers explained with evidence (3); risks and mitigations (3); assumptions/limitations and next steps with owners (3).
- **Variance explanation (5):** identifies room revenue (weekday corporate demand, OTA shift) and other operating expenses (commissions, utilities tariff, July chiller repair) with numbers.
- **Forecast method (4):** states the ratio method, that it assumes Q4 under-performance persists into January, and that it ignores bookings on hand (pickup data would improve it).

### Data issues built into the capstone raw file

- Duplicate row: Jun
- Missing sold room nights: Mar (rebuild = revenue / reported ADR)
- Room revenue keyed in thousands: Aug
- Sold > available (transposed digits): Oct (rebuild = revenue / reported ADR)
