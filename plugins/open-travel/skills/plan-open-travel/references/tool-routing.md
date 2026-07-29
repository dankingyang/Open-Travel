# Plugin routing

Discover callable tools before promising a provider. Tool names can be
namespaced by the runtime; match by plugin and capability rather than assuming a
fixed namespace.

## Route matrix

| Need | Preferred installed plugins | Selection rule |
|---|---|---|
| Fixed-date flights | Trip.com `search_flights`, Kiwi `search_flight`, Skyscanner | Search at least two compatible sources when a comparison is useful |
| Flexible-date flights | Trip.com `search_low_price_flights_v2`, Skyscanner indicative prices | Preserve the user's full window; split only when a tool's limit requires it |
| Final live Skyscanner view | Skyscanner live prices | Call at most once and make it the final assistant action in that turn |
| China rail | 12306 `get-tickets` and `get-interline-tickets`, Trip.com `search_train_routes` | Prefer 12306 for mainland inventory; use Trip.com as comparison or fallback |
| Global rail | Trip.com where supported; Transitous for open timetable routing | If structured coverage is inadequate, search and verify the current official operator source |
| Intercity bus or coach | Installed structured source; Transitous where open feeds cover it | Otherwise search the web and verify operator or terminal evidence |
| Ferry | Installed structured source; Transitous where open feeds cover it | Otherwise search the web and verify operator, port, and current service status |
| Hotels | trivago text search, then radius search | Use a market-compatible locale, validate `country_city`, and compare total-stay prices |
| Activities and food | Klook travel discovery | Use destination, dates, currency, budget, language, and interests |
| Trails | Wikiloc geocode, trail search, trail display | Geocode location searches first and follow the plugin's batching rules |
| Open-ended destination ideas | Klook plus available flight discovery tools | State that discovery prices are not final fare quotes |
| Weather and FX gaps | `scripts/public_data.py` | Use only when installed tools do not cover the field |
| Public-transit gaps | `scripts/transitous.py` | Require a real contact and preserve Transitous attribution |
| Surface transport web verification | Internet search, then current official page | Search snippets discover sources; opened pages support claims |

## Provider-specific constraints

- Trip.com: use `search_flights` for exact dates and
  `search_low_price_flights_v2` for flexible windows. Do not use the deprecated
  low-price v1 tool when v2 exists.
- Trip.com locale is not a market or currency guarantee. Preserve returned
  market, domain, currency, tax scope, and purchase eligibility.
- Skyscanner: indicative search is suitable for date discovery. Its live-price
  tool renders a widget and must be the final action, so never place it inside a
  multi-source tool-call batch.
- Kiwi: use the runtime-accepted date representation; retry one alternate date
  format only for a validation mismatch. Disable self-transfer,
  different-airport connections, or overnight stopovers when they violate hard
  constraints.
- 12306: query only. Never continue into passenger selection or ordering.
- trivago: read `trivago.md`; start unfiltered, keep shopper market separate
  from destination, use a compatible search locale, validate `country_city`,
  and use coordinates when text resolution is unreliable. Retain the advertiser
  field. A trivago result is not automatically a Booking.com, Agoda, or
  direct-hotel offer.
- Klook: query destinations sequentially with a small page, normalize compact
  summary fields, deduplicate product IDs, and fetch detail only after selection.
- Wikiloc: geocode before location-based trail discovery, then display selected
  trail IDs only when the user benefits from the map.

## Discovery and degradation

1. Search for installed or callable tools relevant to the request.
2. Suggest connecting a missing useful plugin without blocking available work.
3. Announce the providers that will be queried and say whether a browser is planned.
4. Run independent compatible calls in parallel.
5. Preserve success, timeout, unavailable, and error independently per source.
6. Explain every source switch and any material field still missing.
7. When a supplier is unsupported, provide the most specific official search
   entry available and keep inventory unknown.
8. For rail, intercity bus, or ferry with no adequate structured source, search
   the internet automatically. Prefer official operator and authority evidence;
   use aggregators only for discovery or clearly scoped reseller prices.

Do not open a browser when structured results already provide enough candidates,
price scope, source links, and retrieval times for an honest comparison.
