"""Store and cache solar production history on a 15 minute grid.

This module provides the ProductionStore class, which:
- Fetches production statistics from Home Assistant's recorder
- Prefers 5 minute (short-term) statistics while they are still retained,
  falling back to hourly (long-term) statistics for older ranges
- Normalizes all data to watts on a 15 minute grid and persists it,
  accumulating history beyond the recorder's own retention limits
"""

from datetime import UTC, datetime, timedelta
from typing import override

import pandas as pd

from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.helpers import recorder

from .const import log
from .datastore import DataStore


class ProductionStore(DataStore):
    """Caches solar production as watts on a 15 minute grid."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        storage_dir: str | None = None,
        storage_fn_prefix: str | None = None,
    ) -> None:
        """Initialize the ProductionStore for a production entity."""
        super().__init__(hass, storage_dir, storage_fn_prefix)
        self.entity_id = entity_id

    @override
    def get_next_horizon_revalidation_time(self) -> datetime | None:
        return self.last_updated + timedelta(hours=6)

    @override
    async def get_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch data between the given timestamps, filling missing ranges.

        Production data always ends in the past, so the horizon bookkeeping of
        the base class would lock out freshly recorded data.
        """
        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        await self.fetch_missing_data(start, end)
        return self.data.loc[start:end]

    @override
    async def fetch_missing_data(self, start: datetime, end: datetime) -> bool:
        """Fetch missing ranges, preferring 5 minute statistics where available."""
        updated = False

        # Two passes: 5 minute stats first (they may only cover part of the
        # range depending on recorder retention), then fill whatever is still
        # missing from hourly stats. This avoids relying on retention
        # bookkeeping, e.g. when purge_keep_days was changed after data was
        # already purged.
        for rstart, rend in self.gen_missing_date_ranges(start, end):
            updated = await self._fetch_5min(rstart, rend) or updated

        for rstart, rend in self.gen_missing_date_ranges(start, end):
            updated = await self._fetch_hourly(rstart, rend) or updated

        if updated:
            await self.serialize()
        return updated

    async def _fetch_5min(self, start: datetime, end: datetime) -> bool:
        """Fetch 5 minute statistics and grid them to 15 minute slots."""
        log.debug(
            "%s: fetching 5 minute production stats %s -> %s",
            self.entity_id,
            start,
            end,
        )
        # one extra bucket back so diff() can derive the first bucket's delta
        df = await self._get_stats(start - timedelta(minutes=5), end, "5minute")
        if df.empty:
            return False

        def _transform(df: pd.DataFrame) -> pd.DataFrame:
            # sums are the cumulative meter total, so diff to get Wh per
            # bucket; a 5 minute bucket: Wh -> W
            df["power"] = df["power"].diff() * 12
            return df.resample("15min").mean()

        df = await self.hass.async_add_executor_job(_transform, df)
        return self._store(df)

    async def _fetch_hourly(self, start: datetime, end: datetime) -> bool:
        """Fetch hourly statistics and grid them to 15 minute slots."""
        log.debug(
            "%s: fetching hourly production stats %s -> %s", self.entity_id, start, end
        )
        # one extra hour back so diff() can derive the first bucket's delta
        df = await self._get_stats(start - timedelta(hours=1), end, "hour")
        if df.empty:
            return False

        def _transform(df: pd.DataFrame) -> pd.DataFrame:
            # long-term sums are cumulative, so diff to get Wh per hour bucket
            df["power"] = df["power"].diff()
            # an hourly bucket's energy is spread over the hour, so center it
            # before interpolating onto the 15 minute grid. interpolate("cubic")
            # lazily imports scipy, so this must not run on the event loop.
            df = df.shift(30, "min")
            # cubic splines need >= 4 points, small gaps only have a few
            resampled = df.resample("15min")
            if df["power"].count() >= 4:
                return resampled.interpolate("cubic")
            return resampled.interpolate("linear")

        df = await self.hass.async_add_executor_job(_transform, df)
        # existing (finer) data wins over interpolated hourly rows
        return self._store(df, overwrite=False)

    async def _get_stats(
        self, start: datetime, end: datetime, period: str
    ) -> pd.DataFrame:
        instance = recorder.get_instance(self.hass)
        stats = await instance.async_add_executor_job(
            statistics_during_period,
            self.hass,
            start,
            end,
            {self.entity_id},
            period,
            {"energy": "Wh"},
            {"sum"},
        )
        rows = stats.get(self.entity_id, [])
        if not rows:
            return pd.DataFrame(columns=["power"])

        df = pd.DataFrame(
            {
                "time": [pd.Timestamp(r["start"], tz=UTC, unit="s") for r in rows],
                "power": [r["sum"] for r in rows],
            }
        )
        df["power"] = pd.to_numeric(df["power"], errors="coerce")
        return df.set_index("time")

    def _store(self, df: pd.DataFrame, overwrite: bool = True) -> bool:
        """Normalize a fetched frame and merge it into the store."""
        df["power"] = df["power"].clip(lower=0)
        df.loc[df["power"] < 15, "power"] = 0
        if not overwrite:
            df = df[~df.index.isin(self.data.index)]
        return self._update_data(df)
