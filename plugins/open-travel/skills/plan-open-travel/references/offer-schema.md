# Offer and plan schemas

Normalize provider results before comparison. Extra provider-specific fields may be retained under `raw`, but the common fields below drive decisions.

## Evidence

```json
{
  "provider": "example-provider",
  "source_type": "api",
  "fetched_at": "2026-07-25T10:30:00+08:00",
  "source_url": "https://example.com/search",
  "market": "CN",
  "currency": "CNY",
  "price_status": "live",
  "taxes_included": true,
  "baggage_status": "included",
  "completeness": "complete",
  "confidence": 0.9,
  "warnings": []
}
```

Allowed `source_type`: `plugin`, `mcp`, `api`, `web_search`,
`structured_web`, `browser`, `local`. Use `web_search` for discovery snippets,
not final schedule or price proof. Use `local` only for deterministic
planner-generated records, never for a live provider observation.

Allowed `price_status`: `live`, `recent`, `estimated`, `unavailable`.

Allowed `completeness`: `complete`, `partial`, `unavailable`.

Allowed `baggage_status`: `included`, `not_included`, `unknown`,
`not_returned`. Use `unknown` when the source cannot establish the allowance;
use `not_returned` when the field is absent.

## Candidate plan

The deterministic evaluator accepts:

```json
{
  "id": "plan-a",
  "title": "直飞 + 市区青旅",
  "currency": "CNY",
  "costs": {
    "transport_fare": 1800,
    "taxes": 320,
    "baggage": 300,
    "seat": 0,
    "origin_access": 35,
    "destination_egress": 80,
    "stay": 1200,
    "stay_taxes": 100,
    "cleaning": 0,
    "city_tax": 40,
    "late_transport": 0,
    "extra_nights": 0,
    "other": 0
  },
  "cost_estimates": {
    "baggage": {"min": 0, "max": 400},
    "destination_egress": {"min": 40, "max": 120}
  },
  "required_cost_fields": [
    "transport_fare",
    "taxes",
    "baggage",
    "origin_access",
    "destination_egress",
    "stay"
  ],
  "duration_minutes": 420,
  "transfers": 0,
  "walking_meters": 900,
  "comfort_score": 72,
  "connection": {
    "self_transfer": false,
    "separate_tickets": false,
    "airport_change": false,
    "station_change": false,
    "checked_bag_reclaim": false,
    "connection_minutes": null,
    "connection_scope": "international",
    "departure_local_time": "09:10",
    "arrival_local_time": "14:20",
    "public_transport_last_time": "23:30",
    "lodging_checkin_end": "23:00"
  },
  "evidence": []
}
```

Use `null` for an unknown cost. Never use zero to mean unknown.
`cost_estimates` is optional and may only supply explicit defensible ranges for
unknown required fields. It never turns a plan into a complete live total.

## Domain details

Keep these details when available:

- Flight: marketing/operating carrier, flight number, airports, local datetimes
  and timezones, stops, layovers, self-transfer, separate tickets, fare brand,
  booking class, per-segment baggage state and allowance, refund/change
  restrictions.
- Stay: property and room type, total stay price, taxes/cleaning/city fees, rating count and source, bathroom/room privacy, breakfast, cancellation and check-in restrictions.
- Ground route: operator, stops, local datetimes, transfers, walking, first/last service, live disruptions, luggage burden.

## Provider error

```json
{
  "provider": "example-provider",
  "code": "SUPPLIER_UNSUPPORTED",
  "message": "no supported supplier",
  "request_id": "provider-request-id",
  "retryable": false,
  "context": {
    "resolved_destination": "Butterworth",
    "applied_filters": {}
  }
}
```

Keep successful `offers` when an export also contains `errors`.
