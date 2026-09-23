# Astronomical data

External data downloaded away from application runtime

Each dataset should be recorded in `manifest.json` with
- filename
- source URL
- dataset or model version
- coverage period
- SHA-256 checksum (for data integrity)
- retrieval date

*Application run time will not download data silently*

The manifest is currently empty (`"datasets": []`). No ephemeris has been
chosen or downloaded yet. See `docs/AGENT_HANDOFF.md` §3.3 for the policy and
milestone 1 for the first dataset (`de440s.bsp` is the documented candidate).
