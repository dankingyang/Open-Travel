# Ranking rules

Run `scripts/evaluate_plans.py` after converting candidates to the plan schema.

## Complete cost

The evaluator sums:

```text
transport fare + taxes + baggage + required seat fees
+ origin access + destination egress
+ stay + stay taxes + cleaning + city tax
+ late transport + extra nights + other required costs
```

Any `required_cost_fields` value that is missing or `null` makes the total incomplete. The evaluator reports a known subtotal and missing fields instead of inventing a total.

## Auxiliary estimated comparison

Strict complete totals remain the only inputs to the Pareto frontier and A–E
role ranking. If an incomplete plan provides defensible `cost_estimates` ranges
for every missing required field, the evaluator may return it separately under
`estimated_options`.

- Show known subtotal, estimated range, and estimated fields.
- Sort by range midpoint only inside the auxiliary section.
- Do not assign `recommended`, `lowest-cost`, or other primary badges.
- Do not claim budget compliance from an estimated range.
- Omit plans whose missing fields lack defensible ranges.

## Risk labels

The deterministic rules flag:

- self-transfer;
- separate tickets;
- airport or station changes;
- checked-bag reclaim;
- short domestic or international connections;
- red-eye or very early departures;
- arrival after the last public transport;
- arrival after lodging check-in;
- single-source or incomplete evidence;
- missing required costs.

Risk points order candidates; labels and reasons must still be shown to the user.

## Hard constraints

Filter candidates before recommendation. Supported constraints are documented in `request-schema.md`. An incomplete total cannot prove compliance with `max_total_cost`.

## Pareto frontier

A plan dominates another only when it is no worse on:

- complete total cost;
- duration;
- risk points;
- comfort score (higher is better);

and strictly better on at least one. Incomplete totals do not enter the normal Pareto frontier.

## Representative roles

- `recommended`: normalized weighted comparison of cost, duration, risk, and
  discomfort.
- `lowest-cost`: lowest complete total, then lower risk and duration.
- `fastest`: shortest door-to-door duration, then lower risk and total.
- `low-hassle`: fewest transfers, then lower risk, walking, and duration.
- `comfort`: lowest risk, then highest comfort, fewer transfers, and shorter
  duration.

Select role winners independently, then merge badges for roles won by the same
plan. Add other Pareto candidates by balanced score only when needed to reach
three distinct options. Return at most five. If fewer than three eligible
complete plans exist, return fewer and explain why.
