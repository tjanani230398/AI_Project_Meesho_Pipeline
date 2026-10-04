# Narrative Report: Ethnic Wear Swings and Top Resellers

All figures come from the verified Part 1 outputs (`monthly_category_revenue.csv`,
`region_revenue.csv`, `top_resellers.csv`) and the Part 2 engine. Revenue includes orders of
every status (delivered, returned, cancelled and pending). The two Ethnic Wear blocks follow
the rules in `prompt_pack.md`: only supplied numbers, every claim labelled, no reseller
names.

---

## 3.2 Worked narratives

### Narrative A: Ethnic Wear, May vs. April (+77.1%, flagged)

**Context.** This update looks at Ethnic Wear revenue in May vs. April. Any month-on-month
change above 8.0% in either direction is reviewed.

**Insight.** [Fact] Ethnic Wear revenue rose from INR 104,520.77 in April to INR 185,107.61
in May, a change of 77.1%. [Fact] Orders rose from 64 to 104 over the same period.

**Implication.** [Hypothesis] The jump may reflect a May-specific demand driver, such as a
festive or promotional push, because orders and revenue rose together; the figures alone do
not show why. [Action] Ask the regional leads whether any Ethnic Wear promotion or festive
stocking ran in May; if none did, find another explanation before May is used as a planning
baseline. [Action] Split May's INR 185,107.61 by order status; if delivered revenue is much
lower, treat the 77.1% as overstated.

### Narrative B: Ethnic Wear, June vs. May (-58.74%, flagged)

**Context.** This update looks at Ethnic Wear revenue in June vs. May. Any month-on-month
change above 8.0% in either direction is reviewed.

**Insight.** [Fact] Ethnic Wear revenue fell from INR 185,107.61 in May to INR 76,371.53 in
June, a change of -58.74%. [Fact] Orders fell from 104 to 52 over the same period.

**Implication.** [Hypothesis] The fall may be the May driver ending, rather than a new
weakness, because orders and revenue fell together; the figures alone do not show why.
[Action] Ask the regional leads whether the May Ethnic Wear promotion or festive demand ended,
and whether any June stock shortage held back Ethnic Wear orders. [Action] Compare June's
Ethnic Wear orders with May's region by region: a drop concentrated in one region points to a
local problem to fix, while an even drop across regions points to demand returning to normal.

### Self-score against the refinement checklist

| Criterion | Score | Why |
|---|---|---|
| Specificity | Pass | Both blocks name Ethnic Wear and the exact months, and every figure (INR 104,520.77, INR 185,107.61, INR 76,371.53, 77.1%, -58.74%, orders 64, 104, 52) matches the verified Part 1 and Part 2 output. |
| Audience fit | Pass | Written in plain business language for a regional manager, with no SQL or analyst terms, and each block is under 150 words. |
| Completeness | Pass | Each block has a Context (what and which period), an Insight (labelled [Fact] numbers) and an Implication (a [Hypothesis] plus [Action] items). |
| Actionability | Pass | Each block names concrete checks (promotion or festive stocking in May, an order-status split of May revenue, June stock shortages, a region-by-region order comparison) and what each result would change. |

---

## Top-reseller narrative (masked, safe for external-facing summaries)

**Context.** This update looks at which resellers spent the most across April to June. Seventeen
resellers spent more than INR 50,000 in total; the five highest are shown, identified only by
region and coded alias. Spend includes orders of every status.

**Insight.** [Fact] ALIAS-19 (West) spent INR 75,295.09, ALIAS-22 (West) INR 73,882.33,
ALIAS-12 (South) INR 69,936.46, ALIAS-06 (North) INR 64,238.97 and ALIAS-05 (North)
INR 61,825.02. [Fact] The five sit in three regions: West, North and South.

**Implication.** [Hypothesis] The two West leaders may be ordering more often or in larger
baskets than other resellers; the totals alone do not show which. [Action] Ask the West and
North regional managers to compare the order history of ALIAS-19, ALIAS-22, ALIAS-06 and
ALIAS-05 by category and month against the other resellers in their region, and report
whether the lead comes from order frequency or order size. [Action] Because these totals
include returned and cancelled orders, re-run the ranking on delivered orders only before
any reseller recognition or incentive is decided.

---

## 3.3 Chart-choice justification (text only)

**Q1. "Which month had the highest total revenue?"** (April INR 419,417.43, May INR 444,594.25,
June INR 398,055.24). Two variables are involved, month and total revenue, so this is a
bivariate comparison of one category against one number. I would use a simple vertical bar
chart with three bars. The question is "which is highest", not "how is it trending", so bars
beat a line, which would imply a trend from only three points. The y-axis must start at zero:
May leads April by only about 6%, and a truncated axis would make the gap look far larger than
it is. The May bar is highlighted in a strong colour with April and June in a neutral grey,
and each bar carries its value, so the answer reads within 10 seconds. There is a single
series, so no legend, and no 3D effects, which distort bar heights.

**Q2. "What percentage share does Ethnic Wear represent of April's total revenue?"**
(INR 104,520.77 of INR 419,417.43 = 24.92%). This is a univariate part-to-whole question:
one measure (revenue) in one month, split across the five categories. I would use a
horizontal bar chart of each category's share of April revenue, sorted from largest to
smallest, with Ethnic Wear highlighted and labelled 24.92%. The axis starts at zero, there is
one series so no legend (category names sit directly on the bars), and nothing is 3D. A pie
or donut is the obvious alternative, but the three largest shares (27.15%, 24.92% and 23.95%)
are close, and comparing angles is slower and less accurate than comparing bar lengths, so a
pie would fail the 10-second test. If a pie is required, keep it to these five slices, label
them directly and never render it in 3D. The sorted bars also show that Ethnic Wear is the
second-largest category, behind Western Wear.

**Q3. "How do the four regions compare on total revenue?"** (North INR 337,125.46, West
INR 333,106.33, South INR 316,736.68, East INR 275,098.45). Two variables, region and total
revenue, make this bivariate. I would use a bar chart with four bars sorted from highest to
lowest, a y-axis starting at zero, one neutral colour, and no legend because there is one
series. North and West are close, so each bar needs a data label to be read at a glance, and
the sorting makes the ranking obvious within 10 seconds. If the manager later asks for regions
by month, that adds a third variable (multivariate); a grouped bar chart with one series per
month would then be justified, and only then does a legend earn its place. It should still be
a flat 2D chart.
