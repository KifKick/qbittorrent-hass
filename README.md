# qBittorrent (Advanced)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![GitHub Release](https://img.shields.io/github/v/release/KifKick/qbittorrent-hass)](https://github.com/KifKick/qbittorrent-hass/releases)
[![Lint & Test](https://github.com/KifKick/qbittorrent-hass/actions/workflows/lint-test.yml/badge.svg)](https://github.com/KifKick/qbittorrent-hass/actions/workflows/lint-test.yml)
[![Validate](https://github.com/KifKick/qbittorrent-hass/actions/workflows/validate.yml/badge.svg)](https://github.com/KifKick/qbittorrent-hass/actions/workflows/validate.yml)

A Home Assistant integration for [qBittorrent](https://www.qbittorrent.org/) that goes well beyond the built-in one: live transfer and torrent statistics, switches and number entities for the client's main settings, and 44 actions covering almost the whole qBittorrent Web API, from adding torrents to RSS rules and search. Set up entirely from the UI, built on [`qbittorrent-api`](https://pypi.org/project/qbittorrent-api/).

Looking for a dashboard? See [Dashboard cards](#dashboard-cards) below.

> [!NOTE]
> Home Assistant ships its own, smaller `qbittorrent` integration. To stay out of its way, this one uses the domain **`qbt`** (actions are `qbt.*`) and appears as **qBittorrent (Advanced)** in Add Integration. Both can be installed side by side, but set up only one of them for the same server.

## Features

- **UI setup** with username/password or an API key, HTTPS, self-signed certificates and a URL path prefix for reverse proxies. Reauthentication is offered when the credentials stop working.
- **Sensors** for speeds, session totals, speed limits, share ratio, free disk space, peers, DHT nodes, connection status and torrent counts by state.
- **Switches** for alternative speed limits, DHT and torrent queueing.
- **Number entities** for the incoming port, connection and upload slot limits, global and alternative speed limits, and queue sizes, all editable from the device page.
- **Buttons** to resume, pause or reannounce all torrents and to shut qBittorrent down.
- **44 actions**: torrents, files, categories, tags, share and speed limits, peers, preferences, RSS feeds and auto-download rules, search and torrent creation. Several of them return data (`get_torrents`, `export_torrent`, search results, preferences).
- **No entity per torrent.** A single torrent list sensor and the `qbt.get_torrents` action cover lookups, so big libraries don't flood the entity registry.
- **Several servers**: add one entry per qBittorrent instance.
- **Diagnostics** download with credentials, host and private preferences redacted.
- English and Polish.

## Requirements

- Home Assistant 2024.6 or newer.
- qBittorrent with the Web UI turned on (**Tools → Options → Web UI**).
- API key sign-in needs qBittorrent 5.2 or newer. Username and password work on older versions.

The integration installs `qbittorrent-api` 2026.10.0, which targets qBittorrent 5.2.4. Older qBittorrent releases mostly work. If the connected version isn't fully supported, Home Assistant shows a repair notice and most entities and actions keep working.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=KifKick&repository=qbittorrent-hass&category=integration)

Or by hand:

1. In HACS, open **⋮ → Custom repositories**, add `https://github.com/KifKick/qbittorrent-hass` with the type **Integration**.
2. Search for **qBittorrent (Advanced)**, download it, and restart Home Assistant.

### Manual

Copy `custom_components/qbt` from the [latest release](https://github.com/KifKick/qbittorrent-hass/releases/latest) into `config/custom_components/` and restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up qBittorrent (Advanced).](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=qbt)

Or go to **Settings → Devices & services → Add integration** and search for **qBittorrent (Advanced)**.

1. **Connection**: host, port (default `8080`), HTTPS, certificate verification and an optional path prefix if qBittorrent sits behind a reverse proxy, for example `/qbittorrent`.
2. **Authentication**: the Web UI username and password, or an API key from the qBittorrent Web UI.

### Options

Open **Configure** on the integration entry to change:

| Option | Default | Range | |
|---|---|---|---|
| Scan interval | 30 s | 5–3600 s | How often torrents and transfer stats are fetched. Version info and preferences refresh every fourth update. |
| Torrent list sensor | on | | Turn off if you only use `qbt.get_torrents`. |
| Torrents in the list sensor | 200 | 10–2000 | Cap on the sensor's attributes, sorted by name. |

## Entities

Entities belong to one device per server. Those marked *diagnostic* or *config* are on the device page but are left out of auto-generated dashboards.

### Sensors

| Sensor | Notes |
|---|---|
| Download speed, Upload speed | |
| Downloaded this session, Uploaded this session | diagnostic |
| Download speed limit, Upload speed limit | the limit in effect right now; diagnostic |
| Global share ratio | |
| Free space | on the default save path |
| Peer connections, DHT nodes | diagnostic |
| Connection status | `connected`, `firewalled` or `disconnected` |
| Torrents, Torrents downloading, Torrents seeding, Torrents paused | |
| Torrents checking, Torrents with errors | diagnostic |
| Categories, Tags | counts; diagnostic |
| qBittorrent version, Web API version, Default save path | diagnostic |
| Torrent list | torrents keyed by hash, with name, state, progress, speeds, category, tags, save path, ratio, size and ETA; diagnostic. These attributes aren't stored in the recorder. |

A **Connectivity** binary sensor reports whether Home Assistant can reach the server.

### Controls

| Type | Entities |
|---|---|
| Switch | Alternative speed limits, DHT, Torrent queueing |
| Number | Incoming connections port, Maximum connections (global and per torrent), Maximum upload slots (global and per torrent), Global download and upload limit, Alternative download and upload limit, Maximum active downloads, uploads and torrents |
| Button | Resume all torrents, Pause all torrents, Reannounce all torrents, Shut down qBittorrent |

Speed limits on number entities are in KiB/s, and `0` means unlimited. For connection and slot limits, `-1` means unlimited. Switches and numbers re-read the setting from qBittorrent right after a change, so the state always shows what the server applied.

## Actions

Every action takes `config_entry_id`, the qBittorrent server to talk to (a dropdown in the UI). Torrents are passed as a list of hashes in `hashes`, or as a single `hash` where an action works on one torrent. **Developer tools → Actions** shows every field with its description.

| Group | Actions |
|---|---|
| Add and remove | `add_torrent` (magnet links, URLs, a `.torrent` file path or base64 content, with all the usual add options), `delete_torrents` (optionally with files), `create_torrent` |
| Control | `pause_torrents`, `resume_torrents`, `recheck_torrents`, `reannounce_torrents`, `force_start`, `set_auto_management`, `set_super_seeding` |
| Queue | `increase_priority`, `decrease_priority`, `top_priority`, `bottom_priority` |
| Organize | `set_category`, `add_tags`, `remove_tags`, `set_location`, `set_save_path`, `rename_torrent` |
| Files | `set_file_priority`, `export_torrent` (returns the `.torrent` as base64) |
| Limits | `set_share_limits`, `set_upload_limit`, `set_download_limit` (per torrent), `set_global_upload_limit`, `set_global_download_limit`, `set_speed_limits_mode` |
| Categories and tags | `create_category`, `edit_category`, `remove_categories`, `create_tags`, `delete_tags` |
| Peers and preferences | `ban_peers`, `get_app_preferences`, `set_preferences` |
| RSS | `rss_add_feed`, `rss_remove_item`, `rss_set_rule`, `rss_remove_rule` |
| Search | `search_start`, `search_get_results`, `search_stop` |
| Lookup | `get_torrents` |

Limits passed to actions are in **bytes per second**, unlike the number entities.

### Finding torrents

Use `qbt.get_torrents` to find hashes. It filters by state, category or tag, sorts, pages with `limit`/`offset`, and returns `{"torrents": [...]}` with the full torrent info from qBittorrent:

```yaml
action: qbt.get_torrents
data:
  config_entry_id: YOUR_ENTRY_ID
  status_filter: completed
  category: movies
  sort: completion_on
  reverse: true
  limit: 10
response_variable: result
```

For a quick look without an action, open the **Torrent list** sensor in **Developer tools → States**. Its attributes stop at the configured cap, so prefer the action in automations.

## Examples

Turn on alternative speed limits in the evening:

```yaml
automation:
  - alias: Slow torrents in the evening
    triggers:
      - trigger: time
        at: "18:00:00"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.qbittorrent_192_168_1_10_alternative_speed_limits
```

Tag and pause every completed torrent:

```yaml
script:
  park_completed:
    sequence:
      - action: qbt.get_torrents
        data:
          config_entry_id: YOUR_ENTRY_ID
          status_filter: completed
        response_variable: result
      - variables:
          hashes: "{{ result.torrents | map(attribute='hash') | list }}"
      - condition: template
        value_template: "{{ hashes | count > 0 }}"
      - action: qbt.add_tags
        data:
          config_entry_id: YOUR_ENTRY_ID
          hashes: "{{ hashes }}"
          tags: [done]
      - action: qbt.pause_torrents
        data:
          config_entry_id: YOUR_ENTRY_ID
          hashes: "{{ hashes }}"
```

The device is named after the server, for example **qBittorrent (192.168.1.10)**, and entity IDs follow that name; check yours on the device page. `YOUR_ENTRY_ID` is the entry ID, which the action editor fills in when you pick the server.

## Dashboard cards

[qBittorrent (Advanced) Cards](https://github.com/KifKick/qbittorrent-hass-cards) is a companion card bundle made for this integration, installed separately from HACS as a **Dashboard** repository:

- **Overview card**: connection status, speeds with the current limit and a history graph, torrent counts, free space and ratio, with buttons for alternative speed limits and pause/resume all.
- **Torrents card**: a live, paged torrent list with qBittorrent's filters and per-torrent details, where you can pause, resume, force-start, reannounce, recheck or remove each torrent.
- **Top torrents card**: a top-N ranking by upload, ratio, speed, leechers, seeding time or size.

The cards find this integration's entities by themselves; you only pick the qBittorrent server. They need integration version 0.2.6 or newer.

![Overview card, light and dark](https://raw.githubusercontent.com/KifKick/qbittorrent-hass-cards/main/docs/images/overview-card.png)

[![Open your Home Assistant instance and open the cards repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=KifKick&repository=qbittorrent-hass-cards&category=plugin)

## Troubleshooting

- **Can't connect**: check that the Web UI is on and that Home Assistant can reach that host and port. If qBittorrent limits Web UI access to certain IP addresses, Home Assistant's address has to be on the list.
- **Behind a reverse proxy**: fill in the path prefix, and turn off certificate verification only if the certificate is self-signed.
- **"Unsupported qBittorrent version" repair**: the server runs a version newer or older than the library targets. Most things still work; update the integration when a new release comes out.
- **Bug reports**: download diagnostics from the integration entry (credentials are redacted) and attach them to an [issue](https://github.com/KifKick/qbittorrent-hass/issues) with your qBittorrent version and the error from the Home Assistant log.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install qbittorrent-api pytest-homeassistant-custom-component ruff

ruff check custom_components/ tests/
python -m pytest tests/
```

The tests use `pytest-homeassistant-custom-component` and cover the config flow, coordinator, entities, actions and diagnostics. CI runs ruff and the tests, plus hassfest and the HACS validator.

To release, bump `version` in [`manifest.json`](custom_components/qbt/manifest.json), add a matching section to [`CHANGELOG.md`](CHANGELOG.md), and push a `vX.Y.Z` tag. The release workflow checks that the tag matches the manifest, runs ruff and the tests, and publishes a GitHub release with that changelog section as notes.

## AI disclosure

This integration was written **entirely by AI**: Claude Sonnet 5 and later Claude Opus 5.5 (Anthropic), via [Claude Code](https://claude.com/claude-code). That covers the Python, the tests, the translations and this README. [KifKick](https://github.com/KifKick) decided the scope and design and tested it on a real server. Every commit is co-authored by the model that wrote it, so the git log shows what was generated and when.

The integration handles your qBittorrent credentials; [`config_flow.py`](custom_components/qbt/config_flow.py) and [`coordinator.py`](custom_components/qbt/coordinator.py) are short enough to read before you install it.

## License

MIT, see [LICENSE](LICENSE). Not affiliated with the qBittorrent project.
