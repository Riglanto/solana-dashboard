"""Solana mainnet RPC collector (getSlot, getEpochInfo, getVoteAccounts,
getRecentPerformanceSamples). Uses the free public endpoint — no key needed.

Parsing is split into pure functions (unit-testable) separate from HTTP.
"""

from __future__ import annotations

import logging

from solana_dashboard.collectors.base import CollectorError, post_json_rpc
from solana_dashboard.core.schema import METRIC_DEFS, Metric, utcnow

logger = logging.getLogger(__name__)

PUBLIC_RPC_URL = "https://api.mainnet-beta.solana.com"

PERF_SAMPLES = 5  # window used for the averaged TPS metric


# ---------------------------------------------------------------------------
# Pure parsing helpers
# ---------------------------------------------------------------------------

def parse_performance_samples(samples: list[dict]) -> dict[str, float]:
    """Compute TPS and slot-time metrics from getRecentPerformanceSamples.

    Samples are ~2s windows; each has slot, numTransactions, numSlots,
    samplePeriodSecs. Returns {tps, tps_avg_5, avg_slot_time_ms}.
    """
    if not samples:
        raise CollectorError("getRecentPerformanceSamples returned no samples")

    latest = samples[0]
    tps = latest["numTransactions"] / latest["samplePeriodSecs"]

    window_txs = sum(s["numTransactions"] for s in samples)
    window_secs = sum(s["samplePeriodSecs"] for s in samples)
    tps_avg_5 = window_txs / window_secs if window_secs else 0.0

    num_slots = latest.get("numSlots") or 0
    avg_slot_time_ms = (
        latest["samplePeriodSecs"] / num_slots * 1000 if num_slots else 0.0
    )

    return {
        "tps": tps,
        "tps_avg_5": tps_avg_5,
        "avg_slot_time_ms": avg_slot_time_ms,
    }


def parse_epoch_info(epoch_info: dict) -> dict[str, float]:
    """Extract epoch, progress % from getEpochInfo."""
    slot_index = epoch_info["slotIndex"]
    slots_in_epoch = epoch_info["slotsInEpoch"]
    progress = slot_index / slots_in_epoch * 100 if slots_in_epoch else 0.0
    return {
        "epoch": epoch_info["epoch"],
        "current_slot": epoch_info["absoluteSlot"],
        "epoch_progress_pct": progress,
    }


def parse_vote_accounts(vote_accounts: dict) -> dict[str, float]:
    """Extract validator health metrics from getVoteAccounts."""
    active = vote_accounts.get("current", [])
    delinquent = vote_accounts.get("delinquent", [])

    active_stake = sum(v["activatedStake"] / 1e9 for v in active)
    delinquent_stake = sum(v["activatedStake"] / 1e9 for v in delinquent)
    total_stake = active_stake + delinquent_stake

    delinquent_pct = (
        delinquent_stake / total_stake * 100 if total_stake else 0.0
    )

    return {
        "active_count": len(active),
        "delinquent_count": len(delinquent),
        "total_stake_sol": total_stake,
        "delinquent_stake_pct": delinquent_pct,
    }


# ---------------------------------------------------------------------------
# HTTP collection
# ---------------------------------------------------------------------------

def collect(rpc_url: str = PUBLIC_RPC_URL) -> list[Metric]:
    """Run one collection cycle against the Solana RPC endpoint."""
    now = utcnow()
    metrics: list[Metric] = []
    source = f"solana-rpc({rpc_url})"

    def add(key: str, value: float) -> None:
        metrics.append(Metric.from_def(METRIC_DEFS[key], value, source, now))

    perf = post_json_rpc(rpc_url, "getRecentPerformanceSamples", [PERF_SAMPLES])
    for key, value in parse_performance_samples(perf).items():
        add(f"network.{key}", value)

    epoch = post_json_rpc(rpc_url, "getEpochInfo")
    for key, value in parse_epoch_info(epoch).items():
        add(f"network.{key}", value)

    votes = post_json_rpc(rpc_url, "getVoteAccounts")
    for key, value in parse_vote_accounts(votes).items():
        add(f"validators.{key}", value)

    return metrics
