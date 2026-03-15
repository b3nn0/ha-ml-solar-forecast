"""Energy platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MLSolarForecastCoordinator


async def async_get_solar_forecast(
    hass: HomeAssistant, config_entry_id: str
) -> dict[str, dict[str, float | int]] | None:
    """Get solar forecast for a config entry ID."""

    if (coordinator := hass.data[DOMAIN].get(config_entry_id)) is None:
        return None

    assert isinstance(coordinator, MLSolarForecastCoordinator)

    prediction = await coordinator.get_current_forecast()
    # weather data is always at the start of each 15 minute slot, but we want the average of each 15 minute slot.
    # Then convert to energy
    power = (prediction["power"] + prediction["power"].shift(-1)) / 2
    energy = (power / 4).to_dict()

    result = {}
    for key, value in energy.items():
        # we need Wh at 15 minute resolution, model delivered watts
        result[key.isoformat()] = value

    return {"wh_hours": result}
