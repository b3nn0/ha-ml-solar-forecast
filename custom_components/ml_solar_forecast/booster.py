"""Module for training and predicting with a gradient boosting model.

This module provides the Booster class, which handles:
- Training a gradient boosting model on historical production data
- Persisting and reloading the trained model on disk
- Making predictions with the trained model

It uses hessboost, a Rust-based gradient boosting library with an
XGBoost-compatible API. Unlike LightGBM, hessboost publishes musllinux
(musl/Alpine) wheels, so it can run in-process on Alpine-based Home
Assistant without an external machine-learner addon.
"""

from pathlib import Path

import hessboost
import pandas as pd

from homeassistant.core import HomeAssistant

from .const import log

# XGBoost-style training parameters used by hessboost.
TRAIN_PARAMS: dict = {
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "max_depth": 6,
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
}
NUM_BOOST_ROUND: int = 300


class Booster:
    """Backend-neutral wrapper around a gradient boosting library."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        storage_dir: str,
        target_column: str = "power",
    ) -> None:
        """Init with hass, a model name, a storage directory and the target column."""
        self.hass = hass
        self.name = name
        self.target_column = target_column
        self.model_path = Path(storage_dir) / f"{name}.bin"
        self._booster: hessboost.Booster | None = None

    async def train(self, df: pd.DataFrame) -> None:
        """Train a model on the given dataframe and persist it to disk."""
        booster = await self.hass.async_add_executor_job(self._train_sync, df)
        log.debug(f"trained model {self.name} ({booster.num_boosted_rounds()} rounds)")

    async def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Use the trained model to predict values for the target column."""
        return await self.hass.async_add_executor_job(self._predict_sync, df)

    async def is_trained(self) -> bool:
        """Check if there is currently a trained model for this learner."""
        return await self.hass.async_add_executor_job(self._get_booster) is not None

    def _get_booster(self) -> hessboost.Booster | None:
        """Return the in-memory booster, lazily loading it from disk."""
        if self._booster is None and self.model_path.is_file():
            try:
                self._booster = hessboost.Booster(str(self.model_path))
                log.debug(f"loaded model {self.name} from {self.model_path}")
            except hessboost.ModelFormatError:
                log.warning(f"model file for {self.name} is corrupt, ignoring it")
        return self._booster

    def _train_sync(self, df: pd.DataFrame) -> hessboost.Booster:
        """Blocking training routine, run in a worker thread."""
        dtrain = hessboost.DMatrix(df, label=self.target_column)
        booster = hessboost.train(
            TRAIN_PARAMS, dtrain, NUM_BOOST_ROUND, verbose_eval=False
        )
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        booster.save_model(str(self.model_path))
        self._booster = booster
        return booster

    def _predict_sync(self, df: pd.DataFrame) -> pd.DataFrame:
        """Blocking prediction routine, run in a worker thread."""
        booster = self._get_booster()
        if booster is None:
            raise RuntimeError(f"model {self.name} is not trained yet")

        if self.target_column in df.columns:
            df = df.drop(columns=[self.target_column])

        prediction = pd.DataFrame(index=df.index)
        prediction[self.target_column] = booster.predict(df)
        return prediction
