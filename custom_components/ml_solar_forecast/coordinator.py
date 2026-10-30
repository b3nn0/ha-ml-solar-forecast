"""Coordinator for the ML Solar Forecast integration.

This module provides the MLSolarForecastCoordinator class, which handles:
- Data fetching and updating for solar power forecasting
- Model training and prediction using a gradient boosting model (hessboost)
- Weather data collection and processing
- Integration with Home Assistant's recorder for historical data
"""

import asyncio
from datetime import datetime, timedelta

from astral import Observer, sun
import numpy as np
import pandas as pd

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from .booster import Booster
from .const import (
    CONF_LOCATION,
    CONF_MAX_INVERTER_POWER_W,
    CONF_OPENMETEO_API_KEY,
    CONF_OPENMETEO_WEATHER_MODELS,
    CONF_PRODUCTION_ENTITY,
    CONF_TRAINING_DAYS,
    DOMAIN,
    log,
)
from .productionstore import ProductionStore
from .weatherstore import WeatherStore


class MLSolarForecastCoordinator(DataUpdateCoordinator):
    """The coordinator for fetching updates."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Init the coordinator."""
        super().__init__(
            hass,
            log,
            name=DOMAIN,
            config_entry=config,
            update_interval=timedelta(minutes=60),
        )

        self.hass = hass
        self.config = config
        self.key: str = config.data[CONF_PRODUCTION_ENTITY]
        self.lat: float = config.data[CONF_LOCATION]["latitude"]
        self.lon: float = config.data[CONF_LOCATION]["longitude"]

        self.weatherstore = WeatherStore(
            self.hass,
            self.key,
            self.lat,
            self.lon,
            hass.config.path("ml-solar-forecast"),
            config.data.get(CONF_OPENMETEO_API_KEY),
            config.data.get(CONF_OPENMETEO_WEATHER_MODELS),
        )
        self.productionstore = ProductionStore(
            self.hass,
            self.key,
            hass.config.path("ml-solar-forecast"),
            f"production_{config.data[CONF_PRODUCTION_ENTITY]}_v1",
        )
        self.booster = Booster(
            self.hass,
            f"ml-solar-forecast-{config.data[CONF_PRODUCTION_ENTITY]}",
            hass.config.path("ml-solar-forecast"),
        )
        # force retrain initially
        self.last_train_time: datetime = utcnow() - timedelta(days=1)

        self.curr_forecast: pd.DataFrame | None = None
        self.update_lock = asyncio.Lock()

    async def get_current_forecast(self) -> pd.DataFrame | None:
        """Get the current forecast data.

        If no forecast data is currently available, update the forecast data first.
        Returns the forecast data containing energy production in watt-hours (Wh) for each time period.
        """
        if self.curr_forecast is None:
            await self._async_update_data()
        return self.curr_forecast

    async def _async_update_data(self) -> pd.DataFrame | None:
        """Update data."""
        log.debug("updating forecast for %s", self.key)

        async with self.update_lock:
            if len(self.weatherstore.data) == 0:
                await self.weatherstore.load()
            if len(self.productionstore.data) == 0:
                await self.productionstore.load()

            # Retrain nightly
            if (
                not await self.booster.is_trained()
                or self.last_train_time.date() != utcnow().date()
            ):
                await self.retrain_model()

            # for actual forecasting, start from beginning of today
            today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            end = today + timedelta(days=14)
            fcstart = today - timedelta(days=60)

            log.debug(f"{self.key}: refreshing weather data {today} -> {end}")
            await self.weatherstore.refresh_range(today, end)
            log.debug(f"{self.key}: preparing data: {fcstart} -> {end}")
            data = await self._prepare_dataframe(fcstart, end, False)

            log.debug(f"{self.key}: computing forecast...")
            forecast = await self.booster.predict(data)
            # re-join original data so we have elevation levels to launder data
            forecast = pd.concat([data, forecast], axis=1)
            forecast = self.data_laundry(forecast)

            self.curr_forecast = forecast[["power"]]
            log.debug(f"{self.key}: forecast update done")

        return self.curr_forecast

    async def retrain_model(self):
        """Retrain the gradient boosting model with historical data.

        This method collects historical solar production data and retrains the model
        to improve future predictions. It is called nightly to incorporate new data.
        """
        end_time = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=self.config.data[CONF_TRAINING_DAYS])

        log.info(
            f"{self.key}: retraining forecast model {start_time} -> {end_time}. preparing data.."
        )

        data = await self._prepare_dataframe(start_time, end_time, True)
        data = data.dropna()

        log.debug(f"{self.key}: training model...")
        await self.booster.train(data)
        log.debug(f"{self.key}: model retrain done.")
        self.last_train_time = utcnow()

    async def _prepare_dataframe(
        self, start_time: datetime, end_time: datetime, with_power: bool
    ) -> pd.DataFrame:

        data = await self.weatherstore.get_data(start_time, end_time)
        data = data.copy()

        # Computing sun positions for thousands of timestamps is CPU-bound
        # (astral is pure Python), so keep it off the event loop.
        data = await self.hass.async_add_executor_job(self._add_solar_positions, data)

        if with_power:
            power = await self.productionstore.get_data(start_time, end_time)
            data = pd.concat([data, power], axis=1)
            data = self.data_laundry(data)

        return data.dropna()

    def _add_solar_positions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add azimuth and elevation columns for each timestamp in the index."""
        observer = Observer(latitude=self.lat, longitude=self.lon)
        data["azimuth"] = list(data.index.map(lambda t: sun.azimuth(observer, t)))
        data["elevation"] = list(data.index.map(lambda t: sun.elevation(observer, t)))
        return data

    def data_laundry(self, df: pd.DataFrame):
        """Cleans up data to matchs some basic assumptions.

        - Remove negative power
        - ensure power is 0 at night
        - remove power > inverter output.
        """

        df["power"] = df["power"].clip(lower=0)

        max_power = self.config.data.get(CONF_MAX_INVERTER_POWER_W)
        if max_power is not None:
            df.loc[df["power"] > max_power] = np.nan

        if "elevation" in df.columns:
            df.loc[df["elevation"] <= 0, "power"] = 0

        return df
