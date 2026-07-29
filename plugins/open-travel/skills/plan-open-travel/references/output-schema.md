# Standardized option output

Keep the answer concise enough to compare without hiding evidence.

## Option rules

- Target three to five materially distinct, complete, eligible plans.
- Use stable display IDs `A` through `E`; do not expose internal plan IDs as
  the primary choice.
- Consider five roles: `recommended`, `lowest-cost`, `fastest`, `low-hassle`,
  and `comfort`.
- Merge role badges when one plan wins several roles. Never repeat an
  itinerary to make the list look longer.
- Return one or two options when that is all the evidence supports and explain
  why more were not eligible.
- Keep incomplete or constraint-failing candidates out of the ranked option
  list.

## 1. Search summary

- request and defaults;
- hard constraints;
- sources queried and sources skipped;
- retrieval time window;
- whether browser data was used.

## 2. Option comparison

Use a table with:

| ID | Positioning | Complete cost | Door-to-door | Transfers | Stay | Main risk | Evidence |
|---|---|---:|---:|---:|---|---|---|

Never sort an incomplete subtotal as though it were a complete total.

Order rows by recommendation usefulness, not blindly by price. Make the option
ID and positioning visible before the details.

## 3. Option cards

Use this field order for every option:

```text
### A — <short title> [Recommended] [Lowest cost]
Best for: <traveler or priority>
Route: <door-to-door summary>
Time: <local departure/arrival, duration, transfers>
Complete cost: <currency total> or <known subtotal + missing fields>
Cost breakdown: <transport + access + stay + required extras>
Includes: <tax, baggage, seat, accommodation-fee scope>
Advantages: <one or two concrete advantages>
Tradeoffs: <one or two concrete costs or risks>
Evidence: <provider, retrieval time, price status, direct link>
```

Omit a badge that does not apply, but do not omit fields silently. Write
`Unknown` plus the verification action when a material field is absent.

## 4. Missing data

List only missing facts that could change the recommendation. Say what would need to be re-queried or manually verified.

## 5. Estimated comparison

When no complete ranking is possible, or when partial candidates remain useful,
show a separate table headed `Known cost + estimated range`. Use IDs `R1`
through `R5`, and include known subtotal, range, estimated fields, still-unknown
fields, and evidence quality. Never mix these rows into A–E or give them primary
role badges.

## 6. Choice prompt

End with one compact instruction:

```text
Reply with A/B/C to expand that option, or name two IDs to compare them.
```

Use only IDs that were actually presented. Do not imply that replying books or
holds anything.

## Source placement

Place provider, timestamp, method, status, and direct link near the supported claim. Avoid a detached source dump that makes provenance hard to follow.
