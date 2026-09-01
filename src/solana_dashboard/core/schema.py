"""Normalized metric schema — the single source of truth.

Every metric the dashboard/report can display is declared here with its
definition and unit. Collectors emit values against this registry, so numbers
always carry provenance (which source, collected when) and a documented
definition — the standardization gap the Solana Foundation's Open Data
Platform was built to solve.

Display and change semantics (precision, integer counts, brief-compliance
requiredness) also live here, so renderers derive formatting from the
registry instead of hardcoding key lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MetricDef:
    """Registry entry describing one metric."""

    key: str
    label: str
    category: str  # Network | Validators | Market | DeFi | Upgrades
    definition: str
    unit: str | None = None
    order: int = 0       # display order within category
    precision: int = 2   # decimals used by tile/table formatting
    integer: bool = False  # count metric: changes of >= 1 are meaningful
    required: bool = False  # missing → cycle fails (brief compliance gate)


@dataclass(frozen=True)
class Metric:
    """A collected measurement. Metadata lives in the registry, not here."""

    key: str
    value: float
    source: str
    collected_at: datetime

    @classmethod
    def from_def(
        cls,
        defn: MetricDef,
        value: float,
        source: str,
        collected_at: datetime,
    ) -> "Metric":
        return cls(
            key=defn.key,
            value=value,
            source=source,
            collected_at=collected_at,
        )

    def to_dict(self) -> dict:
        """Serialize with registry lineage so the JSON stays self-describing."""
        d = METRIC_DEFS.get(self.key)
        return {
            "key": self.key,
            "value": self.value,
            "unit": d.unit if d else None,
            "source": self.source,
            "collected_at": self.collected_at.isoformat(),
            "label": d.label if d else self.key,
            "category": d.category if d else "",
            "definition": d.definition if d else "",
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def _def(
    key: str,
    label: str,
    category: str,
    definition: str,
    unit: str | None = None,
    order: int = 0,
    precision: int = 2,
    integer: bool = False,
    required: bool = False,
) -> MetricDef:
    return MetricDef(
        key=key,
        label=label,
        category=category,
        definition=definition,
        unit=unit,
        order=order,
        precision=precision,
        integer=integer,
        required=required,
    )


METRIC_DEFS: dict[str, MetricDef] = {
    # --- Network ---
    "network.current_slot": _def(
        "network.current_slot", "Current slot", "Network",
        "Latest confirmed slot from getSlot (RPC).", order=0,
        integer=True, required=True,
    ),
    "network.epoch": _def(
        "network.epoch", "Epoch", "Network",
        "Current epoch number from getEpochInfo.", order=1,
        integer=True, required=True,
    ),
    "network.epoch_progress_pct": _def(
        "network.epoch_progress_pct", "Epoch progress", "Network",
        "slotIndex / slotsInEpoch * 100 from getEpochInfo.", "%", order=2,
        required=True,
    ),
    "network.tps": _def(
        "network.tps", "TPS (latest)", "Network",
        "numTransactions / samplePeriodSecs of the most recent "
        "getRecentPerformanceSamples entry.", order=3,
        precision=1, required=True,
    ),
    "network.tps_avg_5": _def(
        "network.tps_avg_5", "TPS (5-sample avg)", "Network",
        "Sum of numTransactions over sum of samplePeriodSecs across the last "
        "5 performance samples.", order=4, precision=1,
    ),
    "network.avg_slot_time_ms": _def(
        "network.avg_slot_time_ms", "Avg slot time", "Network",
        "samplePeriodSecs / numSlots * 1000 from the most recent performance "
        "sample.", "ms", order=5,
    ),
    # --- Validators ---
    "validators.active_count": _def(
        "validators.active_count", "Active validators", "Validators",
        "Count of active vote accounts from getVoteAccounts.", order=0,
        integer=True, required=True,
    ),
    "validators.delinquent_count": _def(
        "validators.delinquent_count", "Delinquent validators", "Validators",
        "Count of delinquent vote accounts from getVoteAccounts.", order=1,
        integer=True, required=True,
    ),
    "validators.total_stake_sol": _def(
        "validators.total_stake_sol", "Total stake", "Validators",
        "Sum of stake (active + delinquent) in SOL from getVoteAccounts.",
        "SOL", order=2,
    ),
    "validators.delinquent_stake_pct": _def(
        "validators.delinquent_stake_pct", "Delinquent stake", "Validators",
        "Delinquent stake / total stake * 100.", "%", order=3,
        required=True,
    ),
    # --- Market ---
    "market.sol_price_usd": _def(
        "market.sol_price_usd", "SOL price", "Market",
        "USD spot price from CoinGecko simple/price.", "USD", order=0,
        required=True,
    ),
    # --- DeFi ---
    "defi.solana_tvl_usd": _def(
        "defi.solana_tvl_usd", "Solana TVL", "DeFi",
        "Total value locked on Solana from DefiLlama /v2/chains.", "USD",
        order=0, required=True,
    ),
    "defi.dex_volume_24h_usd": _def(
        "defi.dex_volume_24h_usd", "DEX volume (24h)", "DeFi",
        "Sum of totalVolume24h across Solana DEXes from DefiLlama "
        "/overview/dexs.", "USD", order=1, required=True,
    ),
    "defi.stablecoin_supply_usd": _def(
        "defi.stablecoin_supply_usd", "Stablecoin supply", "DeFi",
        "Sum of peggedUSD balances on Solana from DefiLlama stablecoins.",
        "USD", order=2, required=True,
    ),
    # --- On-chain (Dune Analytics, optional, config-gated) ---
    "dune.active_wallets_24h": _def(
        "dune.active_wallets_24h", "Active wallets (24h)", "On-chain",
        "Distinct wallet addresses active on Solana in the last 24h, from a "
        "Dune Analytics query. Requires DUNE_API_KEY + DUNE_QUERIES; "
        "unavailable while unconfigured.", order=0, integer=True,
    ),
    "dune.fee_revenue_24h_usd": _def(
        "dune.fee_revenue_24h_usd", "Fee revenue (24h)", "On-chain",
        "Total user fees paid on Solana in the last 24h in USD, from a Dune "
        "Analytics query. Requires DUNE_API_KEY + DUNE_QUERIES; unavailable "
        "while unconfigured.", "USD", order=1,
    ),
    # --- Upgrades ---
    "upgrade.alpenglow_stars": _def(
        "upgrade.alpenglow_stars", "Alpenglow repo stars", "Upgrades",
        "Stargazer count of github.com/anza-xyz/alpenglow — a proxy for "
        "interest in the Alpenglow consensus initiative.", order=0,
        integer=True,
    ),
}

CATEGORY_ORDER = ["Network", "Validators", "Market", "DeFi", "On-chain", "Upgrades"]

# State entries (string/categorical) worth displaying, in display order.
STATE_DEFS: list[tuple[str, str]] = [
    ("upgrade.simd_0525", "SIMD-0525"),
    ("upgrade.simd_0525_status", "SIMD-0525 status"),
    ("upgrade.simd_0525_created", "SIMD-0525 created"),
    ("upgrade.alpenglow", "Alpenglow (consensus)"),
    ("upgrade.alpenglow_last_push", "Alpenglow last push"),
]


def defs_for_category(category: str) -> list[MetricDef]:
    """Registry entries for one category, in display order."""
    return sorted(
        (d for d in METRIC_DEFS.values() if d.category == category),
        key=lambda d: d.order,
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
