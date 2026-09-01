"""DeFiLlama collector: Solana TVL, DEX volume (24h), stablecoin supply.

All endpoints are free and CORS-friendly (the dashboard re-uses them
client-side for live refresh between nightly pipeline runs).
"""

from __future__ import annotations

import logging

from solana_dashboard.collectors.base import CollectorError, get_json
from solana_dashboard.core.schema import METRIC_DEFS, Metric, utcnow

logger = logging.getLogger(__name__)

BASE_URL = "https://api.llama.fi"
STABLECOINS_URL = "https://stablecoins.llama.fi"
CHAIN_NAME = "Solana"


def collect() -> list[Metric]:
    now = utcnow()
    source = "defillama"
    metrics: list[Metric] = []

    def add(key: str, value: float) -> None:
        metrics.append(Metric.from_def(METRIC_DEFS[key], value, source, now))

    # --- TVL from /v2/chains (flat list of chain objects) ---
    chains = get_json(f"{BASE_URL}/v2/chains")
    if not isinstance(chains, list):
        raise CollectorError("/v2/chains returned unexpected shape")
    solana = next((c for c in chains if c.get("name") == CHAIN_NAME), None)
    if solana is None:
        raise CollectorError("Solana not found in /v2/chains")
    add("defi.solana_tvl_usd", float(solana["tvl"]))

    # --- DEX volume: sum 24h volume over protocols listing Solana ---
    # /overview/dexs ignores ?chain= on this endpoint version and aggregates
    # across chains, so filter the per-protocol list instead.
    dexs = get_json(f"{BASE_URL}/overview/dexs")
    if not isinstance(dexs, dict):
        raise CollectorError("/overview/dexs returned unexpected shape")
    protocols = dexs.get("protocols", [])
    dex_volume_24h = sum(
        float(p.get("total24h") or 0.0)
        for p in protocols
        if isinstance(p, dict) and CHAIN_NAME in p.get("chains", [])
    )
    add("defi.dex_volume_24h_usd", dex_volume_24h)

    # --- Stablecoin supply: sum peggedUSD on the Solana chain ---
    # Current shape: chainCirculating[chain]["current"]["peggedUSD"];
    # legacy shape was chainBalances[chain]["peggedUSD"].
    stablecoins = get_json(
        f"{STABLECOINS_URL}/stablecoins", params={"includePrices": "true"}
    )
    assets = stablecoins.get("peggedAssets", []) if isinstance(stablecoins, dict) else []
    supply = 0.0
    for asset in assets:
        circulating = asset.get("chainCirculating", {})
        chain = circulating.get(CHAIN_NAME) if isinstance(circulating, dict) else None
        if chain:
            supply += float(chain.get("current", {}).get("peggedUSD") or 0.0)
            continue
        balances = asset.get("chainBalances", {})
        supply += float(balances.get(CHAIN_NAME, {}).get("peggedUSD") or 0.0)
    add("defi.stablecoin_supply_usd", supply)

    return metrics
