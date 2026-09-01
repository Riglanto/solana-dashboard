"""CoinGecko collector: SOL spot price (USD)."""

from __future__ import annotations

import logging

from solana_dashboard.collectors.base import CollectorError, get_json
from solana_dashboard.core.schema import METRIC_DEFS, Metric, utcnow

logger = logging.getLogger(__name__)

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def collect() -> list[Metric]:
    now = utcnow()
    source = "coingecko"

    data = get_json(
        PRICE_URL,
        params={"ids": "solana", "vs_currencies": "usd"},
        headers={"Accept": "application/json"},
    )
    if not isinstance(data, dict):
        raise CollectorError("simple/price returned unexpected shape")
    solana = data.get("solana", {})
    price = solana.get("usd")
    if price is None:
        raise CollectorError(f"solana/usd missing from response: {data}")

    return [
        Metric.from_def(
            METRIC_DEFS["market.sol_price_usd"], float(price), source, now
        )
    ]
