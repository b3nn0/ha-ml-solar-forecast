"""Constants and configuration for the Machine Learning Solar Forecast integration."""

import logging

# Constants for the integration
DOMAIN = "ml_solar_forecast"
NAME = "Machine Learning Solar Forecast"
VERSION = "0.0.0.dev0"


SERVICE_NAME_GET_FORECAST = "get_forecast"

SERVICE_DATA_START = "start"
SERVICE_DATA_END = "end"

CONF_LOCATION = "location"
CONF_PRODUCTION_ENTITY = "production_entity"
CONF_TRAINING_DAYS = "training_days"
CONF_MAX_INVERTER_POWER_W = "max_inverter_power_w"

log = logging.getLogger(__package__)
