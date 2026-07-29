# trivago MCP search contract

Use the callable MCP tool schema as the execution contract. The public landing
page may show a simplified `search_hotels` example, while the current server
exposes:

- `trivago_accommodation_search` with `query`, `arrival`, and `departure`;
- `trivago_accommodation_radius_search` with `latitude`, `longitude`,
  `arrival`, and `departure`.

The configured endpoint is `https://mcp.trivago.com/mcp`. No API key is
required.

## Baseline request

Establish an unfiltered baseline before adding preferences:

1. Use ISO dates `YYYY-MM-DD`.
2. Pass `adults` and `rooms` explicitly; keep `rooms <= adults`.
3. Treat `country` as the shopper pricing/content market, not the hotel
   destination.
4. Set `currency` explicitly.
5. Use a search language compatible with the selected market. Do not copy the
   conversation language blindly.
6. Query an unambiguous provider-friendly destination such as
   `City, Country`.
7. Omit amenity, hotel-star, and review filters.

The current country enum does not include `CN`, although `CNY` and
`ZH_HANS_CN` exist in their respective enums. For a shopper in an unsupported
market, use the destination market when it is supported; otherwise use the
explicit documented default market `US`. Disclose the market substitution.
Currency may still be CNY when supported.

## Language and market compatibility

The bridge accepts each enum independently at validation time but may fail for
an incompatible combination. Live verification on 2026-07-29 found:

- `country=MY`, `currency=MYR`, `language=MS_MY`: successful;
- `country=MY`, `currency=CNY`, `language=MS_MY`: successful;
- `country=MY`, `currency=MYR`, `language=ZH_HANS_CN`: generic search error.

Therefore:

- prefer the market's matching locale when available;
- use `EN_US` as the compatibility retry locale;
- translate the returned content for the user after the search;
- map a generic failure that disappears after the locale retry to
  `MARKET_LANGUAGE_MISMATCH`;
- do not classify it as no inventory.

## Destination resolution

Inspect the returned `country_city` before accepting results. A city name can
resolve to the wrong country.

If the text search errors, returns a suspiciously small result set, or resolves
to the wrong place:

1. geocode the intended city, landmark, or neighborhood;
2. call `trivago_accommodation_radius_search` with those target coordinates;
3. keep dates, occupancy, market, currency, and compatible language unchanged;
4. record `DESTINATION_MISMATCH` when the original text resolution was wrong.

Do not use the user's current coordinates. The radius tool requires the target
destination coordinates.

## Filters

Only add filters after a successful baseline.

- Add one filter group at a time so a failing group can be identified.
- The schema permits multiple booleans, but it does not state whether multiple
  star or review thresholds are OR, AND, or collapsed by the bridge. Avoid
  multiple values in one rating group unless verified.
- On failure, retry the last successful request without the newly added group.
- Never change destination, dates, occupancy, market, or currency silently.

## Response handling

Read results from `structuredContent.accommodations`. The server currently
returns up to 25 accommodations and does not expose a result-limit parameter.

- Keep only the most useful five to eight records in model context.
- Preserve `price_per_stay`, `price_per_night`, currency, advertiser,
  accommodation URL, rating, review count, distance, and coordinates.
- Compare total-stay prices. Do not derive a total from a rounded nightly label
  when `price_per_stay` is present.
- Treat taxes, mandatory fees, room type, occupancy rules, and cancellation as
  unknown unless explicitly returned.
- Do not repeat the MCP's large text envelope when structured content exists.

Official documentation: https://mcp.trivago.com/docs
