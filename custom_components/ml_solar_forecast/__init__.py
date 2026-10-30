"""The HA-ML Solar Forecast integration."""

from datetime import UTC, datetime, timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.selector import ConfigEntrySelector
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_DATA_CONFIG_ENTRY,
    SERVICE_DATA_END,
    SERVICE_DATA_RESOLUTION,
    SERVICE_DATA_START,
    SERVICE_NAME_GET_FORECAST,
)
from .coordinator import MLSolarForecastCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

RESOLUTION_RAW = "raw"
RESOLUTION_HOURLY = "hourly"

SERVICE_SCHEMA_GET_FORECAST = vol.Schema(
    {
        vol.Required(SERVICE_DATA_CONFIG_ENTRY): ConfigEntrySelector(
            {"integration": DOMAIN}
        ),
        vol.Optional(SERVICE_DATA_START): cv.datetime,
        vol.Optional(SERVICE_DATA_END): cv.datetime,
        vol.Optional(SERVICE_DATA_RESOLUTION, default=RESOLUTION_RAW): vol.In(
            (RESOLUTION_RAW, RESOLUTION_HOURLY)
        ),
    }
)


def _aggregate_hourly(
    watts: dict[datetime, float], wh_period: dict[datetime, float]
) -> tuple[dict[datetime, float], dict[datetime, float]]:
    """Aggregate the 15 minute series to whole hours.

    Each entry is bucketed by its hour-floor: power values are averaged,
    energy values are summed.
    """
    watts_buckets: dict[datetime, list[float]] = {}
    hourly_wh: dict[datetime, float] = {}

    for ts, watt in watts.items():
        hour = ts.replace(minute=0, second=0, microsecond=0)
        watts_buckets.setdefault(hour, []).append(watt)
        hourly_wh[hour] = hourly_wh.get(hour, 0) + wh_period[ts]

    hourly_watts = {
        hour: sum(values) / len(values) for hour, values in watts_buckets.items()
    }
    return hourly_watts, hourly_wh


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up configured initegration."""

    async def async_get_forecast(call: ServiceCall) -> ServiceResponse:
        """Return the solar production forecast time series.

        The response has two flat ``{ISO timestamp -> number}`` maps:

        - ``watts``: estimated instantaneous power in W at the timestamp.
        - ``wh_period``: energy in Wh produced during the 15 minute interval
          that starts at the timestamp.

        Timestamps are emitted in the Home Assistant timezone, not UTC.
        """
        entry = service.async_get_config_entry(
            hass, DOMAIN, call.data[SERVICE_DATA_CONFIG_ENTRY]
        )
        coordinator = hass.data[DOMAIN][entry.entry_id]
        fc = await coordinator.get_current_forecast()

        tz = await dt_util.async_get_time_zone(hass.config.time_zone)
        start = call.data.get(SERVICE_DATA_START)
        end = call.data.get(SERVICE_DATA_END)
        if start is None:
            start = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end is None:
            end = start + timedelta(days=14)
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=tz)
        if end < start:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="end_before_start",
            )

        start_utc = start.astimezone(UTC)
        end_utc = end.astimezone(UTC)

        watts = {
            ts: float(power)
            for ts, power in fc["power"].items()
            if start_utc <= ts < end_utc
        }
        wh_period = {ts: power / 4 for ts, power in watts.items()}
        if call.data[SERVICE_DATA_RESOLUTION] == RESOLUTION_HOURLY:
            watts, wh_period = _aggregate_hourly(watts, wh_period)

        watts_out: dict[str, JsonValueType] = {}
        wh_out: dict[str, JsonValueType] = {}
        for ts in sorted(watts):
            local_iso = ts.astimezone(tz).isoformat()
            watts_out[local_iso] = watts[ts]
            wh_out[local_iso] = wh_period[ts]
        return {"watts": watts_out, "wh_period": wh_out}

    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_GET_FORECAST,
        async_get_forecast,
        schema=SERVICE_SCHEMA_GET_FORECAST,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA-ML Solar Forecast from a config entry."""
    coordinator = MLSolarForecastCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.coordinator = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
