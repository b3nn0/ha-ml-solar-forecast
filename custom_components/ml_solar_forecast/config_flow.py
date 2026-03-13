"""Configuration flow for the HA-ML Solar Forecast integration."""

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    NumberSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_LOCATION,
    CONF_MAX_INVERTER_POWER_W,
    CONF_OPENMETEO_API_KEY,
    CONF_OPENMETEO_WEATHER_MODELS,
    CONF_PRODUCTION_ENTITY,
    CONF_TRAINING_DAYS,
    DOMAIN,
)


class MLSolarForecastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for ML Solar Forecast integration."""

    VERSION = 1
    config_data: dict[str, any]

    def __init__(self) -> None:
        """Initialize the ML Solar Forecast config flow."""
        self.config_data = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.config_data.update(user_input)
            return self.async_create_entry(title="ML Solar Forecast", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION,
                        default={
                            "latitude": self.hass.config.latitude,
                            "longitude": self.hass.config.longitude,
                        },
                    ): LocationSelector({"radius": False}),
                    vol.Required(CONF_PRODUCTION_ENTITY): EntitySelector(
                        EntitySelectorConfig(
                            multiple=False,
                            filter=EntityFilterSelectorConfig(
                                device_class=SensorDeviceClass.ENERGY
                            ),
                        )
                    ),
                    vol.Required(
                        CONF_TRAINING_DAYS,
                        default=180,
                    ): NumberSelector({}),
                    vol.Optional(CONF_MAX_INVERTER_POWER_W): NumberSelector({}),
                    vol.Optional(
                        CONF_OPENMETEO_API_KEY,
                        default="",
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                    vol.Optional(
                        CONF_OPENMETEO_WEATHER_MODELS,
                        default="",
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                }
            ),
        )
