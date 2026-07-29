# Keyless public data

`scripts/public_data.py` provides two no-key supporting-data calls. They are not flight or accommodation price sources.

## Weather

Resolve a place through Open-Meteo geocoding, then request the daily forecast:

```bash
python scripts/public_data.py weather "东京" 2026-08-01 2026-08-05 --query-name Tokyo --country-code JP
```

The output includes local daily minimum/maximum temperature, precipitation probability, weather code, coordinates, timezone, source URLs, and retrieval time.

Pass an ISO 3166-1 alpha-2 country code whenever the trip request contains one. Some translated names are not indexed under that country filter, so pass a provider-friendly Latin or native `--query-name` while keeping the user's original display name. Without a country hint, the client compares up to ten candidates and prefers the most populous administrative place, but the selected country must still be shown to the user.

Open-Meteo forecasts currently cover a rolling window of about 16 days. For a
later start date, the script returns an unavailable record containing
`earliest_query_date` and a suggested seven-day pre-departure check. Do not
substitute climate averages unless the user explicitly requests an estimate.

## Exchange rate

Get a daily reference rate through Frankfurter v2, with the ECB daily reference
feed as fallback:

```bash
python scripts/public_data.py fx 10000 CNY JPY
```

The client retries transient failures a limited number of times and caches the
day's reference rate. Label it `recent`, show the rate date and actual provider,
and warn that banks/cards may add a spread or fee.

## Failure handling

- Default network timeout: 10 seconds with one retry for transient failures.
- Return a non-zero exit code with a diagnostic category such as `TIMEOUT`,
  `DNS_ERROR`, `HTTP_ERROR`, or `UPSTREAM_UNAVAILABLE`.
- Do not open a browser when either public endpoint fails; continue without the supporting datum or use another structured source.
