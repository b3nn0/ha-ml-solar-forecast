"""Coordinator for the ML Solar Forecast integration.

This module provides the MLSolarForecastCoordinator class, which handles:
- Data fetching and updating for solar power forecasting
- Model training and prediction using LightGBM
- Weather data collection and processing
- Integration with Home Assistant's recorder for historical data
"""

import asyncio
from datetime import UTC, datetime, timedelta

from astral import Observer, sun
import pandas as pd

from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import recorder
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_LOCATION,
    CONF_PRODUCTION_ENTITY,
    CONF_TRAINING_DAYS,
    DOMAIN,
    log,
)
from .lgbm import LGBM
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
            self.key, self.lat, self.lon, hass.config.path("ml-solar-forecast")
        )
        self.lgbm = LGBM(f"ml-solar-forecast-{config.data[CONF_PRODUCTION_ENTITY]}")
        # force retrain initially
        self.last_train_time: datetime = datetime.now(UTC) - timedelta(days=1)

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

            # Retrain nightly
            if (
                not await self.lgbm.is_trained()
                or self.last_train_time.date() != datetime.now(UTC).date()
            ):
                await self.retrain_model()

            # for actual forecasting, start from beginning of today
            today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            end = today + timedelta(days=14)
            fcstart = today - timedelta(days=60)

            log.debug(f"{self.key}: refreshing weather data {today} -> {end}")
            await self.weatherstore.refresh_range(today, end)
            log.debug(f"{self.key}: preparing data: {fcstart} -> {end}")
            data = await self._prepare_dataframe(fcstart, end, False)

            log.debug(f"{self.key}: computing forecast...")
            self.curr_forecast = await self.lgbm.predict(data, "power")

            log.debug(f"{self.key}: forecast update done")

        return self.curr_forecast

    async def retrain_model(self):
        """Retrain the LightGBM model with historical data.

        This method collects historical solar production data and retrains the model
        to improve future predictions. It is called nightly to incorporate new data.
        """
        end_time = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=self.config.data[CONF_TRAINING_DAYS])

        log.info(
            f"{self.key}: retraining forecast model {start_time} -> {end_time}. preparing data.."
        )

        data = await self._prepare_dataframe(start_time, end_time, True)
        data = data.dropna()

        log.debug(f"{self.key}: training model...")
        await self.lgbm.train(data, "power")
        log.debug(f"{self.key}: model retrain done.")
        self.last_train_time = datetime.now(UTC)

    async def _prepare_dataframe(
        self, start_time: datetime, end_time: datetime, with_power: bool
    ) -> pd.DataFrame:

        data = await self.weatherstore.get_data(start_time, end_time)
        data = data.copy()

        observer = Observer(latitude=self.lat, longitude=self.lon)

        data["azimuth"] = list(
            data.index.map(lambda t: sun.azimuth(observer, t + timedelta(minutes=7)))
        )
        data["elevation"] = list(
            data.index.map(lambda t: sun.elevation(observer, t + timedelta(minutes=7)))
        )

        if with_power:
            power = await self._collect_solar_history(start_time, end_time)
            data = pd.concat([data, power], axis=1)
        return data

    async def _collect_solar_history(
        self, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:

        log.debug(
            f"{self.key} fetching production statistics {start_time} -> {end_time}"
        )
        entity_id = self.config.data[CONF_PRODUCTION_ENTITY]

        statistic_id = {entity_id}
        types = {"sum"}
        units = {"energy": "Wh"}

        recorder_instance = recorder.get_instance(self.hass)

        df = pd.DataFrame()

        if end_time > start_time:
            # Fetch remaining required time from hourly data and spline it
            stats = await recorder_instance.async_add_executor_job(
                statistics_during_period,
                self.hass,
                start_time,
                end_time,
                statistic_id,
                "hour",
                units,
                types,
            )
            df = pd.DataFrame()
            df["time"] = [
                pd.Timestamp(r["start"], tz=UTC, unit="s") for r in stats[entity_id]
            ]
            df["power"] = [r["sum"] for r in stats[entity_id]]
            df = df.set_index("time")
            df["power"] = df["power"].diff()

            # For now, learning only runs on hourly aggregates instead of 15 minute intervals.
            # Since for one hour, 1W=1Wh, we just interpret our learning data as "watts" instead of "watt-hours".
            # -> the model predicts watts, we just divide by 4 in the forecast if needed

            df = await asyncio.to_thread(
                lambda: df.shift(30, "min").resample("15min").interpolate("cubic")
            )

        df["power"] = df["power"].clip(lower=0).apply(lambda p: 0 if p < 15 else p)
        return df.dropna()
