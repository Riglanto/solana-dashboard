"""Unit tests for the pure RPC parsing logic (no network)."""

import pytest

from solana_dashboard.collectors.base import CollectorError
from solana_dashboard.collectors.rpc import (
    parse_epoch_info,
    parse_performance_samples,
    parse_vote_accounts,
)


def _sample(slot, txs, slots, secs):
    return {
        "slot": slot,
        "numTransactions": txs,
        "numSlots": slots,
        "samplePeriodSecs": secs,
    }


class TestPerformanceSamples:
    def test_tps_and_slot_time_from_single_sample(self):
        out = parse_performance_samples([_sample(100, 5000, 200, 2.0)])
        assert out["tps"] == pytest.approx(2500.0)
        assert out["avg_slot_time_ms"] == pytest.approx(10.0)
        assert out["tps_avg_5"] == pytest.approx(2500.0)

    def test_window_average_over_multiple_samples(self):
        samples = [
            _sample(200, 4000, 200, 2.0),
            _sample(100, 6000, 200, 2.0),
        ]
        out = parse_performance_samples(samples)
        # latest sample governs single-sample metrics; window averages all.
        assert out["tps"] == pytest.approx(2000.0)
        assert out["tps_avg_5"] == pytest.approx(2500.0)

    def test_empty_samples_raise(self):
        with pytest.raises(CollectorError):
            parse_performance_samples([])

    def test_zero_num_slots_does_not_divzero(self):
        out = parse_performance_samples([_sample(100, 100, 0, 2.0)])
        assert out["tps"] == pytest.approx(50.0)
        assert out["avg_slot_time_ms"] == 0.0


class TestEpochInfo:
    def test_progress_computed(self):
        out = parse_epoch_info(
            {"absoluteSlot": 100_000, "epoch": 800, "slotIndex": 250_000,
             "slotsInEpoch": 500_000}
        )
        assert out["epoch"] == 800
        assert out["current_slot"] == 100_000
        assert out["epoch_progress_pct"] == pytest.approx(50.0)

    def test_zero_slots_in_epoch(self):
        out = parse_epoch_info(
            {"absoluteSlot": 1, "epoch": 1, "slotIndex": 0, "slotsInEpoch": 0}
        )
        assert out["epoch_progress_pct"] == 0.0


class TestVoteAccounts:
    def test_delinquent_stake_percentage(self):
        def acct(stake_lamports, active=True):
            return {
                "activatedStake": stake_lamports,
                "votePubkey": "x",
                "nodePubkey": "y",
            }

        out = parse_vote_accounts(
            {
                "current": [acct(90e9), acct(10e9)],
                "delinquent": [acct(10e9)],
            }
        )
        assert out["active_count"] == 2
        assert out["delinquent_count"] == 1
        assert out["total_stake_sol"] == pytest.approx(110.0)
        assert out["delinquent_stake_pct"] == pytest.approx(100 / 11)
