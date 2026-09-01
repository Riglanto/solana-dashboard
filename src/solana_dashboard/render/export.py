"""Machine-readable export: copies the newest snapshot to reports/latest.json.

This is the stable artifact consumers (and the write-up) reference. The full
dashboard/report renderers land in Week 2; export exists from day one so the
CI loop is real immediately.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def export_latest(cur_path: Path, reports_dir: Path) -> Path:
    """Copy newest snapshot → reports/latest.json. Returns output path."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "latest.json"
    shutil.copyfile(cur_path, out)
    return out
