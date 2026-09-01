"""CLI entry point: python -m solana_dashboard <command>.

Commands:
  collect   Run one collection cycle (persist snapshot + history)
  render    Regenerate artifacts (dashboard.html / latest.json)
  serve     Serve the reports directory locally for testing
"""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import webbrowser
from pathlib import Path

from solana_dashboard.core.pipeline import main as collect_main
from solana_dashboard.core.store import newest_snapshot, previous_snapshot
from solana_dashboard.render.dashboard import render_dashboard
from solana_dashboard.render.export import export_latest
from solana_dashboard.render.report import render_report


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: python -m solana_dashboard {collect|render|serve} [--data-dir DIR]")
        return 0

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command == "collect":
        return collect_main(rest)

    if command == "render":
        parser = argparse.ArgumentParser(prog="solana-dashboard render")
        parser.add_argument("--data-dir", default="data")
        args = parser.parse_args(rest)
        data_dir = Path(args.data_dir)
        reports_dir = data_dir.parent / "reports"
        cur = newest_snapshot(data_dir)
        if cur is None:
            print(f"error: no snapshots in {data_dir / 'snapshots'} — run collect first")
            return 2
        prev = previous_snapshot(data_dir)
        dashboard = render_dashboard(cur, data_dir, reports_dir)
        report = render_report(cur, prev, reports_dir)
        export_latest(cur, reports_dir)
        print(f"dashboard: {dashboard}")
        print(f"report:    {report}")
        print(f"json:      {reports_dir / 'latest.json'}")
        return 0

    if command == "serve":
        parser = argparse.ArgumentParser(prog="solana-dashboard serve")
        parser.add_argument("--data-dir", default="data")
        parser.add_argument("--port", type=int, default=8000)
        parser.add_argument("--no-browser", action="store_true")
        args = parser.parse_args(rest)
        reports_dir = Path(args.data_dir).parent / "reports"
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(reports_dir)
        )
        with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
            url = f"http://127.0.0.1:{args.port}/dashboard.html"
            print(f"serving {reports_dir} → {url}")
            if not args.no_browser:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")
        return 0

    print(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
