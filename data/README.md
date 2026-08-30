# Astronomical data

External data downloaded away from applciaton runtime

Each dataset should be record in `manifest.json` with
- filename
- source URL
- dataset or model version
- coverage period
- SHA-256 checksum (for data integrity)
- retrieval date

*Application run time will not download data silently*