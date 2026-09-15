# 0.1.0 alpha

First downloadable POCKETPort release, with local WireGuard pairing, a Chinese dashboard/manual, Claude/Codex collection Skill manifests, seven stdio MCP tools, selected-host JSON/JSONP collection, and local JSON export.

## Validation

- Linux, Python 3.12: clean virtual environment installation completed.
- 11 automated tests passed: hostname boundaries, credential minimisation, JSONP and nested JSON, non-target filtering, body/session limits, pagination/path bounds, export consistency, TLS selection, dashboard authentication/origin rejection, real synthetic HTTP proxy collection, and MCP-driven WireGuard lifecycle/export.
- Claude/Codex plugin manifest and Skill validation passed.
- Three-OS CI is included; the GitHub Actions page shows actual remote outcomes.

## Known limitations

- No real-phone acceptance test for this packaged release yet; platform/App compatibility is not certified.
- No bundled Python runtime or signed native installer. Python 3.12/3.13 and an internet connection for installation are required.
- Manual browsing drives collection. No guaranteed account-wide history, automatic pagination or credential replay.
- JSON/JSONP only. Oversized bodies may be omitted or rejected; media and opaque data are not exported.
- App certificate pinning, Android user-CA restrictions, cache and IPv6/QUIC can prevent collection.
- One local POCKETPort instance on port 8766 at a time. Prefer native desktop networking over WSL.
- Cloud-only chat clients use file upload; remote HTTP MCP hosting is not included.
