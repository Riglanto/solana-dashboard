"""Upgrade tracker: SIMD-0525 (Reduce Slot Times) + Alpenglow (consensus).

State collector — returns BOTH numeric metrics (alpenglow stars) and string
state entries (statuses/titles/dates). State lives in the `state` table and
the snapshot's `state` key: categorical data doesn't fit the float metric
model, and its history lets the report notice status changes (e.g. a SIMD
moving from Draft → Accepted).

Sources (free, no key, unauthenticated GitHub API — 60 req/hr is ample at
one cycle per day):
  - solana-foundation/solana-improvement-documents → proposals/SIMD-0525.md
  - anza-xyz/alpenglow repo metadata
"""

from __future__ import annotations

import base64
import logging

from solana_dashboard.collectors.base import CollectorError, get_json
from solana_dashboard.core.schema import METRIC_DEFS, Metric, utcnow

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
SIMD_0525_URL = (
    f"{GITHUB_API}/repos/solana-foundation/solana-improvement-documents/"
    "contents/proposals/0525-reduce-slot-times.md"
)
ALPENGLOW_REPO_URL = f"{GITHUB_API}/repos/anza-xyz/alpenglow"


def parse_frontmatter(text: str) -> dict[str, str]:
    """Crude YAML-frontmatter parse — enough for status/title/created."""
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1] if len(text.split("---", 2)) > 1 else ""
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip().strip("'\"")
    return out


def fetch_simd_0525() -> dict[str, str]:
    """State entries describing SIMD-0525 from its frontmatter."""
    try:
        data = get_json(SIMD_0525_URL, retries=2)
        content = base64.b64decode(data["content"]).decode()
        fm = parse_frontmatter(content)
    except Exception as exc:  # noqa: BLE001 — degrade, never fail the cycle
        logger.warning("SIMD-0525 fetch failed: %s", exc)
        return {
            "upgrade.simd_0525_status": "unavailable",
            "upgrade.simd_0525_source": "github.com/solana-foundation/solana-improvement-documents",
        }

    return {
        "upgrade.simd_0525": f"SIMD-0525 {fm.get('title', 'Reduce Slot Times')}",
        "upgrade.simd_0525_status": fm.get("status", "unknown"),
        "upgrade.simd_0525_created": fm.get("created", ""),
        "upgrade.simd_0525_source": "github.com/solana-foundation/solana-improvement-documents",
    }


def fetch_alpenglow() -> tuple[dict[str, str], list[Metric]]:
    """Alpenglow repo metadata → state entries + stars metric."""
    now = utcnow()
    source = "github.com/anza-xyz/alpenglow"

    repo = get_json(ALPENGLOW_REPO_URL, retries=2)
    stars = repo.get("stargazers_count")
    pushed = (repo.get("pushed_at") or "")[:10]  # YYYY-MM-DD

    state = {
        "upgrade.alpenglow": "Active development (open source)",
        "upgrade.alpenglow_last_push": pushed or "unknown",
        "upgrade.alpenglow_source": source,
    }
    metrics: list[Metric] = []
    if stars is not None:
        metrics.append(
            Metric.from_def(METRIC_DEFS["upgrade.alpenglow_stars"], float(stars), source, now)
        )
    return state, metrics


def collect() -> tuple[list[Metric], dict[str, str]]:
    """Collector interface: (metrics, state)."""
    metrics: list[Metric] = []
    state: dict[str, str] = {}

    simd_state = fetch_simd_0525()
    state.update(simd_state)

    try:
        alpen_state, alpen_metrics = fetch_alpenglow()
        state.update(alpen_state)
        metrics.extend(alpen_metrics)
    except CollectorError as exc:
        logger.warning("alpenglow fetch failed: %s", exc)
        state["upgrade.alpenglow"] = "status unavailable"

    return metrics, state
