"""Constants for the qBittorrent integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "qbt"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

# --- Config entry / options keys -------------------------------------------------

CONF_USE_HTTPS: Final = "use_https"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_PATH: Final = "path"
CONF_AUTH_METHOD: Final = "auth_method"
CONF_API_KEY: Final = "api_key"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ENABLE_TORRENT_LIST_SENSOR: Final = "enable_torrent_list_sensor"
CONF_MAX_TORRENTS_IN_ATTRIBUTES: Final = "max_torrents_in_attributes"

AUTH_METHOD_PASSWORD: Final = "password"
AUTH_METHOD_API_KEY: Final = "api_key"

# --- Defaults ----------------------------------------------------------------------

DEFAULT_PORT: Final = 8080
DEFAULT_USE_HTTPS: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_SLOW_UPDATE_EVERY_N_CYCLES: Final = 4
DEFAULT_MAX_TORRENTS_IN_ATTRIBUTES: Final = 200
DEFAULT_ENABLE_TORRENT_LIST_SENSOR: Final = True

MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 3600
MIN_MAX_TORRENTS_IN_ATTRIBUTES: Final = 10
MAX_MAX_TORRENTS_IN_ATTRIBUTES: Final = 2000

# --- Torrent states grouped into aggregate buckets ---------------------------------
# See qBittorrent WebUI API docs for the full list of possible `state` values.

STATES_DOWNLOADING: Final = frozenset(
    {"downloading", "metaDL", "forcedDL", "stalledDL", "queuedDL"}
)
STATES_SEEDING: Final = frozenset(
    {"uploading", "forcedUP", "stalledUP", "queuedUP"}
)
STATES_PAUSED: Final = frozenset({"pausedDL", "pausedUP", "stoppedDL", "stoppedUP"})
STATES_CHECKING: Final = frozenset(
    {"checkingDL", "checkingUP", "checkingResumeData"}
)
STATES_ERRORED: Final = frozenset({"error", "missingFiles"})

# --- Service names -------------------------------------------------------------------

SERVICE_ADD_TORRENT: Final = "add_torrent"
SERVICE_DELETE_TORRENTS: Final = "delete_torrents"
SERVICE_PAUSE_TORRENTS: Final = "pause_torrents"
SERVICE_RESUME_TORRENTS: Final = "resume_torrents"
SERVICE_RECHECK_TORRENTS: Final = "recheck_torrents"
SERVICE_REANNOUNCE_TORRENTS: Final = "reannounce_torrents"
SERVICE_FORCE_START: Final = "force_start"
SERVICE_SET_AUTO_MANAGEMENT: Final = "set_auto_management"
SERVICE_SET_SUPER_SEEDING: Final = "set_super_seeding"
SERVICE_INCREASE_PRIORITY: Final = "increase_priority"
SERVICE_DECREASE_PRIORITY: Final = "decrease_priority"
SERVICE_TOP_PRIORITY: Final = "top_priority"
SERVICE_BOTTOM_PRIORITY: Final = "bottom_priority"
SERVICE_SET_LOCATION: Final = "set_location"
SERVICE_SET_SAVE_PATH: Final = "set_save_path"
SERVICE_SET_CATEGORY: Final = "set_category"
SERVICE_ADD_TAGS: Final = "add_tags"
SERVICE_REMOVE_TAGS: Final = "remove_tags"
SERVICE_SET_SHARE_LIMITS: Final = "set_share_limits"
SERVICE_SET_UPLOAD_LIMIT: Final = "set_upload_limit"
SERVICE_SET_DOWNLOAD_LIMIT: Final = "set_download_limit"
SERVICE_RENAME_TORRENT: Final = "rename_torrent"
SERVICE_SET_FILE_PRIORITY: Final = "set_file_priority"
SERVICE_EXPORT_TORRENT: Final = "export_torrent"

SERVICE_CREATE_CATEGORY: Final = "create_category"
SERVICE_EDIT_CATEGORY: Final = "edit_category"
SERVICE_REMOVE_CATEGORIES: Final = "remove_categories"
SERVICE_CREATE_TAGS: Final = "create_tags"
SERVICE_DELETE_TAGS: Final = "delete_tags"

SERVICE_SET_SPEED_LIMITS_MODE: Final = "set_speed_limits_mode"
SERVICE_SET_GLOBAL_DOWNLOAD_LIMIT: Final = "set_global_download_limit"
SERVICE_SET_GLOBAL_UPLOAD_LIMIT: Final = "set_global_upload_limit"
SERVICE_BAN_PEERS: Final = "ban_peers"
SERVICE_SET_PREFERENCES: Final = "set_preferences"

SERVICE_RSS_ADD_FEED: Final = "rss_add_feed"
SERVICE_RSS_REMOVE_ITEM: Final = "rss_remove_item"
SERVICE_RSS_SET_RULE: Final = "rss_set_rule"
SERVICE_RSS_REMOVE_RULE: Final = "rss_remove_rule"

SERVICE_SEARCH_START: Final = "search_start"
SERVICE_SEARCH_STOP: Final = "search_stop"
SERVICE_SEARCH_GET_RESULTS: Final = "search_get_results"

SERVICE_GET_TORRENTS: Final = "get_torrents"
SERVICE_GET_APP_PREFERENCES: Final = "get_app_preferences"

SERVICE_CREATE_TORRENT: Final = "create_torrent"

# --- Service field names -------------------------------------------------------------

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_HASHES: Final = "hashes"
ATTR_HASH: Final = "hash"
