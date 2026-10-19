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

## What the manifest records

Three datasets:

- `jpl-de440s-planetary-ephemeris` — the JPL DE440s SPICE kernel at
  `data/external/de440s.bsp`. This is the independent oracle for the Skyfield
  comparison: `tests/reference_cases/test_skyfield_agreement.py` runs the custom
  Besselian solver and Skyfield reading this kernel over the same eight events
  and requires them to agree. It is **fetched, not committed** — 32 MB, and
  reproducible from the recorded URL and checksum — so `data/external/` is
  git-ignored and CI downloads the file before running the comparison.

- `naoj-jupiter-occultations-2019-2020` — a human-saved NAOJ snapshot of the
  four Jupiter events of Meeus Table III (2019 November 28 to 2020 February 19),
  stored at `data/validation/naoj/naoj_jupiter_2019_2020.json`. NAOJ draws the
  contact times as a `.gif` image, so only the machine-readable status text is
  captured; OCR of the image is forbidden by the handoff. This snapshot is the
  independent oracle for the Jupiter regression lock in
  `tests/reference_cases/test_meeus_jupiter.py`, whose `expected` values are
  derived from this repository's own solver and are **not** printed in Meeus.

- `naoj-saturn-occultations-2024-2025` — the same for four Saturn events
  (2024 November 11 to 2025 February 01) at Tokyo, stored at
  `data/validation/naoj/naoj_saturn_2024_2025.json`. Here NAOJ returns a visible
  event as a *text* table, so the 2024-12-08 contact times and the Moon's
  altitude are captured as machine-readable values as well as the status.

Small human-saved snapshots are committed; anything fetched from a URL is not.
See `docs/AGENT_HANDOFF.md` §3.3 for the policy.

## Scripts

Three scripts operate on the data. None runs at application runtime.

```bash
# Show (or run, with --download) the deliberate download step.
uv run python scripts/fetch_reference_data.py fetch
uv run python scripts/fetch_reference_data.py fetch --download

# One dataset only, e.g. the ephemeris in a CI job that does not need the rest.
uv run python scripts/fetch_reference_data.py fetch --download \
  --only jpl-de440s-planetary-ephemeris

# Recompute every recorded SHA-256 and fail on a mismatch or a missing file.
uv run python scripts/fetch_reference_data.py verify
uv run python scripts/fetch_reference_data.py verify \
  --only naoj-saturn-occultations-2024-2025

# Check the saved NAOJ snapshots against this project's own solver.
uv run python scripts/verify_reference_data.py --dataset jupiter
uv run python scripts/verify_reference_data.py --dataset saturn --trace
```

A `PLACEHOLDER` checksum is reported as `unrecorded` and fails `verify` unless
`--allow-unrecorded` is passed, so a dataset cannot pass without a real checksum.
`fetch --download` verifies the checksum of what it just downloaded, so a
re-released upstream file cannot silently change what CI is testing.

`curl` is used when present and `urllib` when it is not, because some CI images
ship neither `curl` nor `wget`. Either way the bytes are the same and the
checksum that follows is the same.
