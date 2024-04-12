import time
from decimal import Decimal
from typing import List, Optional

import pandas_ta as ta  # noqa: F401
from pydantic import Field, validator

from hummingbot.client.config.config_data_types import ClientFieldData
from hummingbot.core.data_type.common import PriceType, TradeType
from hummingbot.data_feed.candles_feed.candles_factory import CandlesConfig
from hummingbot.smart_components.controllers.market_making_controller_base import (
    MarketMakingControllerBase,
    MarketMakingControllerConfigBase,
)
from hummingbot.smart_components.executors.dca_executor.data_types import DCAExecutorConfig
from hummingbot.smart_components.order_level_distributions.distributions import Distributions


class PMMMagaibaControllerConfig(MarketMakingControllerConfigBase):
    controller_name = "pmm_magaiba"
    candles_config: List[CandlesConfig] = []
    buy_spreads: List[float] = Field(
        default="1,2,4",
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter a comma-separated list of buy spreads (e.g., '0.01, 0.02'):"))
    sell_spreads: List[float] = Field(
        default="1,2,4",
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter a comma-separated list of sell spreads (e.g., '0.01, 0.02'):"))
    candles_connector: str = Field(
        default=None,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the connector for the candles data, leave empty to use the same exchange as the connector: ", )
    )
    candles_trading_pair: str = Field(
        default=None,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the trading pair for the candles data, leave empty to use the same trading pair as the connector: ", )
    )
    interval: str = Field(
        default="3m",
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the candle interval (e.g., 1m, 5m, 1h, 1d): ",
            prompt_on_new=False))

    macd_fast: int = Field(
        default=12,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the MACD fast length: ",
            prompt_on_new=True))
    macd_slow: int = Field(
        default=26,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the MACD slow length: ",
            prompt_on_new=True))
    macd_signal: int = Field(
        default=9,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the MACD signal length: ",
            prompt_on_new=True))
    natr_length: int = Field(
        default=14,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the NATR length: ",
            prompt_on_new=True))
    dca_levels: int = Field(
        default=5,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the number of DCA levels: ",
            prompt_on_new=True))
    dca_spread_scalar: Decimal = Field(
        default=2,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the DCA spread scalar: ",
            prompt_on_new=True))
    dca_amount_ratio_increment: float = Field(
        default=1.5,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the DCA amount ratio increment: ",
            prompt_on_new=True))
    executor_activation_bounds: Optional[List[Decimal]] = Field(
        default=None,
        client_data=ClientFieldData(
            is_updatable=True,
            prompt=lambda mi: "Enter the activation bounds for the orders "
                              "(e.g., 0.01 activates the next order when the price is closer than 1%): ",
            prompt_on_new=False))

    @validator("executor_activation_bounds", pre=True, always=True)
    def parse_activation_bounds(cls, v):
        if isinstance(v, list):
            return [Decimal(val) for val in v]
        elif isinstance(v, str):
            if v == "":
                return None
            return [Decimal(val) for val in v.split(",")]
        return v

    @validator("candles_connector", pre=True, always=True)
    def set_candles_connector(cls, v, values):
        if v is None or v == "":
            return values.get("connector_name")
        return v

    @validator("candles_trading_pair", pre=True, always=True)
    def set_candles_trading_pair(cls, v, values):
        if v is None or v == "":
            return values.get("trading_pair")
        return v


class PMMMagaibaController(MarketMakingControllerBase):
    """
    This is a dynamic version of the PMM controller.It uses the MACD to shift the mid-price and the NATR
    to make the spreads dynamic. It also uses the Triple Barrier Strategy to manage the risk.
    """
    def __init__(self, config: PMMMagaibaControllerConfig, *args, **kwargs):
        self.config = config
        self.max_records = max(config.macd_slow, config.macd_fast, config.macd_signal, config.natr_length) + 10
        amounts_distributed = Distributions.geometric(n_levels=self.config.dca_levels, start=1.0,
                                                      ratio=self.config.dca_amount_ratio_increment)
        self.dca_amounts_pct = [amount / sum(amounts_distributed) for amount in amounts_distributed]
        if len(self.config.candles_config) == 0:
            self.config.candles_config = [CandlesConfig(
                connector=config.candles_connector,
                trading_pair=config.candles_trading_pair,
                interval=config.interval,
                max_records=self.max_records
            )]
        super().__init__(config, *args, **kwargs)

    async def update_processed_data(self):
        candles = self.market_data_provider.get_candles_df(connector_name=self.config.candles_connector,
                                                           trading_pair=self.config.candles_trading_pair,
                                                           interval=self.config.interval,
                                                           max_records=self.max_records)
        natr = ta.natr(candles["high"], candles["low"], candles["close"], length=self.config.natr_length) / 100
        macd_output = ta.macd(candles["close"], fast=self.config.macd_fast, slow=self.config.macd_slow, signal=self.config.macd_signal)
        macd = macd_output[f"MACD_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"]
        macd_signal = - (macd - macd.mean()) / macd.std()
        macdh = macd_output[f"MACDh_{self.config.macd_fast}_{self.config.macd_slow}_{self.config.macd_signal}"]
        macdh_signal = macdh.apply(lambda x: 1 if x > 0 else -1)
        max_price_shift = natr / 2
        price_multiplier = Decimal(((0.5 * macd_signal + 0.5 * macdh_signal) * max_price_shift).iloc[-1])
        spread_multiplier = Decimal(natr.iloc[-1])
        mid_price = self.market_data_provider.get_price_by_type(self.config.connector_name, self.config.trading_pair,
                                                                PriceType.MidPrice)
        reference_price = mid_price * (1 + price_multiplier)
        self.processed_data = {"reference_price": reference_price, "spread_multiplier": spread_multiplier}

    def get_executor_config(self, level_id: str, price: Decimal, amount: Decimal):
        trade_type = self.get_trade_type_from_level_id(level_id)
        spread_multiplier = self.processed_data["spread_multiplier"]

        if trade_type == TradeType.BUY:
            prices = [price * (1 - n * self.config.dca_spread_scalar * spread_multiplier) for n in range(self.config.dca_levels)]
        else:
            prices = [price * (1 + n * self.config.dca_spread_scalar * spread_multiplier) for n in range(self.config.dca_levels)]
        amounts_quote = [amount * pct * price for pct, price in zip(self.dca_amounts_pct, prices)]
        return DCAExecutorConfig(
            timestamp=time.time(),
            level_id=level_id,
            connector_name=self.config.connector_name,
            trading_pair=self.config.trading_pair,
            prices=prices,
            amounts_quote=amounts_quote,
            leverage=self.config.leverage,
            side=trade_type,
            time_limit=self.config.time_limit,
            stop_loss=self.config.stop_loss,
            trailing_stop=self.config.trailing_stop,
            activation_bounds=self.config.executor_activation_bounds,
        )