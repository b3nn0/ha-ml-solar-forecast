"""The HA-ML Solar Forecast integration."""

from datetime import UTC, datetime, timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    SERVICE_DATA_END,
    SERVICE_DATA_START,
    SERVICE_NAME_GET_FORECAST,
    log,
)
from .coordinator import MLSolarForecastCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SCHEMA_GET_FORECAST = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Optional(SERVICE_DATA_START): cv.datetime,
        vol.Optional(SERVICE_DATA_END): cv.datetime,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up configured initegration."""

    async def async_get_forecast(call: ServiceCall) -> None:
        entry_id = call.data["entry_id"]
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator is None:
            log.error("entry_id %s is not valid", entry_id)
            return None
        fc = await coordinator.get_current_forecast()
        start = call.data.get(SERVICE_DATA_START)
        end = call.data.get(SERVICE_DATA_END)
        if not start:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end:
            end = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=14)
        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        data = fc.loc[start:end]
        return {k.isoformat(): v for k, v in data["power"].to_dict().items()}

    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_GET_FORECAST,
        async_get_forecast,
        schema=None,  # SERVICE_SCHEMA_GET_FORECAST,
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA-ML Solar Forecast from a config entry."""
    coordinator = MLSolarForecastCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.coordinator = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS) # ??
    # if unload_ok:
    #    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
