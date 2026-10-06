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

The manifest is no longer empty. It records one dataset:

- `naoj-jupiter-occultations-2019-2020` — a human-saved NAOJ snapshot of the
  four Jupiter events of Meeus Table III (2019 November 28 to 2020 February 19),
  stored at `data/validation/naoj/naoj_jupiter_2019_2020.json`. NAOJ draws the
  contact times as a `.gif` image, so only the machine-readable status text is
  captured; OCR of the image is forbidden by the handoff. This snapshot is the
  independent oracle for the Jupiter regression lock in
  `tests/reference_cases/test_meeus_jupiter.py`, whose `expected` values are
  derived from this repository's own solver and are **not** printed in Meeus.

No ephemeris has been chosen or downloaded yet. `data/external/` does not exist
until a URL dataset is fetched. See `docs/AGENT_HANDOFF.md` §3.3 for the policy
and milestone 1 for the first dataset (`de440s.bsp` is the documented candidate).

## Scripts

Two scripts operate on the manifest. Neither runs at application runtime.

```bash
# Show (or run, with --download) the deliberate download step.
uv run python scripts/fetch_reference_data.py fetch
uv run python scripts/fetch_reference_data.py fetch --download

# Recompute every recorded SHA-256 and fail on a mismatch or a missing file.
uv run python scripts/fetch_reference_data.py verify

# Check the saved NAOJ snapshot against this project's own solver.
uv run python scripts/verify_reference_data.py
```

A `PLACEHOLDER` checksum is reported as `unrecorded` and fails `verify` unless
`--allow-unrecorded` is passed, so a dataset cannot pass without a real checksum.

