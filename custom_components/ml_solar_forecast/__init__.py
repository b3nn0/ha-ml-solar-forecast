"""The HA-ML Solar Forecast integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import MLSolarForecastCoordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up configured initegration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA-ML Solar Forecast from a config entry."""
    coordinator = MLSolarForecastCoordinator(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    # coordinator is only updated if there are listeners. We have no entities for now - create dummy listener.
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    await coordinator.async_config_entry_first_refresh()

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
