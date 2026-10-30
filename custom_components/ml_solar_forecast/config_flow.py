"""Configuration flow for the HA-ML Solar Forecast integration."""

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
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

    def _data_schema(self) -> vol.Schema:
        """Return the schema for the configuration form."""
        return vol.Schema(
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
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="ML Solar Forecast", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._data_schema(),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        if user_input is not None:
            entry = self._get_reconfigure_entry()
            self.hass.config_entries.async_update_entry(entry, data=user_input)
            if not entry.update_listeners:
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
            return self.async_abort(
                reason="reconfigure_successful",
                translation_domain=HOMEASSISTANT_DOMAIN,
            )

        entry = self._get_reconfigure_entry()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                self._data_schema(), entry.data
            ),
        )
