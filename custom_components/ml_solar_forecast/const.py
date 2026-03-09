"""Constants and configuration for the Machine Learning Solar Forecast integration."""

import logging

# Constants for the integration
DOMAIN = "ml_solar_forecast"
NAME = "Machine Learning Solar Forecast"
VERSION = "0.0.1"

CONF_LOCATION = "location"
CONF_PRODUCTION_ENTITY = "production_entity"
CONF_TRAINING_DAYS = "training_days"

log = logging.getLogger(__package__)
