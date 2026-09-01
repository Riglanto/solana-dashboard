"""Unit tests for the Dune adapter (mocked HTTP, no network)."""

import pytest

from solana_dashboard.collectors import dune
from solana_dashboard.collectors.base import CollectorError


def _completed(rows):
    return {
        "state": "QUERY_STATE_COMPLETED",
        "is_execution_success": True,
        "result": {"rows": rows},
    }


class TestConfig:
    def test_no_key_disables_adapter(self, monkeypatch):
        monkeypatch.delenv(dune.ENV_KEY, raising=False)
        assert dune.collect() == []

    def test_key_without_queries_raises(self, monkeypatch):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.delenv(dune.ENV_QUERIES, raising=False)
        with pytest.raises(CollectorError, match="DUNE_QUERIES"):
            dune._config()

    def test_malformed_queries_json_raises(self, monkeypatch):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, "{not json")
        with pytest.raises(CollectorError, match="not valid JSON"):
            dune._config()


class TestCollect:
    def test_maps_query_rows_to_metrics(self, monkeypatch):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, '{"dune.active_wallets_24h": {"query_id": 1, "column": "active_wallets"}}')
        monkeypatch.setattr(
            dune, "get_json", lambda *a, **k: _completed([{"active_wallets": 412345}])
        )
        out = dune.collect()
        assert len(out) == 1
        assert out[0].key == "dune.active_wallets_24h"
        assert out[0].value == 412345
        assert out[0].source == "dune"

    def test_unknown_metric_key_is_skipped(self, monkeypatch, caplog):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, '{"dune.nope": {"query_id": 1}}')
        monkeypatch.setattr(
            dune, "get_json", lambda *a, **k: _completed([{"x": 1}])
        )
        assert dune.collect() == []
        assert "unknown metric key" in caplog.text

    def test_executes_and_retries_when_no_cached_result(self, monkeypatch):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, '{"dune.fee_revenue_24h_usd": {"query_id": 7, "column": "fees"}}')
        calls = {"n": 0}

        def fake_get(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"state": "QUERY_STATE_EXECUTING"}  # nothing cached
            return _completed([{"fees": 1234.5}])

        monkeypatch.setattr(dune, "get_json", fake_get)
        monkeypatch.setattr(
            dune, "post_json", lambda *a, **k: {"execution_id": "e1"}
        )
        out = dune.collect()
        assert len(out) == 1
        assert out[0].key == "dune.fee_revenue_24h_usd"
        assert out[0].value == pytest.approx(1234.5)

    def test_still_executing_surfaces_transient_error(self, monkeypatch, caplog):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, '{"dune.fee_revenue_24h_usd": {"query_id": 7}}')
        monkeypatch.setattr(
            dune, "get_json",
            lambda *a, **k: {"state": "QUERY_STATE_EXECUTING"},
        )
        monkeypatch.setattr(
            dune, "post_json", lambda *a, **k: {"execution_id": "e1"}
        )
        assert dune.collect() == []  # cycle survives; failure is logged
        assert "no completed execution" in caplog.text

    def test_missing_column_is_skipped(self, monkeypatch, caplog):
        monkeypatch.setenv(dune.ENV_KEY, "k")
        monkeypatch.setenv(dune.ENV_QUERIES, '{"dune.active_wallets_24h": {"query_id": 1, "column": "nope"}}')
        monkeypatch.setattr(
            dune, "get_json", lambda *a, **k: _completed([{"active_wallets": 1}])
        )
        assert dune.collect() == []
        assert "column" in caplog.text
