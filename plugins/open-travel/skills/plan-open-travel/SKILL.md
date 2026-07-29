---
name: plan-open-travel
description: Plan transparent, affordable worldwide door-to-door travel. Use when Codex needs to compare flights, rail, intercity bus, ferry, stays, activities, trails, local transit, weather, or exchange rates; route searches through installed travel plugins and current web sources; calculate complete costs and connection risks; or present a standardized set of sourced travel options without booking.
---

# Plan with Open Travel

Build travel plans from traceable live sources. Use installed travel plugins for
search and keep local code limited to deterministic validation and ranking.

## Boundaries

- Query, compare, explain, and provide links. Never book, pay, cancel, or modify an order.
- Never implement price history, tracking, alerts, or buy-now advice.
- Do not store passwords, identity documents, payment data, or browser sessions.
- Never present generated, cached, partial, or estimated numbers as a live complete price.
- Never bypass login, CAPTCHA, paywall, rate limit, robots policy, or another access control.

## Workflow

1. Build a `TripRequest`.
   - Require origin, destination, and a usable date or trip-length window.
   - Default missing traveler count to one adult and disclose the default.
   - Ask only for missing facts that block the first search.
   - Separate hard constraints from preferences.
   - Read [request-schema.md](references/request-schema.md).

2. Discover and announce sources.
   - Read [tool-routing.md](references/tool-routing.md).
   - Read [provider-availability.md](references/provider-availability.md) when
     deciding between a bundled MCP and a host marketplace plugin.
   - Discover callable plugin and MCP tools before promising a provider.
   - Prefer bundled, verified provider-operated public MCPs. Use installed
     Skyscanner, Trip.com, Klook, and Wikiloc plugins only where no public
     portable provider MCP is available or the official MCP requires separate
     partner authorization.
   - On hosts without those marketplace plugins, continue through current
     official web sources or the documented generic fallback. Do not make Codex
     marketplace availability a requirement for the Skill.
   - If a useful plugin is disconnected, suggest connecting it without blocking
     other useful work.
   - Tell the user which providers will be queried and whether a browser is planned.
   - Run independent compatible searches in parallel and preserve per-source failures.

3. Search through provider tools.
   - Read [provider-quirks.md](references/provider-quirks.md) for every provider
     used in the request.
   - For rail, intercity bus, coach, or ferry, read
     [surface-transport.md](references/surface-transport.md).
   - For accommodation search through trivago, read
     [trivago.md](references/trivago.md).
   - Use fixed-date tools for exact dates and flexible-date tools for ranges.
   - Use 12306 for mainland-China rail and Trip.com where its rail supplier
     covers the route. Use Trip.com, Kiwi, or Skyscanner for flights according
     to their tool-specific constraints.
   - For rail, bus, or ferry without adequate structured coverage, search the
     internet automatically, discover the operator, and verify the result on a
     current official operator, authority, station, terminal, or port page.
   - Use trivago for hotel comparison. Establish an unfiltered, market-compatible
     baseline and validate destination resolution before adding filters.
   - Use Klook for bookable activities and Wikiloc for outdoor trail discovery.
   - Treat validation, open-data coverage, supplier coverage, and provider failures as source
     statuses. Never translate them into route, inventory, or property absence.
   - Do not restore the retired flight aggregator or provider wrappers.

4. Fill only uncovered gaps.
   - Read [local-capabilities.md](references/local-capabilities.md) before using
     any bundled script.
   - For weather or exchange rates, read [public-data.md](references/public-data.md)
     and run `scripts/public_data.py` when no installed tool covers the need.
   - For public-transit routing, run `scripts/transitous.py` with a real
     `TRAVEL_CONTACT` only when installed tools do not provide the route.
   - Use a visible browser only when structured sources lack a material field,
     the user requests a specific site, or an existing login is necessary.
   - Explain the site, reason, and fields before opening it.

5. Normalize evidence.
   - Read [offer-schema.md](references/offer-schema.md) and
     [evidence-policy.md](references/evidence-policy.md).
   - Preserve provider, retrieval method, timestamp, URL, price status,
     market, currency, tax scope, baggage status, completeness, advertiser or
     seller, provider error code, request ID, and warnings.
   - Compare stays by total stay price, not headline nightly price.
   - Keep unknown taxes, baggage, fees, and local transport costs as `null`.

6. Evaluate candidate plans.
   - Assemble only a bounded set of materially distinct candidates.
   - Use `scripts/offer_io.py` to validate and combine normalized plugin exports
     when several transport, stay, and access offers must be composed.
   - Read [ranking-rules.md](references/ranking-rules.md), then run:

```bash
python scripts/evaluate_plans.py input.json --output evaluated.json
```

   - Treat the output as decision support and verify every selected plan against
     the request and current tool results.
   - Keep strict complete-total ranking as the primary result. When strict
     ranking is impossible, present the evaluator's separate known-cost plus
     estimate-range comparison; never mix estimated options into A–E rankings.

7. Present results.
   - Read [output-schema.md](references/output-schema.md).
   - Target three to five distinct, complete, eligible options and label them
     `A`, `B`, `C`, `D`, and `E`.
   - Cover recommended, lowest-cost, fastest, low-hassle, and comfort roles
     when distinct qualifying plans exist.
   - Merge role badges when one plan wins several roles. Never duplicate or
     invent plans merely to reach the target count.
   - Explain tradeoffs in plain language and list missing material data.
   - Include source links and retrieval times near the claims they support.
   - End with a short choice prompt that lets the user reply with option IDs.

## Re-query Rules

- Reuse results from the current planning session only.
- When the user changes a condition, re-query only affected components.
- Re-query all dynamic prices when dates, traveler counts, room occupancy,
  baggage, or currency materially change.
- Never treat same-session reuse as historical price tracking.
