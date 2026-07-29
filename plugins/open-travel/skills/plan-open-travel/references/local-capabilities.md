# Local capability policy

Local code has three explicit classes. Do not treat every bundled script as an
equivalent data source.

## Core: use for deterministic processing

| Capability | File | Use |
|---|---|---|
| Export validation and bounded composition | `scripts/offer_io.py` | Validate normalized plugin results, preserve unknown costs, convert currency only with explicit rates, and compose a bounded candidate set |
| Complete-cost and risk evaluation | `scripts/travel_core.py` | Apply hard constraints, calculate complete totals, label connection and evidence risks, compute the Pareto frontier, and select representative plans |
| Evaluator CLI | `scripts/evaluate_plans.py` | Run the deterministic evaluator on an assembled JSON payload |

These modules do not query providers. Use them whenever their validation or
arithmetic improves repeatability.

## Conditional: use only for uncovered data gaps

| Capability | File | Strength | Limitation |
|---|---|---|---|
| Weather and FX | `scripts/public_data.py` | Small, keyless Open-Meteo weather client plus Frankfurter with ECB fallback | Weather is forecast data; FX is a reference rate and excludes card or cash spreads |
| Public-transit routing | `scripts/transitous.py` | Structured MOTIS route results with attribution | Requires a real contact, has uneven geographic coverage, and usually has no fare |

Use these only after checking installed plugins. Label every result with its
provider, retrieval time, and limitation.

## Retained MCPs: use for live provider queries

| Capability | Runtime | Status |
|---|---|---|
| China rail | Plugin-provided `npx -y 12306-mcp@0.3.9` | Retained after a live query test and a separate startup/tool-list smoke test |
| Flights | Provider-operated remote Kiwi MCP at `https://mcp.kiwi.com` | Public cross-client configuration documented by Kiwi.com; treat missing tax and fare-condition details as incomplete |
| Hotels | Provider-operated remote trivago MCP at `https://mcp.trivago.com/mcp` | Public cross-client endpoint documented by trivago; keep taxes and mandatory fees unverified when absent |

The 12306 MCP is a pinned third-party Node package, not project-owned provider
code. The plugin launches it through `npx`, so do not require a repository-local
`node_modules`, package-manager store, absolute executable path, or fixed
working directory. If `npx` is unavailable, report that Node.js is a runtime
prerequisite instead of silently switching providers.

## Retired: do not use in active planning

The following legacy capability types are intentionally outside the active
plugin:

- the Airbnb MCP, because compliant access was blocked by robots policy;
- the Skiplagged MCP, because repeated live tests returned rate-limit errors;
- the project-owned multi-source flight MCP server and provider wrappers;
- the `fast-flights` page parser and optional Python runtime;
- direct 12306 page requests;
- the old manifest runner coupled to those adapters.

They are redundant, unavailable under the required access policy, or depend on
provider response internals. Do not ship or silently restore archived copies.

## Decision order

1. Use installed travel plugins and retained MCPs for live inventory and search.
2. Use core local modules for validation, composition, and ranking.
3. Use conditional local modules only for a material gap.
4. For rail, intercity bus, or ferry gaps, search the internet automatically
   and verify the current official source.
5. Use a visible browser after disclosure when verification requires an
   interactive page, generated result, or existing login.
