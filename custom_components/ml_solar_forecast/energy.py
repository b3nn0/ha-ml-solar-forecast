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
    power = (
        prediction["power"].clip(lower=0).apply(lambda p: 0 if p < 15 else p).to_dict()
    )

    result = {}
    for key, value in power.items():
        # we need Wh at 15 minute resolution, model delivered watts
        result[key.isoformat()] = value / 4.0

    return {"wh_hours": result}
