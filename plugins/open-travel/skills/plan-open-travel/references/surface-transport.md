# Global rail, bus, and ferry sourcing

There is no retained source that guarantees worldwide schedules, live
inventory, purchase-market prices, and fare rules across rail, intercity bus,
and ferry. Use a layered workflow instead of country-specific exceptions.

## Source layers

1. Query callable structured sources.
   - Use 12306 for mainland-China rail.
   - Use Trip.com rail where its supplier supports the route.
   - Use `scripts/transitous.py` for provider-neutral timetable and routing
     coverage based on available open feeds.
   - Use any installed mode-specific plugin when it exposes the requested
     geography and date.
2. If structured sources do not establish the route, schedule, and required
   price fields, search the internet automatically.
3. Use web search to discover the current operator and official sales channel,
   then open the supporting page. Search-result snippets alone do not prove a
   current timetable, service status, inventory, or price.

Transitous is a routing source, not a guaranteed fare or inventory source. Its
coverage varies with published GTFS, NeTEx, and realtime feeds. Mobility
Database is useful for discovering open feeds, not for buying tickets.

## Web verification order

Prefer evidence in this order:

1. official operator timetable or ticket search;
2. official rail authority, transport authority, station, terminal, or port;
3. official national or regional open-data feed;
4. aggregator or reseller.

Use aggregators to discover operators and compare candidates. Do not use an
aggregator as final proof of service status or exact purchase price when a
current official source is available. Preserve the aggregator's market,
currency, seller, fee scope, and purchase restrictions when it is the only
price source.

## Search procedure

- Search using origin, destination, exact travel date, transport mode, and
  words equivalent to `official`, `timetable`, or `tickets`.
- Resolve stations, terminals, and ports before comparing results.
- Verify the operator, service number, local departure and arrival time,
  operating date, boarding point, drop-off point, transfer location, and
  current service status.
- For cross-border routes, verify border procedure, expected processing time,
  visa or entry assumptions, and whether passengers must remove luggage.
- For ferries, verify weather or seasonal restrictions and whether the page is
  a current timetable rather than an archived route page.
- For prices, capture passenger type, market, currency, taxes, booking fee,
  baggage allowance, refund/change rules, and retrieval time.

## Failure semantics

- `NO_ROUTE`: a current authoritative source explicitly shows no route.
- `NO_INVENTORY`: the route exists and the requested departure is sold out.
- `NOT_ON_SALE`: the route exists but the requested date is outside the sales
  window.
- `SUPPLIER_UNSUPPORTED`: the queried provider does not cover the operator or
  geography.
- `PROVIDER_ERROR`: the source failed and route status remains unknown.

Never infer `NO_ROUTE` from an empty aggregator result, unsupported supplier,
timeout, destination-resolution failure, or missing open-data feed.

## Evidence labels

- Record Transitous or open-feed results as schedule/routing evidence with
  price status `unavailable` unless an explicit fare is returned.
- Record web search as `web_search` discovery evidence.
- Record the opened official page as `structured_web` or `browser` evidence.
- Keep total cost partial until ticket price, required fees, and access costs
  are established or supplied as explicit estimate ranges.

Useful background:

- Transitous documentation: https://transitous.org/doc/
- Transitous source coverage: https://transitous.org/sources/
- GTFS overview: https://gtfs.org/documentation/overview/
- Mobility Database: https://mobilitydatabase.org/
