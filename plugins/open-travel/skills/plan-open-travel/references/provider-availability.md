# Portable provider availability

Audit official provider sources before adding or replacing an MCP entry. Accept
an endpoint only when the provider publishes it on an official domain with
client configuration or authentication instructions. A same-name community
server, marketplace tool namespace, guessed subdomain, or private app transport
is not an official portable MCP.

Status verified on 2026-07-29:

| Provider | Official portable MCP | Open Travel status |
|---|---|---|
| Kiwi.com | Public Streamable HTTP endpoint `https://mcp.kiwi.com` | Bundled as `travel_kiwi` |
| trivago | Public Streamable HTTP endpoint `https://mcp.trivago.com/mcp` | Bundled as `travel_hotels` |
| Skyscanner | Official MCP exists, but access is granted case by case to approved partners; no public endpoint is documented | Do not bundle; use an installed authorized plugin or user-supplied approved connection |
| Trip.com | No provider-published public MCP endpoint found | Use the installed Trip.com plugin when available |
| Klook | No provider-published public MCP endpoint found | Use the installed Klook plugin when available |
| Wikiloc | No provider-published public MCP endpoint found | Use the installed Wikiloc plugin when available |
| China Railway 12306 | No operator-published MCP found | Retain the pinned third-party `12306-mcp` package and label its provenance |

Official references:

- Kiwi.com MCP: https://www.kiwi.com/pages/mcp/
- trivago MCP: https://mcp.trivago.com/docs
- Skyscanner MCP access policy:
  https://developers.skyscanner.net/docs/mcp-server
- Official MCP Registry: https://registry.modelcontextprotocol.io/

## Selection rules

1. Prefer a verified public provider-operated MCP over a host-specific
   marketplace plugin.
2. Do not publish partner credentials, API keys, OAuth tokens, private
   endpoints, or endpoints extracted from a host application's internal
   transport.
3. Keep a restricted official MCP as an optional user connection; do not make
   it a default dependency of an open-source plugin.
4. Keep marketplace plugins as optional capabilities when the provider has no
   public portable MCP.
5. Recheck official documentation and the official MCP Registry before changing
   this table; absence is time-sensitive.
6. When a host does not provide an optional marketplace plugin, use current
   official web sources and generic routing instead of failing or installing a
   same-name third-party MCP.
