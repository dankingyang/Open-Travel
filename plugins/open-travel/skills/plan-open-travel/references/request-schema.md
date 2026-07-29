# TripRequest schema

Use this normalized object before querying tools.

```json
{
  "origin": {"name": "上海", "kind": "city"},
  "destinations": [{"name": "东京", "kind": "city"}],
  "date_window": {
    "depart_from": "2026-09-13",
    "depart_to": "2026-09-17",
    "return_from": "2026-09-18",
    "return_to": "2026-09-22"
  },
  "duration_days": 6,
  "travelers": {"adults": 1, "children": 0},
  "budget": {"amount": 6000, "currency": "CNY"},
  "pace": "balanced",
  "flight_preferences": {
    "cabin": "economy",
    "checked_bags": 1,
    "allow_low_cost": true,
    "allow_red_eye": false,
    "allow_self_transfer": false
  },
  "stay_preferences": {
    "types": ["hostel", "hotel"],
    "private_room": true,
    "minimum_rating": 8.0
  },
  "ground_transport_preferences": {
    "maximum_walking_meters": 1200,
    "maximum_transfers": 2
  },
  "hard_constraints": {},
  "soft_preferences": []
}
```

## Blocking fields

Ask only when origin, destination, or usable dates/trip length are missing. Default travelers to one adult and disclose it. Budget and detailed preferences improve ranking but do not block an initial search.

## Date handling

- Use ISO dates internally.
- Interpret displayed departure and arrival times in the location's local timezone.
- Preserve flexible windows; do not collapse them to a single date before price comparison.
- Never silently substitute dates when a provider cannot search the full window.

## Hard constraints

Supported evaluator constraints include:

```json
{
  "max_total_cost": 6000,
  "max_duration_minutes": 1200,
  "max_transfers": 2,
  "disallow_self_transfer": true,
  "disallow_separate_tickets": true,
  "disallow_airport_change": true,
  "disallow_red_eye": true
}
```
