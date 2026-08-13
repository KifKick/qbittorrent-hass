"""Service handlers for the qBittorrent integration.

All qbittorrent-api calls are synchronous, so every call to the client goes
through `hass.async_add_executor_job`. Services are registered once at the
component level (not per config entry) and take a `config_entry_id` field so
a specific qBittorrent instance can be targeted when multiple are configured.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from functools import partial
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Conflict409Error,
    Forbidden403Error,
    NotFound404Error,
)

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_HASH,
    ATTR_HASHES,
    DOMAIN,
    SERVICE_ADD_TAGS,
    SERVICE_ADD_TORRENT,
    SERVICE_BAN_PEERS,
    SERVICE_BOTTOM_PRIORITY,
    SERVICE_CREATE_CATEGORY,
    SERVICE_CREATE_TAGS,
    SERVICE_CREATE_TORRENT,
    SERVICE_DECREASE_PRIORITY,
    SERVICE_DELETE_TAGS,
    SERVICE_DELETE_TORRENTS,
    SERVICE_EDIT_CATEGORY,
    SERVICE_EXPORT_TORRENT,
    SERVICE_FORCE_START,
    SERVICE_GET_APP_PREFERENCES,
    SERVICE_GET_TORRENTS,
    SERVICE_INCREASE_PRIORITY,
    SERVICE_PAUSE_TORRENTS,
    SERVICE_REANNOUNCE_TORRENTS,
    SERVICE_RECHECK_TORRENTS,
    SERVICE_REMOVE_CATEGORIES,
    SERVICE_REMOVE_TAGS,
    SERVICE_RENAME_TORRENT,
    SERVICE_RESUME_TORRENTS,
    SERVICE_RSS_ADD_FEED,
    SERVICE_RSS_REMOVE_ITEM,
    SERVICE_RSS_REMOVE_RULE,
    SERVICE_RSS_SET_RULE,
    SERVICE_SEARCH_GET_RESULTS,
    SERVICE_SEARCH_START,
    SERVICE_SEARCH_STOP,
    SERVICE_SET_AUTO_MANAGEMENT,
    SERVICE_SET_CATEGORY,
    SERVICE_SET_DOWNLOAD_LIMIT,
    SERVICE_SET_FILE_PRIORITY,
    SERVICE_SET_GLOBAL_DOWNLOAD_LIMIT,
    SERVICE_SET_GLOBAL_UPLOAD_LIMIT,
    SERVICE_SET_LOCATION,
    SERVICE_SET_PREFERENCES,
    SERVICE_SET_SAVE_PATH,
    SERVICE_SET_SHARE_LIMITS,
    SERVICE_SET_SPEED_LIMITS_MODE,
    SERVICE_SET_SUPER_SEEDING,
    SERVICE_SET_UPLOAD_LIMIT,
    SERVICE_TOP_PRIORITY,
)

_LOGGER = logging.getLogger(__name__)

HASHES_SCHEMA = vol.All(cv.ensure_list, [cv.string])


def _base_schema(extra: dict[Any, Any] | None = None) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
            **(extra or {}),
        }
    )


def _hashes_schema(extra: dict[Any, Any] | None = None) -> vol.Schema:
    return _base_schema({vol.Required(ATTR_HASHES): HASHES_SCHEMA, **(extra or {})})


def _get_coordinator(hass: HomeAssistant, config_entry_id: str):
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            f"'{config_entry_id}' is not a qBittorrent config entry"
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            f"qBittorrent config entry '{entry.title}' is not currently loaded"
        )
    return entry.runtime_data


async def _async_call(hass: HomeAssistant, coordinator, func: Callable, /, **kwargs: Any) -> Any:
    """Run a synchronous qbittorrent-api call in the executor with error mapping."""
    try:
        return await hass.async_add_executor_job(partial(func, **kwargs))
    except NotFound404Error as err:
        raise ServiceValidationError(f"Torrent(s) or item not found: {err}") from err
    except Conflict409Error as err:
        raise ServiceValidationError(
            f"qBittorrent rejected the request due to a conflicting state: {err}"
        ) from err
    except Forbidden403Error as err:
        coordinator.config_entry.async_start_reauth(hass)
        raise HomeAssistantError(
            "qBittorrent rejected the request; re-authentication has been requested"
        ) from err
    except APIConnectionError as err:
        raise HomeAssistantError(f"Cannot reach qBittorrent: {err}") from err
    except (NotImplementedError, AttributeError) as err:
        raise HomeAssistantError(
            f"This action is not supported by the connected qBittorrent/library version: {err}"
        ) from err


def _dictify(obj: Any) -> Any:
    """Convert qbittorrent-api's dict-like response wrappers into plain JSON-safe types."""
    if isinstance(obj, dict):
        return {key: _dictify(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dictify(item) for item in obj]
    return obj


# Torrent actions that only need one or more torrent hashes, optionally with a
# handful of extra fields whose names already match the qbittorrent-api kwarg.
HASH_ACTION_SERVICES: tuple[tuple[str, str, dict[Any, Any]], ...] = (
    (SERVICE_PAUSE_TORRENTS, "torrents_pause", {}),
    (SERVICE_RESUME_TORRENTS, "torrents_resume", {}),
    (SERVICE_RECHECK_TORRENTS, "torrents_recheck", {}),
    (SERVICE_REANNOUNCE_TORRENTS, "torrents_reannounce", {}),
    (SERVICE_INCREASE_PRIORITY, "torrents_increase_priority", {}),
    (SERVICE_DECREASE_PRIORITY, "torrents_decrease_priority", {}),
    (SERVICE_TOP_PRIORITY, "torrents_top_priority", {}),
    (SERVICE_BOTTOM_PRIORITY, "torrents_bottom_priority", {}),
    (
        SERVICE_FORCE_START,
        "torrents_set_force_start",
        {vol.Required("enable"): cv.boolean},
    ),
    (
        SERVICE_SET_AUTO_MANAGEMENT,
        "torrents_set_auto_management",
        {vol.Required("enable"): cv.boolean},
    ),
    (
        SERVICE_SET_SUPER_SEEDING,
        "torrents_set_super_seeding",
        {vol.Required("enable"): cv.boolean},
    ),
    (
        SERVICE_DELETE_TORRENTS,
        "torrents_delete",
        {vol.Optional("delete_files", default=False): cv.boolean},
    ),
    (SERVICE_SET_CATEGORY, "torrents_set_category", {vol.Required("category"): cv.string}),
    (SERVICE_SET_LOCATION, "torrents_set_location", {vol.Required("location"): cv.string}),
    (SERVICE_SET_SAVE_PATH, "torrents_set_save_path", {vol.Required("save_path"): cv.string}),
    (
        SERVICE_ADD_TAGS,
        "torrents_add_tags",
        {vol.Required("tags"): HASHES_SCHEMA},
    ),
    (
        SERVICE_REMOVE_TAGS,
        "torrents_remove_tags",
        {vol.Required("tags"): HASHES_SCHEMA},
    ),
    (
        SERVICE_SET_UPLOAD_LIMIT,
        "torrents_set_upload_limit",
        {vol.Required("limit"): vol.Coerce(int)},
    ),
    (
        SERVICE_SET_DOWNLOAD_LIMIT,
        "torrents_set_download_limit",
        {vol.Required("limit"): vol.Coerce(int)},
    ),
    (
        SERVICE_SET_SHARE_LIMITS,
        "torrents_set_share_limits",
        {
            vol.Optional("ratio_limit"): vol.Coerce(float),
            vol.Optional("seeding_time_limit"): vol.Coerce(int),
            vol.Optional("inactive_seeding_time_limit"): vol.Coerce(int),
        },
    ),
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register all qBittorrent services. Called once from async_setup."""

    for service_name, method_name, extra_fields in HASH_ACTION_SERVICES:
        _register_hash_action_service(hass, service_name, method_name, extra_fields)

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_TORRENT, _make_add_torrent_handler(hass), schema=_add_torrent_schema()
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RENAME_TORRENT,
        _make_rename_torrent_handler(hass),
        schema=_base_schema(
            {vol.Required(ATTR_HASH): cv.string, vol.Required("name"): cv.string}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FILE_PRIORITY,
        _make_set_file_priority_handler(hass),
        schema=_base_schema(
            {
                vol.Required(ATTR_HASH): cv.string,
                vol.Required("file_ids"): HASHES_SCHEMA,
                vol.Required("priority"): vol.Coerce(int),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_TORRENT,
        _make_export_torrent_handler(hass),
        schema=_base_schema({vol.Required(ATTR_HASH): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )

    # Categories / tags
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_CATEGORY,
        _make_category_handler(hass, "torrents_create_category"),
        schema=_base_schema(
            {
                vol.Required("name"): cv.string,
                vol.Optional("save_path"): cv.string,
                vol.Optional("download_path"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EDIT_CATEGORY,
        _make_category_handler(hass, "torrents_edit_category"),
        schema=_base_schema(
            {
                vol.Required("name"): cv.string,
                vol.Optional("save_path"): cv.string,
                vol.Optional("download_path"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_CATEGORIES,
        _make_names_handler(hass, "torrents_remove_categories", "categories"),
        schema=_base_schema({vol.Required("names"): HASHES_SCHEMA}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_TAGS,
        _make_names_handler(hass, "torrents_create_tags", "tags"),
        schema=_base_schema({vol.Required("tags"): HASHES_SCHEMA}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_TAGS,
        _make_names_handler(hass, "torrents_delete_tags", "tags"),
        schema=_base_schema({vol.Required("tags"): HASHES_SCHEMA}),
    )

    # Transfer / global
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SPEED_LIMITS_MODE,
        _make_transfer_handler(hass, "transfer_set_speed_limits_mode", "intended_state", "enabled"),
        schema=_base_schema({vol.Required("enabled"): cv.boolean}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GLOBAL_DOWNLOAD_LIMIT,
        _make_transfer_handler(hass, "transfer_set_download_limit", "limit", "limit"),
        schema=_base_schema({vol.Required("limit"): vol.Coerce(int)}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GLOBAL_UPLOAD_LIMIT,
        _make_transfer_handler(hass, "transfer_set_upload_limit", "limit", "limit"),
        schema=_base_schema({vol.Required("limit"): vol.Coerce(int)}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BAN_PEERS,
        _make_transfer_handler(hass, "transfer_ban_peers", "peers", "peers"),
        schema=_base_schema({vol.Required("peers"): HASHES_SCHEMA}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PREFERENCES,
        _make_set_preferences_handler(hass),
        schema=_base_schema({vol.Required("preferences"): dict}),
    )

    # RSS
    hass.services.async_register(
        DOMAIN,
        SERVICE_RSS_ADD_FEED,
        _make_rss_handler(hass, "rss_add_feed", {"url": "url", "path": "item_path"}),
        schema=_base_schema(
            {vol.Required("url"): cv.string, vol.Optional("path", default=""): cv.string}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RSS_REMOVE_ITEM,
        _make_rss_handler(hass, "rss_remove_item", {"path": "item_path"}),
        schema=_base_schema({vol.Required("path"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RSS_SET_RULE,
        _make_rss_handler(hass, "rss_set_rule", {"rule_name": "rule_name", "rule_def": "rule_def"}),
        schema=_base_schema({vol.Required("rule_name"): cv.string, vol.Required("rule_def"): dict}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RSS_REMOVE_RULE,
        _make_rss_handler(hass, "rss_remove_rule", {"rule_name": "rule_name"}),
        schema=_base_schema({vol.Required("rule_name"): cv.string}),
    )

    # Search
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_START,
        _make_search_start_handler(hass),
        schema=_base_schema(
            {
                vol.Required("pattern"): cv.string,
                vol.Optional("plugins", default=["enabled"]): HASHES_SCHEMA,
                vol.Optional("category", default="all"): cv.string,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_STOP,
        _make_search_stop_handler(hass),
        schema=_base_schema({vol.Required("search_id"): vol.Coerce(int)}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_GET_RESULTS,
        _make_search_results_handler(hass),
        schema=_base_schema(
            {
                vol.Required("search_id"): vol.Coerce(int),
                vol.Optional("limit"): vol.Coerce(int),
                vol.Optional("offset"): vol.Coerce(int),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    # Lookup / diagnostics
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TORRENTS,
        _make_get_torrents_handler(hass),
        schema=_base_schema(
            {
                vol.Optional("status_filter"): cv.string,
                vol.Optional("category"): cv.string,
                vol.Optional("tag"): cv.string,
                vol.Optional("sort"): cv.string,
                vol.Optional("reverse"): cv.boolean,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_APP_PREFERENCES,
        _make_get_app_preferences_handler(hass),
        schema=_base_schema(),
        supports_response=SupportsResponse.ONLY,
    )

    # Torrent creator (newest, most version-fragile part of the API)
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_TORRENT,
        _make_create_torrent_handler(hass),
        schema=_base_schema(
            {
                vol.Required("source_path"): cv.string,
                vol.Optional("format"): vol.In(["v1", "v2", "hybrid"]),
                vol.Optional("is_private"): cv.boolean,
                vol.Optional("piece_size"): vol.Coerce(int),
                vol.Optional("comment"): cv.string,
                vol.Optional("trackers"): HASHES_SCHEMA,
                vol.Optional("start_seeding"): cv.boolean,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )


def _register_hash_action_service(
    hass: HomeAssistant, service_name: str, method_name: str, extra_fields: dict[Any, Any]
) -> None:
    schema = _hashes_schema(extra_fields)

    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        kwargs = {
            key: value
            for key, value in call.data.items()
            if key not in (ATTR_CONFIG_ENTRY_ID, ATTR_HASHES)
        }
        method = getattr(coordinator.client, method_name)
        await _async_call(
            hass, coordinator, method, torrent_hashes=call.data[ATTR_HASHES], **kwargs
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, service_name, handler, schema=schema)


def _add_torrent_schema() -> vol.Schema:
    return _base_schema(
        {
            vol.Optional("urls"): HASHES_SCHEMA,
            vol.Optional("torrent_file_path"): cv.string,
            vol.Optional("torrent_file_content"): cv.string,
            vol.Optional("save_path"): cv.string,
            vol.Optional("category"): cv.string,
            vol.Optional("tags"): HASHES_SCHEMA,
            vol.Optional("paused"): cv.boolean,
            vol.Optional("skip_checking"): cv.boolean,
            vol.Optional("root_folder"): cv.boolean,
            vol.Optional("rename"): cv.string,
            vol.Optional("upload_limit"): vol.Coerce(int),
            vol.Optional("download_limit"): vol.Coerce(int),
            vol.Optional("auto_torrent_management"): cv.boolean,
            vol.Optional("sequential_download"): cv.boolean,
            vol.Optional("first_last_piece_priority"): cv.boolean,
            vol.Optional("content_layout"): vol.In(["Original", "Subfolder", "NoSubfolder"]),
            vol.Optional("ratio_limit"): vol.Coerce(float),
            vol.Optional("seeding_time_limit"): vol.Coerce(int),
        }
    )


def _make_add_torrent_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        data = call.data

        if not data.get("urls") and not data.get("torrent_file_path") and not data.get(
            "torrent_file_content"
        ):
            raise ServiceValidationError(
                "Provide at least one of 'urls', 'torrent_file_path' or 'torrent_file_content'"
            )

        torrent_files: list[Any] = []
        if path := data.get("torrent_file_path"):
            if not hass.config.is_allowed_path(path):
                raise ServiceValidationError(
                    f"'{path}' is not in an allowed directory (see allowlist_external_dirs)"
                )
            torrent_files.append(path)
        if content := data.get("torrent_file_content"):
            torrent_files.append(base64.b64decode(content))

        await _async_call(
            hass,
            coordinator,
            coordinator.client.torrents_add,
            urls=data.get("urls"),
            torrent_files=torrent_files or None,
            save_path=data.get("save_path"),
            category=data.get("category"),
            tags=data.get("tags"),
            is_paused=data.get("paused"),
            is_skip_checking=data.get("skip_checking"),
            is_root_folder=data.get("root_folder"),
            rename=data.get("rename"),
            upload_limit=data.get("upload_limit"),
            download_limit=data.get("download_limit"),
            use_auto_torrent_management=data.get("auto_torrent_management"),
            is_sequential_download=data.get("sequential_download"),
            is_first_last_piece_priority=data.get("first_last_piece_priority"),
            content_layout=data.get("content_layout"),
            ratio_limit=data.get("ratio_limit"),
            seeding_time_limit=data.get("seeding_time_limit"),
        )
        await coordinator.async_request_refresh()

    return handler


def _make_rename_torrent_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        await _async_call(
            hass,
            coordinator,
            coordinator.client.torrents_rename,
            torrent_hash=call.data[ATTR_HASH],
            new_torrent_name=call.data["name"],
        )
        await coordinator.async_request_refresh()

    return handler


def _make_set_file_priority_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        await _async_call(
            hass,
            coordinator,
            coordinator.client.torrents_file_priority,
            torrent_hash=call.data[ATTR_HASH],
            file_ids=call.data["file_ids"],
            priority=call.data["priority"],
        )

    return handler


def _make_export_torrent_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        torrent_bytes: bytes = await _async_call(
            hass,
            coordinator,
            coordinator.client.torrents_export,
            torrent_hash=call.data[ATTR_HASH],
        )
        return {
            "hash": call.data[ATTR_HASH],
            "torrent_file_base64": base64.b64encode(torrent_bytes).decode("ascii"),
        }

    return handler


def _make_category_handler(hass: HomeAssistant, method_name: str) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        method = getattr(coordinator.client, method_name)
        await _async_call(
            hass,
            coordinator,
            method,
            name=call.data["name"],
            save_path=call.data.get("save_path"),
            download_path=call.data.get("download_path"),
        )
        await coordinator.async_request_refresh()

    return handler


def _make_names_handler(hass: HomeAssistant, method_name: str, field: str) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        method = getattr(coordinator.client, method_name)
        await _async_call(hass, coordinator, method, **{field: call.data[field]})
        await coordinator.async_request_refresh()

    return handler


def _make_transfer_handler(
    hass: HomeAssistant, method_name: str, client_kwarg: str, field: str
) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        method = getattr(coordinator.client, method_name)
        await _async_call(hass, coordinator, method, **{client_kwarg: call.data[field]})
        await coordinator.async_request_refresh()

    return handler


def _make_set_preferences_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        await _async_call(
            hass,
            coordinator,
            coordinator.client.app_set_preferences,
            prefs=call.data["preferences"],
        )
        await coordinator.async_request_refresh()

    return handler


def _make_rss_handler(
    hass: HomeAssistant, method_name: str, field_map: dict[str, str]
) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        method = getattr(coordinator.client, method_name)
        kwargs = {
            kwarg: call.data[field] for field, kwarg in field_map.items() if field in call.data
        }
        await _async_call(hass, coordinator, method, **kwargs)

    return handler


def _make_search_start_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        result = await _async_call(
            hass,
            coordinator,
            coordinator.client.search_start,
            pattern=call.data["pattern"],
            plugins=call.data["plugins"],
            category=call.data["category"],
        )
        return _dictify(result)

    return handler


def _make_search_stop_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        await _async_call(
            hass, coordinator, coordinator.client.search_stop, search_id=call.data["search_id"]
        )

    return handler


def _make_search_results_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        result = await _async_call(
            hass,
            coordinator,
            coordinator.client.search_results,
            search_id=call.data["search_id"],
            limit=call.data.get("limit"),
            offset=call.data.get("offset"),
        )
        return _dictify(result)

    return handler


def _make_get_torrents_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        result = await _async_call(
            hass,
            coordinator,
            coordinator.client.torrents_info,
            status_filter=call.data.get("status_filter"),
            category=call.data.get("category"),
            tag=call.data.get("tag"),
            sort=call.data.get("sort"),
            reverse=call.data.get("reverse"),
        )
        return {"torrents": _dictify(result)}

    return handler


def _make_get_app_preferences_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        result = await _async_call(hass, coordinator, coordinator.client.app_preferences)
        return _dictify(result)

    return handler


def _make_create_torrent_handler(hass: HomeAssistant) -> Callable:
    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        result = await _async_call(
            hass,
            coordinator,
            coordinator.client.torrentcreator_add_task,
            source_path=call.data["source_path"],
            format=call.data.get("format"),
            is_private=call.data.get("is_private"),
            piece_size=call.data.get("piece_size"),
            comment=call.data.get("comment"),
            trackers=call.data.get("trackers"),
            start_seeding=call.data.get("start_seeding"),
        )
        return _dictify(result)

    return handler
