"""Module for interacting with the LightGBM machine learning addon.

This module provides functionality to:
- Train LightGBM models via the addon API
- Check if a model is trained
- Make predictions using trained models
"""

import aiohttp
import pandas as pd

from .const import log


class LGBM:
    """Class to interact with machine-learner addon.

    Hopefully obsolete once this is merged: https://github.com/home-assistant/wheels-custom-integrations/pull/748.
    """

    HOSTNAME: str = "http://localhost:14760"
    # HOSTNAME: str = "http://hass:14760"

    modelname: str = ""

    def __init__(self, modelname: str) -> None:
        """Init with a given name."""
        self.modelname = modelname

    async def train(self, df: pd.DataFrame, target_column: str):
        """Trains a model."""
        data = {
            "model_name": self.modelname,
            "target_column": target_column,
            "dataframe": df.to_csv(index=False),
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(f"{self.HOSTNAME}/train", json=data) as response,
        ):
            content = await response.json()
            log.debug(f"trained model {self.modelname}. Response: {content}")

    async def is_trained(self) -> bool:
        """Check if there is currently a trained model for this learner."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{self.HOSTNAME}/is_trained?model_name={self.modelname}"
            ) as response,
        ):
            data = await response.json()
            log.debug(f"is_trained: {data}")
            return data["is_trained"]

    async def predict(self, df: pd.DataFrame, target_column: str) -> pd.DataFrame:
        """Use the trained model to predict values."""
        async with aiohttp.ClientSession() as session:
            data = {"model_name": self.modelname, "dataframe": df.to_csv(index=False)}
            async with session.post(f"{self.HOSTNAME}/predict", json=data) as response:
                result = await response.json()
                prediction = pd.DataFrame(index=df.index)
                prediction[target_column] = result["predictions"]
                return prediction
