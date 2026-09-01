"""Pipeline: run one collection cycle end-to-end.

collect → merge into metric set → persist (SQLite + snapshot JSON) → export
machine-readable latest.json. Failures degrade gracefully: a failed collector
is logged and reported, never fatal to the whole cycle (the nightly CI run
must survive a flaky third-party API).

Usage:  python -m solana_dashboard collect [--data-dir data]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from solana_dashboard.collectors import ALL_COLLECTORS, ALL_STATE_COLLECTORS
from solana_dashboard.core.schema import (
    CATEGORY_ORDER,
    METRIC_DEFS,
    defs_for_category,
    utcnow,
)
from solana_dashboard.core.store import Store

logger = logging.getLogger(__name__)
console = Console()

# Brief compliance gate, derived from the registry (required=True entries).
REQUIRED_METRIC_KEYS = [d.key for d in METRIC_DEFS.values() if d.required]


def run_cycle(data_dir: Path) -> dict:
    """Run all collectors and persist results. Returns cycle report dict."""
    now = utcnow()
    store = Store(data_dir)
    collected: list = []
    failures: list[str] = []
    state: dict[str, str] = {}

    for name, collector in ALL_COLLECTORS.items():
        try:
            metrics = collector()
            collected.extend(metrics)
            logger.info("%s: %d metrics", name, len(metrics))
        except Exception as exc:  # noqa: BLE001 — one bad source must not kill the cycle
            failures.append(f"{name}: {exc}")
            logger.error("collector %s failed: %s", name, exc)

    for name, collector in ALL_STATE_COLLECTORS.items():
        try:
            state_metrics, state_entries = collector()
            collected.extend(state_metrics)
            state.update(state_entries)
            logger.info("%s: %d metrics, %d state entries",
                        name, len(state_metrics), len(state_entries))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            logger.error("state collector %s failed: %s", name, exc)

    store.insert_cycle(collected)
    store.insert_state(state, now)
    snapshot = store.write_snapshot(collected, now, state=state)
    store.close()

    present = {m.key for m in collected}
    missing = [k for k in REQUIRED_METRIC_KEYS if k not in present]

    report = {
        "collected_at": now.isoformat(),
        "metric_count": len(collected),
        "state_entry_count": len(state),
        "collector_failures": failures,
        "missing_required": missing,
        "snapshot": str(snapshot),
    }
    _print_report(report, collected)
    return report


def _print_report(report: dict, metrics: list) -> None:
    console.print(f"[bold]Cycle[/] {report['collected_at']} — "
                  f"{report['metric_count']} metrics collected")

    table = Table(title="Metrics")
    table.add_column("Category", style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_column("Unit")
    table.add_column("Source", style="dim")

    by_key = {m.key: m for m in metrics}
    for category in CATEGORY_ORDER:
        for d in defs_for_category(category):
            m = by_key.get(d.key)
            if m is None:
                table.add_row(category, d.label, "[red]—[/]", d.unit or "", "missing")
                continue
            value = f"{m.value:,.0f}" if (d.unit is None and m.value == int(m.value)) else f"{m.value:,.2f}"
            table.add_row(category, d.label, value, d.unit or "", m.source)

    console.print(table)

    if report["collector_failures"]:
        console.print("[yellow]Collector failures:[/]")
        for f in report["collector_failures"]:
            console.print(f"  • {f}")
    if report["missing_required"]:
        console.print("[red]Missing required metrics:[/] " + ", ".join(report["missing_required"]))
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="solana-dashboard")
    parser.add_argument("--data-dir", default="data", help="Data directory (default: data)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_cycle(Path(args.data_dir))
    return 0
