"""Sensor platform for the HA-ML Solar Forecast integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MLSolarForecastCoordinator

PARALLEL_UPDATES = 0


class MLForecast:
    """Computed views on the raw forecast dataframe delivered by the coordinator.

    The forecast contains estimated power in watts for each 15 minute slot,
    stamped at the start of the slot. Energy per slot is therefore watts / 4.
    """

    def __init__(self, forecast: pd.DataFrame) -> None:
        """Initialize with the forecast dataframe from the coordinator."""
        self._power = forecast["power"]

    def _day(self, day: datetime) -> pd.Series:
        day = day.astimezone(UTC)
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        return self._power.loc[
            start : start + timedelta(days=1) - timedelta(minutes=15)
        ]

    def _energy_hours(self, start: datetime, end: datetime) -> float | None:
        series = self._power.loc[start : end - timedelta(minutes=15)]
        if series.empty:
            return None
        return float(series.sum() / 4)

    @property
    def energy_today(self) -> float | None:
        """Return the predicted energy of today in Wh."""
        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return self._energy_hours(start, start + timedelta(days=1))

    @property
    def energy_today_remaining(self) -> float | None:
        """Return the predicted energy remaining for today in Wh."""
        now = datetime.now(UTC)
        start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
        start += timedelta(minutes=15)
        end = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if start >= end:
            return None
        return self._energy_hours(start, end)

    @property
    def energy_tomorrow(self) -> float | None:
        """Return the predicted energy of tomorrow in Wh."""
        now = datetime.now(UTC)
        start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return self._energy_hours(start, start + timedelta(days=1))

    @property
    def power_now(self) -> float | None:
        """Return the predicted power for the current 15 minute slot in W."""
        now = datetime.now(UTC)
        start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
        series = self._power.loc[start : start + timedelta(minutes=15)]
        if series.empty:
            return None
        return float(series.iloc[0])

    def _highest_peak_time(self, day: datetime) -> datetime | None:
        series = self._day(day)
        if series.empty or series.max() <= 0:
            return None
        return series.idxmax().to_pydatetime()

    @property
    def power_highest_peak_time_today(self) -> datetime | None:
        """Return the timestamp of the highest power peak today."""
        return self._highest_peak_time(datetime.now(UTC))

    @property
    def power_highest_peak_time_tomorrow(self) -> datetime | None:
        """Return the timestamp of the highest power peak tomorrow."""
        return self._highest_peak_time(datetime.now(UTC) + timedelta(days=1))

    @property
    def energy_current_hour(self) -> float | None:
        """Return the predicted energy of the current hour in Wh."""
        now = datetime.now(UTC)
        start = now.replace(minute=0, second=0, microsecond=0)
        return self._energy_hours(start, start + timedelta(hours=1))

    @property
    def energy_next_hour(self) -> float | None:
        """Return the predicted energy of the next full hour in Wh."""
        now = datetime.now(UTC)
        start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return self._energy_hours(start, start + timedelta(hours=1))


@dataclass(frozen=True)
class MLSolarForecastSensorEntityDescription(SensorEntityDescription):
    """Describes an ML Solar Forecast sensor."""

    value_fn: Callable[[MLForecast], StateType | datetime] | None = None


SENSORS: tuple[MLSolarForecastSensorEntityDescription, ...] = (
    MLSolarForecastSensorEntityDescription(
        key="energy_production_today",
        translation_key="energy_production_today",
        value_fn=lambda forecast: forecast.energy_today,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    MLSolarForecastSensorEntityDescription(
        key="energy_production_today_remaining",
        translation_key="energy_production_today_remaining",
        value_fn=lambda forecast: forecast.energy_today_remaining,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    MLSolarForecastSensorEntityDescription(
        key="energy_production_tomorrow",
        translation_key="energy_production_tomorrow",
        value_fn=lambda forecast: forecast.energy_tomorrow,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    MLSolarForecastSensorEntityDescription(
        key="power_highest_peak_time_today",
        translation_key="power_highest_peak_time_today",
        value_fn=lambda forecast: forecast.power_highest_peak_time_today,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    MLSolarForecastSensorEntityDescription(
        key="power_highest_peak_time_tomorrow",
        translation_key="power_highest_peak_time_tomorrow",
        value_fn=lambda forecast: forecast.power_highest_peak_time_tomorrow,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    MLSolarForecastSensorEntityDescription(
        key="power_production_now",
        translation_key="power_production_now",
        value_fn=lambda forecast: forecast.power_now,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    MLSolarForecastSensorEntityDescription(
        key="energy_current_hour",
        translation_key="energy_current_hour",
        value_fn=lambda forecast: forecast.energy_current_hour,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
    MLSolarForecastSensorEntityDescription(
        key="energy_next_hour",
        translation_key="energy_next_hour",
        value_fn=lambda forecast: forecast.energy_next_hour,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up ML Solar Forecast sensors from a config entry."""
    coordinator: MLSolarForecastCoordinator = entry.coordinator

    async_add_entities(
        [
            MLSolarForecastSensorEntity(
                entry_id=entry.entry_id,
                coordinator=coordinator,
                entity_description=entity_description,
            )
            for entity_description in SENSORS
        ]
        + [
            MLSolarForecastRawSensorEntity(
                entry_id=entry.entry_id, coordinator=coordinator
            )
        ]
    )


class MLSolarForecastSensorEntity(
    CoordinatorEntity[MLSolarForecastCoordinator], SensorEntity
):
    """Defines an ML Solar Forecast sensor."""

    entity_description: MLSolarForecastSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        entry_id: str,
        coordinator: MLSolarForecastCoordinator,
        entity_description: MLSolarForecastSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            name="ML Solar Forecast",
            manufacturer="HA-ML Solar Forecast",
            configuration_url="https://github.com/b3nn0/ha-ml-solar-forecast",
        )

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        assert self.entity_description.value_fn is not None
        return self.entity_description.value_fn(MLForecast(self.coordinator.data))


class MLSolarForecastRawSensorEntity(
    CoordinatorEntity[MLSolarForecastCoordinator], SensorEntity
):
    """Full raw forecast as attributes, keyed by ISO timestamp.

    Attributes are excluded from the recorder to keep the database small.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "forecast_raw_data"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(
        self,
        *,
        entry_id: str,
        coordinator: MLSolarForecastCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{entry_id}_forecast_raw_data"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            name="ML Solar Forecast",
            manufacturer="HA-ML Solar Forecast",
            configuration_url="https://github.com/b3nn0/ha-ml-solar-forecast",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last forecast data point."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.index[-1].to_pydatetime()

    @property
    def extra_state_attributes(self) -> dict[str, float]:
        """Return the raw forecast power (W) per 15 minute slot, from today on."""
        if self.coordinator.data is None:
            return {}
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            ts.isoformat(): float(power)
            for ts, power in self.coordinator.data["power"].loc[today:].items()
        }
