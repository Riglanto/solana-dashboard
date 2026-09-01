"""Dune Analytics collector — on-chain activity (optional, config-gated).

Active wallets and fee revenue are Solana on-chain metrics that neither
DeFiLlama nor CoinGecko expose. The Dune API fills that gap, but it
needs an API key (free community tier) and user-owned/public queries,
so this adapter ships disabled:

  - `DUNE_API_KEY`  — from dune.com/settings/api (free tier)
  - `DUNE_QUERIES`  — JSON map of metric key → {query_id, column}

Example:
  DUNE_QUERIES='{"dune.active_wallets_24h":
                  {"query_id": 123456, "column": "active_wallets"}}'

Without a key the collector quietly contributes nothing: the metrics
stay "unavailable" in the report, the cycle is unaffected, and nothing
in the brief's required set depends on Dune. With a key, a query that
has no cached execution gets kicked off once (executions are
rate-limited, cached results are free) and re-read; a query that is
still executing surfaces as a transient error and retries next cycle.
"""

from __future__ import annotations

import json
import logging
import os

from solana_dashboard.collectors.base import CollectorError, get_json, post_json
from solana_dashboard.core.schema import METRIC_DEFS, Metric, utcnow

logger = logging.getLogger(__name__)

API_BASE = "https://api.dune.com/api/v1"
ENV_KEY = "DUNE_API_KEY"
ENV_QUERIES = "DUNE_QUERIES"

COMPLETED = "QUERY_STATE_COMPLETED"


def _config() -> dict | None:
    """Read env config; None means "adapter disabled" (not an error)."""
    key = os.environ.get(ENV_KEY)
    if not key:
        logger.info("DUNE_API_KEY not set — Dune adapter inactive")
        return None
    raw = os.environ.get(ENV_QUERIES)
    if not raw:
        raise CollectorError(
            f"{ENV_QUERIES} not set (JSON map of metric key → {{query_id, column}})"
        )
    try:
        queries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CollectorError(f"{ENV_QUERIES} is not valid JSON: {exc}") from exc
    return {"key": key, "queries": queries}


def _query_rows(key: str, query_id: int) -> list[dict]:
    """Result rows for one query; kicks off an execution if none is cached."""
    headers = {"X-Dune-API-Key": key}
    url = f"{API_BASE}/query/{query_id}/results"

    def rows_from(data: dict | list) -> list[dict] | None:
        if isinstance(data, dict) and data.get("state") == COMPLETED \
                and data.get("is_execution_success"):
            return data.get("result", {}).get("rows", [])
        return None

    rows = rows_from(get_json(url, headers=headers, retries=2))
    if rows is not None:
        return rows
    # No completed execution cached: start one, then re-read once.
    post_json(f"{API_BASE}/query/{query_id}/execute", headers=headers, retries=1)
    rows = rows_from(get_json(url, headers=headers, retries=2))
    if rows is not None:
        return rows
    raise CollectorError(
        f"dune: query {query_id} has no completed execution", transient=True
    )


def collect() -> list[Metric]:
    cfg = _config()
    if cfg is None:
        return []
    now = utcnow()
    source = "dune"
    metrics: list[Metric] = []
    for key, spec in cfg["queries"].items():
        defn = METRIC_DEFS.get(key)
        if defn is None:
            logger.warning("dune: unknown metric key %r — add it to METRIC_DEFS", key)
            continue
        try:
            rows = _query_rows(cfg["key"], spec["query_id"])
        except CollectorError as exc:
            logger.warning("dune: %s → %s", key, exc)
            continue
        value = rows[0].get(spec.get("column", "value")) if rows else None
        if value is None:
            logger.warning(
                "dune: column %r missing from query %s", spec.get("column"), key
            )
            continue
        metrics.append(Metric.from_def(defn, float(value), source, now))
    return metrics
