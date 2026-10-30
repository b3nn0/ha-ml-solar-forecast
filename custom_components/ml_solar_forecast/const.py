"""Constants and configuration for the Machine Learning Solar Forecast integration."""

import logging

from homeassistant.const import Platform

# Constants for the integration
DOMAIN = "ml_solar_forecast"
NAME = "Machine Learning Solar Forecast"
VERSION = "0.0.0.dev0"


PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_NAME_GET_FORECAST = "get_forecast"

SERVICE_DATA_CONFIG_ENTRY = "config_entry"
SERVICE_DATA_START = "start"
SERVICE_DATA_END = "end"
SERVICE_DATA_RESOLUTION = "resolution"

CONF_LOCATION = "location"
CONF_PRODUCTION_ENTITY = "production_entity"
CONF_TRAINING_DAYS = "training_days"
CONF_MAX_INVERTER_POWER_W = "max_inverter_power_w"
CONF_OPENMETEO_API_KEY = "openmeteo_api_key"
CONF_OPENMETEO_WEATHER_MODELS = "openmeteo_weather_models"

log = logging.getLogger(__package__)
