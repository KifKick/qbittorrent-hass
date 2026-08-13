# qBittorrent for Home Assistant

A thorough Home Assistant custom integration for [qBittorrent](https://www.qbittorrent.org/), built on the [`qbittorrent-api`](https://pypi.org/project/qbittorrent-api/) library. Configuration is done entirely through the Home Assistant UI (Settings → Devices & Services) — no YAML required.

## Features

- **Config flow** with support for both username/password and API key authentication (qBittorrent v5.2+), HTTPS, self-signed certificates, and reverse-proxy path prefixes.
- **Global sensors**: download/upload speed, session totals, speed limits, share ratio, free disk space, DHT nodes, peer connections, connection status, torrent counts by state, category/tag counts, app & Web API version, default save path.
- **Diagnostic "list" sensors** for torrents, categories and tags — their attributes are the easiest way to look up a torrent's hash for use in automations.
- **Switches**: alternative speed limits, DHT.
- **Buttons**: resume all, pause all, reannounce all, shut down qBittorrent.
- **~40 services** covering almost the entire qBittorrent Web API: adding/removing/pausing/resuming torrents, categories, tags, share/speed limits, file priorities, RSS feeds and auto-download rules, the search plugin API, and a `get_torrents` response service for finding hashes without relying on sensor attributes.
- **Options flow** to tune the polling interval and the torrent-list sensor's size.
- **Multiple qBittorrent instances** are supported — add one config entry per server.
- Full **diagnostics** download (with credentials redacted) for bug reports.
- Available in English and Polish.

## Requirements

- qBittorrent with the Web UI enabled (Tools → Options → Web UI).
- `qbittorrent-api` 2026.8.0 (installed automatically), which targets qBittorrent v5.2.3 / Web API v2.15.1. Older versions generally still work; a repair notification is raised if the connected version isn't fully supported.

## Installation

### HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories** and add this repository's URL.
2. Search for "qBittorrent" in HACS and install it.
3. Restart Home Assistant.

### Manual

Copy `custom_components/qbittorrent` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

Go to **Settings → Devices & Services → Add Integration**, search for "qBittorrent", and follow the steps:

1. Enter the host, port, and whether to use HTTPS/verify the certificate.
2. Choose an authentication method — username/password, or an API key generated in the qBittorrent WebUI.

Afterwards, use the integration's **Configure** option to adjust the polling interval and the torrent-list sensor's attribute limit.

## Finding a torrent's hash

Since this integration intentionally does not create one entity per torrent (to avoid entity-count bloat), use one of:

- The `sensor.<name>_torrent_list` entity's attributes (Developer Tools → States).
- The `qbittorrent.get_torrents` service, which returns the full/filtered torrent list as a service response — this is the recommended approach for large libraries, since the sensor's attributes are capped.

## Services

All services take a `config_entry_id` field to target a specific qBittorrent instance. See `services.yaml` or Developer Tools → Actions in Home Assistant for the full list and field descriptions, including:

`add_torrent`, `delete_torrents`, `pause_torrents`, `resume_torrents`, `recheck_torrents`, `reannounce_torrents`, `force_start`, `set_auto_management`, `set_super_seeding`, priority actions, `set_location`, `set_save_path`, `set_category`, `add_tags`/`remove_tags`, `set_share_limits`, `set_upload_limit`/`set_download_limit`, `rename_torrent`, `set_file_priority`, `export_torrent`, category/tag management, global transfer limits, `ban_peers`, `set_preferences`, RSS feed/rule management, search, `get_torrents`, `get_app_preferences`, and `create_torrent`.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install qbittorrent-api pytest-homeassistant-custom-component ruff

ruff check custom_components/ tests/
python -m pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
