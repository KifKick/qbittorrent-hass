# Changelog

## [0.2.6] - 2026-10-12

### Fixed

- **`qbt.get_torrents` failed with "Unable to serialize to JSON" (HTTP 500).** The torrent list returned by `qbittorrent-api` wasn't converted to plain JSON types, so the service failed whenever any torrent matched. It now returns a regular list of torrents.

### Added

- **`limit`, `offset` and `hashes` options for `qbt.get_torrents`**, to page through large libraries or fetch specific torrents without transferring the whole list.

## [0.2.5] - 2026-10-09

### Fixed

- **Recorder warnings / database bloat from the torrent list sensor.** Its per-torrent attributes easily exceeded the recorder's 16 KiB attribute limit and changed on every poll. They are now excluded from the recorder and remain available in the live state only (templates, automations and cards still see them). The torrent count itself is still recorded for history and statistics.

## [0.2.4] - 2026-10-09

### Fixed

- **"Unsupported qBittorrent version" repair warning on qBittorrent 5.2.4.** The bundled `qbittorrent-api` library (2026.8.0) only recognized qBittorrent up to v5.2.3. Bumped it to 2026.10.0, which supports v5.2.4.
- **The unsupported-version warning never went away on its own.** It is now removed automatically once the connected qBittorrent version is supported, and re-checked whenever the qBittorrent version changes (previously only once per integration load).

## [0.2.3] - 2026-08-14

### Fixed

- **HACS could show the installed/available version as a raw commit SHA (e.g. `2dc9b0d`) instead of a proper version number.** This happened because HACS was allowed to track the `main` branch directly instead of tagged releases. Added `hide_default_branch: true` to `hacs.json` so HACS only ever offers versioned releases.

## [0.2.2] - 2026-08-14

### Fixed

- **Switch/number/button writes no longer leak raw exceptions.** Turning off DHT, setting a speed limit, etc. now surfaces a readable error instead of an unhandled traceback when qBittorrent rejects the request. Only genuinely invalid credentials (`LoginFailed`) trigger a re-authentication prompt — a bare `403` (e.g. a temporary brute-force IP ban) no longer forces you to re-enter working credentials, matching the distinction the config flow already made between "invalid_auth" and "banned".
- **A slow, rarely-polled diagnostic fetch (app version, preferences, build info) could take down every sensor.** That fetch is now isolated from the main torrent/speed update, so a transient failure there no longer marks the whole integration unavailable.
- **Unsupported qBittorrent versions no longer risk getting the integration stuck.** Version support is now checked non-blockingly (via `qbittorrent-api`'s own version tables) and only raises a Repairs warning — it can no longer cause the integration to fail every update forever on an unsupported server.
- **The qBittorrent WebUI session is now logged out on unload/reload**, instead of being left open until it naturally expires.
- **Device info (app/Web API version) now updates live** instead of freezing at whatever was known when an entity was first created.
- Hardened the `connection_status` sensor against unrecognized values, validated base64 input in the `add_torrent` service instead of raising a raw decoding error, and made the torrent-list sensor's attribute truncation deterministic (sorted by name) instead of depending on API response order.

### Internal

- Added regression tests for the above error-handling and update-isolation fixes (30 tests total).

## [0.2.1] - 2026-08-13

### Removed

- The duplicate `categories_list`/`tags_list` sensors. `categories_count`/`tags_count` already show the same number as their state; the `_list` sensors only added attributes on top, which read as confusing duplication.

## [0.2.0] - 2026-08-13

### Added

- Number entities for connection/speed/queueing settings: incoming port, max connections (global/per-torrent), max upload slots (global/per-torrent), global and alternative download/upload limits, and max active downloads/uploads/torrents.
- New `queueing_enabled` switch (required for the max-active-* number entities to take effect).

### Fixed

- server_state fields (connection status, speeds, DHT nodes, free space, rate limits, ...) showed as "unknown" after the first update, since qBittorrent only sends *changed* fields on incremental syncs and the coordinator was replacing the cached state wholesale instead of merging.
- Preference-backed switches and number entities now refresh immediately after being changed, instead of waiting up to ~2 minutes for the next slow-poll cycle.

## [0.1.1] - 2026-08-13

### Changed

- **Renamed the integration's domain from `qbittorrent` to `qbt`** to avoid colliding with Home Assistant core's own built-in `qbittorrent` integration (entities/services now use the `qbt.` prefix). Together with the required `CONFIG_SCHEMA` declaration and the brand icon moved to the path HACS expects, this fixes the hassfest/HACS validation failures.
- The config flow now distinguishes qBittorrent's brute-force IP ban (`banned`) from wrong credentials (`invalid_auth`) — previously both showed the same generic error, which was misleading once banned.

### Added

- The installed `qbittorrent-api` library version in the integration's diagnostics download, for easier troubleshooting.

## [0.1.0] - 2026-08-13

### Added

- Initial release of the **qBittorrent (Advanced)** integration: UI-only configuration with username/password or API key authentication (qBittorrent v5.2+), HTTPS, self-signed certificates and reverse-proxy path prefixes.
- About 25 global entities: transfer and torrent statistics, switches (alternative speed limits, DHT) and buttons (resume/pause/reannounce all, shutdown).
- 44 services covering almost the entire qBittorrent Web API, including a `qbt.get_torrents` response service for looking up hashes without cluttering the entity registry.
- Options flow, multiple qBittorrent instances, diagnostics with credentials redacted, and English and Polish translations.
