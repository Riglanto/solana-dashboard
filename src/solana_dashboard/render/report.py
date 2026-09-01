"""Markdown report renderer with auto-generated changelog.

The report is the "auto-updating report" half of the brief: each nightly
cycle regenerates it, and the *What changed* section is computed by diffing
the latest two snapshots — the report narrates its own evolution (epoch
transitions, metric moves, SIMD status changes).

Every metric row carries its definition + source: definitions and lineage
are the differentiator against one-off dashboards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from solana_dashboard.core.schema import (
    CATEGORY_ORDER,
    METRIC_DEFS,
    STATE_DEFS,
    defs_for_category,
)
from solana_dashboard.core.store import load_snapshot
from solana_dashboard.render.dashboard import fmt_timestamp, source_label, tile_value

logger = logging.getLogger(__name__)

CHANGE_THRESHOLD_PCT = 1.0
PP_THRESHOLD = 0.05  # percentage-point threshold for %-unit metrics

# Integer-count metrics: any change of >= 1 counts as a change.
INTEGER_KEYS = {d.key for d in METRIC_DEFS.values() if d.integer}


def _is_pct(key: str) -> bool:
    d = METRIC_DEFS.get(key)
    return d.unit == "%" if d else key.endswith("_pct")


@dataclass(frozen=True)
class Change:
    """One detected change between two snapshots."""

    key: str
    label: str
    prev: float | None
    cur: float | None
    delta_pct: float | None
    note: str = ""


def diff_metrics(prev: dict[str, dict], cur: dict[str, dict]) -> list[Change]:
    """Compare two snapshots' metrics; return notable changes, ordered."""
    changes: list[Change] = []
    for key, m in cur.items():
        d = METRIC_DEFS.get(key)
        label = d.label if d else key
        p = prev.get(key)
        if p is None:
            changes.append(Change(key, label, None, m["value"], None, "first measurement"))
            continue
        prev_val, cur_val = float(p["value"]), float(m["value"])
        if prev_val == cur_val:
            continue
        if key == "network.epoch":
            changes.append(
                Change(key, label, prev_val, cur_val, None,
                       f"epoch advanced to {cur_val:,.0f}")
            )
            continue
        if _is_pct(key):  # percentage-point deltas
            if abs(cur_val - prev_val) >= PP_THRESHOLD:
                changes.append(
                    Change(key, label, prev_val, cur_val,
                           (cur_val - prev_val) / prev_val * 100 if prev_val else None,
                           f"{cur_val - prev_val:+.2f} pp")
                )
            continue
        if key in INTEGER_KEYS:
            if abs(cur_val - prev_val) >= 1:
                delta = (cur_val - prev_val) / prev_val * 100 if prev_val else None
                changes.append(Change(key, label, prev_val, cur_val, delta))
            continue
        if prev_val != 0:
            delta = (cur_val - prev_val) / prev_val * 100
            if abs(delta) >= CHANGE_THRESHOLD_PCT:
                changes.append(Change(key, label, prev_val, cur_val, delta))
    return changes


def _delta_text(c: Change) -> str:
    """Format the Δ column: pp for %-metrics, absolute for counts, else pct."""
    if _is_pct(c.key) and c.note:
        return c.note  # percentage-point delta reads better
    if c.key in INTEGER_KEYS and c.prev is not None and c.cur is not None:
        return f"{c.cur - c.prev:+,.0f}"  # absolute count/slot delta
    return f"{c.delta_pct:+.1f}%" if c.delta_pct is not None else c.note


def diff_state(prev: dict[str, str], cur: dict[str, str]) -> list[str]:
    """Return human-readable lines for state entries that changed."""
    lines = []
    for key, value in cur.items():
        before = prev.get(key)
        if before is not None and before != value:
            label = key.removeprefix("upgrade.").replace("_", " ")
            lines.append(f"- **{label}**: `{before}` → `{value}`")
    return lines


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data._"
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def _summary_line(metrics: dict[str, dict]) -> str:
    """One-sentence executive summary. Values reuse tile formatting."""

    def v(key: str) -> float | None:
        m = metrics.get(key)
        return m["value"] if m else None

    parts = []
    epoch, progress = v("network.epoch"), v("network.epoch_progress_pct")
    if epoch is not None and progress is not None:
        parts.append(
            f"the network was in **epoch {epoch:,.0f}** "
            f"({tile_value('network.epoch_progress_pct', progress)} through)")
    tps = v("network.tps")
    if tps is not None:
        parts.append(f"processing ~**{tile_value('network.tps', tps)} tx/s**")
    slot = v("network.avg_slot_time_ms")
    if slot is not None:
        parts.append(f"at **{tile_value('network.avg_slot_time_ms', slot)}** average slot time")
    sol = v("market.sol_price_usd")
    if sol is not None:
        parts.append(f"SOL traded at **{tile_value('market.sol_price_usd', sol)}**")
    tvl = v("defi.solana_tvl_usd")
    if tvl is not None:
        bits = [f"TVL **{tile_value('defi.solana_tvl_usd', tvl)}**"]
        dex, stables = v("defi.dex_volume_24h_usd"), v("defi.stablecoin_supply_usd")
        if dex is not None:
            bits.append(f"24h DEX volume **{tile_value('defi.dex_volume_24h_usd', dex)}**")
        if stables is not None:
            bits.append(f"stablecoin supply **{tile_value('defi.stablecoin_supply_usd', stables)}**")
        parts.append("DeFi: " + ", ".join(bits))
    active = v("validators.active_count")
    if active is not None:
        part = f"validators: **{active:,.0f} active"
        delinquent, del_pct = v("validators.delinquent_count"), v("validators.delinquent_stake_pct")
        if delinquent is not None:
            part += f"**, {delinquent:,.0f} delinquent"
            if del_pct is not None:
                part += f" ({tile_value('validators.delinquent_stake_pct', del_pct)} of stake)"
        parts.append(part)
    return "As of the latest cycle, " + "; ".join(parts) + "."


def _category_table(category: str, metrics: dict[str, dict]) -> str:
    rows = []
    for d in defs_for_category(category):
        m = metrics.get(d.key)
        value = tile_value(d.key, m["value"]) if m else "—"
        source = source_label(m["source"]) if m else "unavailable"
        rows.append([f"**{d.label}**", value, d.unit or "—", source])
    return _md_table(["Metric", "Value", "Unit", "Source"], rows)


def render_report(
    cur_path: Path, prev_path: Path | None, reports_dir: Path
) -> Path:
    """Assemble reports/report.md from the newest two snapshots."""
    cur = load_snapshot(cur_path)
    cur_metrics = cur["metrics"]
    cur_state = cur.get("state", {})

    header_date = fmt_timestamp(cur["collected_at"])

    # --- changelog ---
    change_lines: list[str] = []
    if prev_path:
        prev = load_snapshot(prev_path)
        prev_metrics = prev["metrics"]
        prev_state = prev.get("state", {})
        prev_date = fmt_timestamp(prev["collected_at"])
        changes = diff_metrics(prev_metrics, cur_metrics)
        state_changes = diff_state(prev_state, cur_state)

        if changes:
            change_lines.append(f"### Metrics — since {prev_date} UTC")
            rows = []
            for c in changes:
                before = tile_value(c.key, c.prev) if c.prev is not None else "—"
                after = tile_value(c.key, c.cur) if c.cur is not None else "—"
                rows.append([c.label, before, after, _delta_text(c)])
            change_lines.append(_md_table(["Metric", "Before", "After", "Δ"], rows))
        if state_changes:
            change_lines.append(f"### Governance — since {prev_date} UTC")
            change_lines.extend(state_changes)
        if not changes and not state_changes:
            change_lines.append("No notable changes since the previous cycle.")
    else:
        change_lines.append("First cycle — no baseline to diff yet.")

    # --- upgrades / governance table ---
    upgrade_rows: list[list[str]] = []
    for key, label in STATE_DEFS:
        value = cur_state.get(key)
        if value:
            upgrade_rows.append([label, value, "state snapshot"])
    if upgrade_rows:
        stars = cur_metrics.get("upgrade.alpenglow_stars")
        if stars:
            d = METRIC_DEFS["upgrade.alpenglow_stars"]
            upgrade_rows.append([d.label, f"{stars['value']:,.0f}",
                                 source_label(stars["source"])])
    else:
        upgrade_rows.append(["—", "Upgrade tracking begins next cycle", "—"])

    # --- definitions appendix ---
    def_rows = [
        [d.key, d.label, d.definition, d.category]
        for d in METRIC_DEFS.values()
    ]

    category_sections = "\n\n".join(
        f"## {category}\n\n{_category_table(category, cur_metrics)}"
        for category in CATEGORY_ORDER
    )

    md = f"""# Solana Ecosystem Report

_Generated {header_date} UTC · [dashboard](dashboard.html) · [machine-readable JSON](latest.json)_

## Executive summary

{_summary_line(cur_metrics)}

## What changed

{"\n\n".join(change_lines)}

{category_sections}

## Upgrades & governance

{_md_table(["Item", "Status", "Tracked from"], upgrade_rows)}

## Sources & methodology

- **Solana RPC** (public mainnet `api.mainnet-beta.solana.com`): `getSlot`,
  `getEpochInfo`, `getVoteAccounts`, `getRecentPerformanceSamples`. TPS =
  `numTransactions / samplePeriodSecs`; slot time = `samplePeriodSecs /
  numSlots`; epoch progress = `slotIndex / slotsInEpoch`.
- **DeFiLlama**: `/v2/chains` (TVL), `/overview/dexs` (DEX volume, protocols
  listing Solana), `stablecoins` (chain circulating supply).
- **CoinGecko**: `simple/price` (SOL spot), `market_chart` (90-day history).
- **GitHub API**: SIMD proposals frontmatter; `anza-xyz/alpenglow` metadata.
- **Dune Analytics** (optional): on-chain activity metrics (active wallets,
  fee revenue) from user-configured queries. Requires a free Dune API key
  (`DUNE_API_KEY`) and a query map (`DUNE_QUERIES`); rows stay unavailable
  while unconfigured. See the README for activation.
- **Cadence**: nightly at 03:23 UTC via GitHub Actions; the repo commits
  regenerated artifacts every cycle. Every metric's definition, source, and
  collection time is embedded in `latest.json`.

## Metric definitions (appendix)

{_md_table(["Key", "Metric", "Definition", "Category"], def_rows)}
"""

    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "report.md"
    out.write_text(md, encoding="utf-8")
    logger.info("report written: %s (%d bytes)", out, out.stat().st_size)
    return out
