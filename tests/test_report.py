"""Unit tests for the snapshot diff / changelog logic."""

from solana_dashboard.render.report import (
    Change,
    _delta_text,
    diff_metrics,
    diff_state,
)


def m(value, key="network.tps"):
    return {key: {"value": value}}


class TestDeltaText:
    def test_first_measurement_uses_note(self):
        c = Change("upgrade.alpenglow_stars", "Alpenglow repo stars",
                   None, 144.0, None, "first measurement")
        assert _delta_text(c) == "first measurement"

    def test_integer_key_absolute_delta(self):
        c = Change("network.current_slot", "Current slot",
                   441305301.0, 441306324.0, 0.0002)
        assert _delta_text(c) == "+1,023"

    def test_pct_key_uses_pp_note(self):
        c = Change("validators.delinquent_stake_pct", "Delinquent stake",
                   0.04, 0.12, 200.0, "+0.08 pp")
        assert _delta_text(c) == "+0.08 pp"

    def test_plain_metric_uses_pct(self):
        c = Change("network.tps", "TPS", 3000.0, 3200.0, 6.67)
        assert _delta_text(c) == "+6.7%"


class TestDiffMetrics:
    def test_large_move_captured(self):
        changes = diff_metrics(m(3000.0), m(3200.0))
        assert len(changes) == 1
        assert changes[0].delta_pct == 6.666666666666667

    def test_small_move_ignored(self):
        assert diff_metrics(m(3000.0), m(3010.0)) == []

    def test_new_metric_flagged(self):
        changes = diff_metrics({}, m(100.0))
        assert changes[0].note == "first measurement"

    def test_epoch_advance_noted(self):
        changes = diff_metrics(
            {"network.epoch": {"value": 1020.0}},
            {"network.epoch": {"value": 1021.0}},
        )
        assert len(changes) == 1
        assert "epoch advanced to 1,021" in changes[0].note

    def test_percentage_point_metric_uses_pp_threshold(self):
        changes = diff_metrics(
            {"validators.delinquent_stake_pct": {"value": 0.04}},
            {"validators.delinquent_stake_pct": {"value": 0.12}},
        )
        assert len(changes) == 1
        assert "+0.08 pp" in changes[0].note

    def test_percentage_point_small_change_ignored(self):
        changes = diff_metrics(
            {"validators.delinquent_stake_pct": {"value": 0.04}},
            {"validators.delinquent_stake_pct": {"value": 0.06}},
        )
        assert changes == []

    def test_count_metric_any_single_change(self):
        changes = diff_metrics(
            {"validators.delinquent_count": {"value": 10}},
            {"validators.delinquent_count": {"value": 11}},
        )
        assert len(changes) == 1
        assert changes[0].delta_pct == 10.0

    def test_unchanged_metrics_not_reported(self):
        assert diff_metrics(m(100.0), m(100.0)) == []


class TestDiffState:
    def test_status_change_reported(self):
        lines = diff_state(
            {"upgrade.simd_0525_status": "Draft"},
            {"upgrade.simd_0525_status": "Accepted"},
        )
        assert len(lines) == 1
        assert "Draft" in lines[0] and "Accepted" in lines[0]

    def test_unchanged_state_silent(self):
        assert diff_state({"a": "x"}, {"a": "x"}) == []
