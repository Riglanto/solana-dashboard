"""Persistence: SQLite history + JSON snapshots.

History enables trend analytics (30/90-day deltas, sparklines) — the
"auto-updating" differentiator — while committed snapshots double as the
machine-readable report artifacts the brief requires.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from solana_dashboard.core.schema import METRIC_DEFS, Metric

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    key          TEXT NOT NULL,
    value        REAL NOT NULL,
    source       TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    unit         TEXT,
    definition   TEXT,
    PRIMARY KEY (key, collected_at)
);

CREATE TABLE IF NOT EXISTS state (
    key          TEXT NOT NULL,
    value        TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (key, collected_at)
);
"""


def snapshot_path(root: Path, collected_at: datetime) -> Path:
    """data/snapshots/2026-08-23T20-15-00Z.json"""
    stamp = collected_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    return root / "snapshots" / f"{stamp}.json"


class Store:
    """SQLite-backed metric history + JSON snapshot writer."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "solana.db"
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(SCHEMA)

    # -- history -----------------------------------------------------------

    def insert_cycle(self, metrics: list[Metric]) -> None:
        """Persist one cycle. Unit/definition come from the registry, so the
        history table stays self-describing without duplicating metadata."""
        rows = []
        for m in metrics:
            d = METRIC_DEFS.get(m.key)
            rows.append((m.key, m.value, m.source, m.collected_at.isoformat(),
                         d.unit if d else None, d.definition if d else ""))
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO metrics"
                " (key, value, source, collected_at, unit, definition)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )

    def history_for_key(
        self, key: str, limit: int = 60
    ) -> list[tuple[str, float]]:
        """(collected_at_iso, value) pairs for one key, oldest first."""
        rows = self._conn.execute(
            "SELECT collected_at, value FROM metrics WHERE key = ?"
            " ORDER BY collected_at ASC LIMIT ?",
            (key, limit),
        ).fetchall()
        return [(ts, value) for ts, value in rows]

    # -- state (string/categorical entries: upgrade statuses etc.) ----------

    def insert_state(self, state: dict[str, str], collected_at: datetime) -> None:
        rows = [(k, v, collected_at.isoformat()) for k, v in state.items()]
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO state (key, value, collected_at)"
                " VALUES (?, ?, ?)",
                rows,
            )

    def latest_state(self) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value FROM state WHERE collected_at = ("
            "  SELECT MAX(collected_at) FROM state)"
        ).fetchall()
        return dict(rows)

    # -- snapshots ----------------------------------------------------------

    def write_snapshot(
        self,
        metrics: list[Metric],
        collected_at: datetime,
        state: dict[str, str] | None = None,
    ) -> Path:
        """Write one JSON snapshot file and return its path."""
        payload = {
            "collected_at": collected_at.isoformat(),
            "cycle": collected_at.strftime("%Y%m%dT%H%M%SZ"),
            "metrics": {m.key: m.to_dict() for m in metrics},
            "state": state or {},
        }
        path = snapshot_path(self.data_dir, collected_at)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        return path

    def close(self) -> None:
        self._conn.close()


def load_snapshot(path: Path) -> dict:
    """Read a snapshot JSON into its raw dict form."""
    return json.loads(path.read_text())


def _snapshot_files(data_dir: Path) -> list[Path]:
    """Snapshot paths, oldest first (empty if the dir is missing/empty)."""
    snap_dir = data_dir / "snapshots"
    if not snap_dir.exists():
        return []
    return sorted(snap_dir.glob("*.json"))


def newest_snapshot(data_dir: Path) -> Path | None:
    files = _snapshot_files(data_dir)
    return files[-1] if files else None


def previous_snapshot(data_dir: Path) -> Path | None:
    """Second-newest snapshot (for change detection in the report)."""
    files = _snapshot_files(data_dir)
    return files[-2] if len(files) >= 2 else None
