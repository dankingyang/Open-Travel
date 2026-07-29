# Provider contracts and degradation

Read the relevant section before calling that provider. Treat validation,
coverage, and upstream failures as evidence about the tool, not evidence that a
route or property does not exist.

## Kiwi

- Use the date format accepted by the callable runtime. The current
  `search-flight` validator may require `DD/MM/YYYY` even when its description
  shows ISO dates.
- On a date-validation failure, retry once with the alternate ISO or
  `DD/MM/YYYY` representation and record `PROVIDER_CONTRACT_MISMATCH`.
- Never translate a parameter-validation failure into `NO_INVENTORY`.

## Trip.com

- Treat `locale`, `market`, and `currency` as separate facts. `zh-CN` does not
  prove mainland-China inventory or CNY pricing.
- Request mainland-China market and CNY only when the callable tool exposes
  those controls. Otherwise preserve the returned domain, market, currency,
  tax scope, and purchase-market uncertainty.
- A converted USD quote remains the original market's quote; conversion does
  not prove that a mainland-China user can buy it at that price.
- Map `no supported supplier` to `SUPPLIER_UNSUPPORTED`, not `NO_ROUTE`.
  Provide the operator's official search entry when available.

## Baggage

- Use four states: `included`, `not_included`, `unknown`, and `not_returned`.
  Never collapse the last two into `not_included`.
- Attach baggage to the fare product and each segment. Preserve fare brand,
  booking class, personal-item allowance, cabin-bag dimensions or weight,
  checked-bag count or weight, and source text when available.
- Call two observations a conflict only when itinerary, dates, passenger type,
  market, seller, cabin, and fare product are comparable and both sources make
  explicit contradictory claims. Missing data is not a conflict.
- Keep baggage cost unknown when the allowance or required bag price is
  unknown; this can change the complete-cost ranking.

## Klook

- Query one destination per call and request a small first page. Do not launch
  several city discovery calls in one parallel batch when their combined
  payload may overflow context.
- Retain only title, current price and currency, rating, review count, duration,
  service languages, cancellation signal, ID, and direct link for comparison.
  Fetch a detailed product only after the user selects it.
- Do not repeat the same product from `attractions_data` and `activity_data`.
  Drop internal tracking fields and search handles from the answer.
- If the tool does not accept adults and children, mark occupancy as
  `not_controllable`. If a returned handle uses a different passenger count,
  flag `PASSENGER_COUNT_MISMATCH` and do not treat the price as an exact
  one-person total.
- Distinguish page language, audio-guide language, live-guide language, and
  support language. A Chinese product page does not prove a Chinese guide.

## Weather

- Open-Meteo's rolling forecast window is not climate data. When the requested
  date is outside the window, show the earliest date on which it can be queried
  and suggest a check seven days before departure.
- For island or ferry-dependent plans, include the seven-day check as a
  decision checkpoint. Do not create an alert or describe climate normals as a
  forecast unless the user separately asks for climate estimates.
