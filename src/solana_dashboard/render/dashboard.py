"""Dashboard renderer: single-file dark-theme HTML (Dune/Superteam aesthetic).

The output is fully self-contained — embedded snapshot data, inline ECharts
(vendored), zero CDN dependencies — so it renders anywhere: GitHub Pages, a
static host, file://, or the local `serve` command.

Layout (form first, per dataviz method):
  - KPI stat tiles (hero numbers) for headline metrics
  - line/area charts for change-over-time (SOL price, TVL, TPS)
  - donut for validator stake split (2 categories, legend + direct labels)
  - full metric registry table (definitions + lineage — the differentiator)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from solana_dashboard.collectors.base import get_json
from solana_dashboard.core.schema import (
    CATEGORY_ORDER,
    METRIC_DEFS,
    STATE_DEFS,
    defs_for_category,
    utcnow,
)
from solana_dashboard.core.store import Store, load_snapshot
from solana_dashboard.render.rain_assets import LOGO_JUP, LOGO_SOL, LOGO_USDC

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR_ECHARTS = REPO_ROOT / "vendor" / "echarts.min.js"

COINGECKO_HISTORY_URL = "https://api.coingecko.com/api/v3/coins/solana/market_chart"
DEFILLAMA_TVL_HISTORY_URL = "https://api.llama.fi/v2/historicalChainTvl/Solana"
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
DEFILLAMA_CHAINS_URL = "https://api.llama.fi/v2/chains"


# ---------------------------------------------------------------------------
# Historical series (fetched at render time; every failure degrades gracefully)
# ---------------------------------------------------------------------------

def fetch_price_history(days: int = 90) -> list[list[float]] | None:
    """[[ts_ms, usd], ...] — CoinGecko market_chart (ms epoch, as returned)."""
    try:
        data = get_json(
            COINGECKO_HISTORY_URL,
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            retries=2,
        )
        prices = data.get("prices", []) if isinstance(data, dict) else []
        return [[float(ts), float(price)] for ts, price in prices]
    except Exception as exc:  # noqa: BLE001 — degrade, don't kill the render
        logger.warning("price history unavailable: %s", exc)
        return None


def fetch_tvl_history(days: int = 30) -> list[list[float]] | None:
    """[[ts_ms, tvl_usd], ...] — DeFiLlama historical chain TVL.

    The endpoint returns the full multi-year series; request only the last
    `days` via start/end (seconds) so the payload stays small. Epoch
    timestamps are emitted in milliseconds to match ECharts time axes.
    """
    try:
        now = utcnow().timestamp()
        data = get_json(
            DEFILLAMA_TVL_HISTORY_URL,
            params={"start": int(now - days * 86400), "end": int(now)},
            retries=2,
        )
        if not isinstance(data, list):
            return None
        cutoff = now - days * 86400
        return [[float(pt["date"]) * 1000, float(pt["tvl"])] for pt in data
                if pt["date"] >= cutoff]
    except Exception as exc:  # noqa: BLE001
        logger.warning("tvl history unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _ms_history(store: Store, key: str) -> list[list[float]]:
    """Per-cycle [[ts_ms, value], ...] history for one metric key.

    collected_at is stored as ISO; epoch milliseconds match ECharts time
    axes (numbers are interpreted as ms).
    """
    return [
        [datetime.fromisoformat(ts).timestamp() * 1000, value]
        for ts, value in store.history_for_key(key)
    ]


def _cycle_hint(n: int) -> str:
    """Cards charting per-cycle SQLite history explain the sparse start."""
    if n < 3:
        return "<p class='hint'>history accumulates nightly — one point per cycle</p>"
    return "<p class='hint'>one point per nightly cycle</p>"

def fmt_compact(value: float) -> str:
    """1_234_567_890 -> 1.23B ; 94.17 -> 94.17 (USD prices keep precision)."""
    magnitude = abs(value)
    if magnitude >= 1e9:
        return f"{value / 1e9:,.2f}B"
    if magnitude >= 1e6:
        return f"{value / 1e6:,.2f}M"
    if magnitude >= 1e3:
        return f"{value / 1e3:,.2f}K"
    if magnitude >= 10:
        return f"{value:,.2f}"
    return f"{value:,.4f}"


def tile_value(key: str, value: float) -> str:
    """Registry-driven display formatting for KPI tiles and tables."""
    defn = METRIC_DEFS.get(key)
    unit = defn.unit if defn else None
    if unit == "USD":
        return f"${fmt_compact(value)}"
    if unit == "SOL":
        return f"{fmt_compact(value)} SOL"
    if unit == "ms":
        return f"{value:,.0f} ms"
    if unit == "%":
        return f"{value:,.2f}%"
    if defn is not None and defn.integer:
        return f"{value:,.0f}"
    return f"{value:,.{defn.precision if defn else 2}f}"


def source_label(source: str) -> str:
    """Strip the URL detail: 'solana-rpc(https://...)' -> 'solana-rpc'."""
    return source.split("(")[0]


def fmt_timestamp(iso: str) -> str:
    """ISO -> '2026-08-24 03:34:04' (UTC, for display)."""
    return iso[:19].replace("T", " ")


def series_delta(history: list[list[float]] | None) -> float | None:
    """Pct change first→last point; None if there aren't enough points."""
    if not history or len(history) < 2:
        return None
    first, last = history[0][1], history[-1][1]
    return (last - first) / first * 100 if first else None


# ---------------------------------------------------------------------------
# Hero background: "Solana rain" — decorative canvas animation.
# Binary + ◎ glyph streaks in the dashboard palette; recessive by design
# (low alpha, aria-hidden, respects prefers-reduced-motion, pauses off-screen).
# ---------------------------------------------------------------------------

RAIN_JS_TEMPLATE = """
(() => {
  const canvas = document.getElementById('rain');
  if (!canvas) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const ctx = canvas.getContext('2d');
  const FONT = 16, STREAK = 10, GLYPHS = '01·';
  // Column mix: mostly the Solana mark, a couple of token logos, and a
  // few binary columns for matrix texture. Type is fixed per column.
  const TYPES = ['sol','sol','sol','sol','sol','sol','sol','sol','usdc','jup','glyph'];
  const L = {
    sol: '__LOGO_SOL__',
    usdc: '__LOGO_USDC__',
    jup: '__LOGO_JUP__',
  };
  const sprites = {};   // type -> pre-rendered offscreen canvas at FONT*dpr
  let cols = 0, rows = 0, drops = [];

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(canvas.clientWidth * dpr);
    canvas.height = Math.floor(canvas.clientHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cols = Math.max(1, Math.ceil(canvas.clientWidth / FONT));
    rows = Math.ceil(canvas.clientHeight / FONT) + STREAK;
    drops = Array.from({ length: cols }, (_, i) => ({
      x: i * FONT + FONT / 2,
      y: -Math.random() * rows * 0.8,        // staggered entry
      speed: 0.35 + Math.random() * 0.75,
      type: TYPES[i % TYPES.length],
      glyph: GLYPHS[(Math.random() * GLYPHS.length) | 0],
    }));
  }

  function paintGlyph(d) {
    const head = Math.floor(d.y);
    for (let k = 0; k < STREAK; k++) {
      const cell = head - k;
      if (cell < 0) continue;
      ctx.fillStyle = k === 0
        ? 'rgba(226, 246, 255, 0.85)'
        : `rgba(8, 145, 178, ${0.16 * (1 - k / STREAK)})`;  // palette cyan
      ctx.fillText(d.glyph, d.x, cell * FONT + FONT * 0.8);
    }
  }

  function paintLogo(d) {
    const sprite = sprites[d.type];
    if (!sprite) return;
    for (let k = 0; k < 4; k++) {
      ctx.globalAlpha = k === 0 ? 1 : 0.35 / k;   // 1, .35, .175, .117
      ctx.drawImage(sprite, d.x - FONT / 2, d.y * FONT - k * FONT - FONT / 2,
                    FONT, FONT);
    }
    ctx.globalAlpha = 1;
  }

  let last = 0;
  function frame(now) {
    if (now - last < 33) return requestAnimationFrame(frame);  // ~30fps
    last = now;
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    ctx.font = `${FONT}px ui-monospace, "Cascadia Mono", Consolas, monospace`;
    ctx.textAlign = 'center';
    for (const d of drops) {
      d.y += d.speed;
      if (d.y - STREAK > rows) d.y = -STREAK;
      if (d.type === 'glyph') paintGlyph(d); else paintLogo(d);
    }
    requestAnimationFrame(frame);
  }

  // Pre-render each logo once; start the loop when all are ready.
  const names = Object.keys(L);
  let pending = names.length;
  function loaded() { if (--pending === 0) { resize(); start(); } }
  for (const name of names) {
    const img = new Image();
    img.onload = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const s = Math.round(FONT * dpr);
      const c = document.createElement('canvas');
      c.width = c.height = s;
      c.getContext('2d').drawImage(img, 0, 0, s, s);
      sprites[name] = c;
      loaded();
    };
    img.onerror = loaded;   // data URIs; belt-and-braces
    img.src = L[name];
  }

  function start() {
    addEventListener('resize', resize);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) last = 0;  // skip the jump on return
    });
    requestAnimationFrame(frame);
  }
})();
"""

RAIN_JS = (
    RAIN_JS_TEMPLATE
    .replace("__LOGO_SOL__", LOGO_SOL)
    .replace("__LOGO_USDC__", LOGO_USDC)
    .replace("__LOGO_JUP__", LOGO_JUP)
)

# ---------------------------------------------------------------------------
# HTML fragments
# ---------------------------------------------------------------------------

PAGE_CSS = """
:root {
  color-scheme: dark;
  --page: #0d0d0d;          /* page plane */
  --surface: #1a1a19;       /* card / chart surface */
  --surface-2: #232322;     /* hover / raised */
  --ink: #ffffff;           /* primary text */
  --ink-2: #c3c2b7;         /* secondary text */
  --muted: #898781;         /* axis labels, meta */
  --gridline: #2c2c2a;
  --baseline: #383835;
  --border: rgba(255,255,255,0.10);
  --cyan: #0891b2;          /* series 1 (validated on dark) */
  --violet: #9085e9;        /* series 2 (validated on dark) */
  --good: #0ca30c;          /* delta up / status good */
  --critical: #d03b3b;      /* delta down / status critical */
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--page);
  color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  line-height: 1.45;
}
main { max-width: 1180px; margin: 0 auto; padding: 0 20px 48px; }

/* -- top bar / hero -- */
.topbar {
  position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
  padding: 18px 20px; border-bottom: 1px solid var(--border);
  background:
    radial-gradient(60% 140% at 88% -30%, rgba(144, 133, 233, 0.10), transparent 60%),
    radial-gradient(55% 140% at 8% 130%, rgba(8, 145, 178, 0.09), transparent 60%);
}
#rain {
  position: absolute; inset: 0; width: 100%; height: 100%;
  pointer-events: none; z-index: 0; opacity: 0.6;
}
.brand { display: flex; align-items: center; gap: 12px; position: relative; z-index: 1; }
.mark {
  width: 40px; height: 40px; border-radius: 10px; flex: none;
  display: grid; place-items: center; font-size: 20px; font-weight: 700;
  background: linear-gradient(135deg, #0891b2 0%, #9085e9 100%);
  color: #fff;
  box-shadow: 0 0 22px rgba(8, 145, 178, 0.30);
  animation: markGlow 6s ease-in-out infinite;
}
@keyframes markGlow {
  0%, 100% { box-shadow: 0 0 16px rgba(8, 145, 178, 0.25); }
  50%      { box-shadow: 0 0 30px rgba(144, 133, 233, 0.45); }
}
.brand h1 { font-size: 17px; font-weight: 650; letter-spacing: -0.01em; }
.sub { color: var(--muted); font-size: 12px; margin-top: 2px; }
.status { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; position: relative; z-index: 1; }
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--border); border-radius: 999px;
  padding: 4px 10px; font-size: 12px; color: var(--ink-2);
  background: var(--surface);
}
.badge .dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--good);
}
.badge.live .dot { animation: pulse 2.2s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.25; } }
.updated { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }

@media (prefers-reduced-motion: reduce) {
  #rain { display: none; }
  .mark, .badge.live .dot { animation: none; }
}

/* -- KPI tiles -- */
.kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px; margin: 22px 0;
}
.tile {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
}
.tile-label { color: var(--muted); font-size: 12px; font-weight: 550; }
.tile-value {
  font-size: 24px; font-weight: 650; margin-top: 6px;
  font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
}
.tile-delta { font-size: 12px; font-weight: 600; margin-left: 6px; }
.delta-up { color: var(--good); }
.delta-down { color: var(--critical); }
.tile-source { color: var(--muted); font-size: 11px; margin-top: 6px; }
.tile-source .live-flag { color: var(--good); }
.bar-track {
  height: 5px; border-radius: 3px; background: var(--surface-2);
  margin-top: 10px; overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, var(--cyan), var(--violet));
}

/* -- charts -- */
.charts {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px; margin-bottom: 22px;
}
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px;
}
.card h2 { font-size: 13px; font-weight: 600; color: var(--ink-2); }
.card .hint { color: var(--muted); font-size: 11px; margin-top: 2px; }
.chart { width: 100%; height: 260px; margin-top: 10px; }
.chart-empty {
  width: 100%; height: 260px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 4px;
  color: var(--muted); font-size: 12px; line-height: 1.5; text-align: center;
}
.range-toggle { display: flex; gap: 4px; margin-top: 8px; }
.range-toggle button {
  background: transparent; color: var(--muted); border: 1px solid var(--border);
  border-radius: 6px; padding: 2px 10px; font-size: 11px; cursor: pointer;
}
.range-toggle button.active { color: var(--ink); border-color: var(--cyan); }
.empty-note { color: var(--muted); font-size: 12px; margin-top: 8px; }

/* -- registry table -- */
.table-card { overflow-x: auto; }
.table-card h2 { margin-bottom: 12px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  text-align: left; color: var(--muted); font-weight: 550; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.04em;
  padding: 8px 10px; border-bottom: 1px solid var(--border);
}
td { padding: 9px 10px; border-bottom: 1px solid var(--gridline); vertical-align: top; }
td.num { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
td .def { color: var(--muted); font-size: 12px; }
.cat { color: var(--cyan); font-size: 11px; font-weight: 600; white-space: nowrap; }
.src { color: var(--muted); font-size: 11px; white-space: nowrap; }
tr:hover td { background: var(--surface-2); }

footer {
  border-top: 1px solid var(--border); color: var(--muted);
  font-size: 12px; padding: 16px 20px 32px; text-align: center;
}
"""

APP_JS = """
const fmt = (v) => {
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(2) + 'K';
  return v.toFixed(2);
};
// Tooltip values keep the full magnitude with at most 2 decimals
// (TPS 3,506.42, SOL $100.12); only B/M compact for very large numbers.
const fmt2 = (v) => {
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  return Number(v.toFixed(2)).toLocaleString('en-US');
};

const AXIS = {
  axisLine: { lineStyle: { color: '#383835' } },
  axisLabel: { color: '#898781', fontSize: 11 },
  splitLine: { lineStyle: { color: '#2c2c2a' } },
};
const TOOLTIP = {
  trigger: 'axis',
  backgroundColor: '#1a1a19',
  borderColor: 'rgba(255,255,255,0.10)',
  textStyle: { color: '#fff', fontSize: 12 },
  axisPointer: { type: 'cross', lineStyle: { color: '#383835' } },
  valueFormatter: (v) => fmt2(v),
};

function lineSeries(data, color, area) {
  return {
    type: 'line', data, showSymbol: data.length < 8,
    symbolSize: 6, lineStyle: { width: 2, color },
    itemStyle: { color },
    areaStyle: area ? {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: color + '2e' },
        { offset: 1, color: color + '00' },
      ]),
    } : undefined,
  };
}

function timeChart(el, series, color, opts) {
  const chart = echarts.init(el, null, { renderer: 'canvas' });
  chart.setOption({
    tooltip: TOOLTIP,
    grid: { left: 8, right: 16, top: 10, bottom: 4, containLabel: true },
    xAxis: { type: 'time', ...AXIS, splitLine: { show: false } },
    // AXIS is shared with the time x-axis, so the value formatter goes on
    // the y-axis only (fmt2 would mangle date labels).
    yAxis: { type: 'value', ...AXIS, axisLabel: { ...AXIS.axisLabel, formatter: fmt2 } },
    series,
  });
  return chart;
}

// Charts need >= 2 points. A lone point (TPS: one per nightly cycle) or a
// failed history fetch gets an explanatory placeholder, not a blank card.
function chartPlaceholder(id, lines) {
  document.getElementById(id).innerHTML =
    '<div class="chart-empty">' + lines.map((l) => '<div>' + l + '</div>').join('') + '</div>';
}

const PAYLOAD = JSON.parse(document.getElementById('payload').textContent);

// --- SOL price chart with 7/30/90d range toggle ---
const priceCard = document.getElementById('price-card');
if (PAYLOAD.price_history && PAYLOAD.price_history.length > 1) {
  const days = 90 * 86400;
  const now = Date.now();
  let priceChart = null;
  const slice = (d) => PAYLOAD.price_history.filter(([t]) => t >= now - d * 86400000);
  function draw(d) {
    if (!priceChart) priceChart = timeChart(
      document.getElementById('chart-price'), [lineSeries(slice(d), '#0891b2', true)],
      '#0891b2');
    else priceChart.setOption({ series: [{ data: slice(d) }] });
  }
  document.querySelectorAll('#price-card .range-toggle button').forEach((b) => {
    b.addEventListener('click', () => {
      document.querySelectorAll('#price-card .range-toggle button').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      draw(parseInt(b.dataset.days, 10));
    });
  });
  draw(90);
} else {
  chartPlaceholder('chart-price', ['SOL price history unavailable this cycle.', 'It returns on the next nightly run.']);
}

// --- TVL area chart ---
if (PAYLOAD.tvl_history && PAYLOAD.tvl_history.length > 1) {
  timeChart(document.getElementById('chart-tvl'),
    [lineSeries(PAYLOAD.tvl_history, '#9085e9', true)], '#9085e9');
} else {
  chartPlaceholder('chart-tvl', ['TVL history unavailable this cycle.', 'It returns on the next nightly run.']);
}

// --- TPS per-cycle chart ---
if (PAYLOAD.tps_history && PAYLOAD.tps_history.length > 1) {
  timeChart(document.getElementById('chart-tps'),
    [lineSeries(PAYLOAD.tps_history, '#0891b2', false)], '#0891b2');
} else {
  chartPlaceholder('chart-tps', ['TPS history accumulates one point per nightly cycle.', 'The chart fills in as cycles run.']);
}

// --- DEX volume per cycle ---
if (PAYLOAD.dex_history && PAYLOAD.dex_history.length > 1) {
  timeChart(document.getElementById('chart-dex'),
    [lineSeries(PAYLOAD.dex_history, '#34d399', true)], '#34d399');
} else {
  chartPlaceholder('chart-dex', ['DEX volume history accumulates one point per nightly cycle.', 'The chart fills in as cycles run.']);
}

// --- Stablecoin supply per cycle ---
if (PAYLOAD.stable_history && PAYLOAD.stable_history.length > 1) {
  timeChart(document.getElementById('chart-stable'),
    [lineSeries(PAYLOAD.stable_history, '#f59e0b', true)], '#f59e0b');
} else {
  chartPlaceholder('chart-stable', ['Stablecoin supply history accumulates one point per nightly cycle.', 'The chart fills in as cycles run.']);
}

// --- Validator stake donut (2 categories: legend + direct labels) ---
const vChart = echarts.init(document.getElementById('chart-validators'));
vChart.setOption({
  tooltip: { trigger: 'item', backgroundColor: '#1a1a19', borderColor: 'rgba(255,255,255,0.10)', textStyle: { color: '#fff' } },
  legend: { bottom: 0, textStyle: { color: '#c3c2b7', fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
  series: [{
    type: 'pie', radius: ['58%', '78%'], center: ['50%', '44%'],
    itemStyle: { borderColor: '#1a1a19', borderWidth: 2 },
    label: { color: '#c3c2b7', fontSize: 11, formatter: '{b} {d}%' },
    labelLine: { lineStyle: { color: '#383835' } },
    data: [
      { name: 'Active stake', value: PAYLOAD.validators.active_stake, itemStyle: { color: '#0891b2' } },
      { name: 'Delinquent stake', value: PAYLOAD.validators.delinquent_stake, itemStyle: { color: '#9085e9' } },
    ],
  }],
});

// --- Live refresh: CORS-friendly public APIs, silent failure ---
function liveUpdate() {
  Promise.all([
    fetch(PAYLOAD.live.price_url).then((r) => r.json()).catch(() => null),
    fetch(PAYLOAD.live.tvl_url).then((r) => r.json()).catch(() => null),
  ]).then(([price, chains]) => {
    if (price && price.solana && price.solana.usd != null) {
      const el = document.getElementById('live-sol-price');
      el.textContent = '$' + price.solana.usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      document.getElementById('sol-price-src').innerHTML = 'CoinGecko · <span class="live-flag">live</span>';
    }
    if (Array.isArray(chains)) {
      const sol = chains.find((c) => c.name === 'Solana');
      if (sol) {
        const el = document.getElementById('live-tvl');
        el.textContent = '$' + fmt(sol.tvl);
        document.getElementById('tvl-src').innerHTML = 'DeFiLlama · <span class="live-flag">live</span>';
      }
    }
  });
}

// --- relative "updated" timestamp ---
function tickUpdated() {
  const el = document.getElementById('updated');
  const then = new Date(PAYLOAD.generated_at).getTime();
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  let label;
  if (s < 60) label = s + 's ago';
  else if (s < 3600) label = Math.floor(s / 60) + 'm ago';
  else if (s < 86400) label = Math.floor(s / 3600) + 'h ago';
  else label = Math.floor(s / 86400) + 'd ago';
  el.textContent = 'Updated ' + label;
}

liveUpdate();
setInterval(liveUpdate, 60000);
tickUpdated();
setInterval(tickUpdated, 30000);
"""


def _kpi_tile(key: str, value: float, source: str, *,
              live_id: str | None = None, source_id: str | None = None,
              delta: tuple[str, str] | None = None) -> str:
    label = METRIC_DEFS[key].label
    val_id = f' id="{live_id}"' if live_id else ""
    src_id = f' id="{source_id}"' if source_id else ""
    delta_html = ""
    if delta:
        text, cls = delta
        delta_html = f'<span class="tile-delta {cls}">{text}</span>'
    return f"""
    <div class="tile">
      <div class="tile-label">{label}</div>
      <div class="tile-value"{val_id}>{tile_value(key, value)}{delta_html}</div>
      <div class="tile-source"{src_id}>{source}</div>
    </div>"""


def _epoch_tile(epoch: float, progress: float, source: str) -> str:
    return f"""
    <div class="tile">
      <div class="tile-label">Epoch (progress)</div>
      <div class="tile-value">{epoch:,.0f}</div>
      <div class="bar-track"><div class="bar-fill" style="width:{min(progress, 100):.1f}%"></div></div>
      <div class="tile-source">{progress:.1f}% through epoch · {source}</div>
    </div>"""


def _upgrades_card(state: dict[str, str], metrics: dict[str, dict]) -> str:
    rows = []
    for key, label in STATE_DEFS:
        value = state.get(key)
        if value:
            rows.append(f"<tr><td class='cat'>Upgrades</td><td><strong>{label}</strong></td>"
                        f"<td colspan='2'>{value}</td></tr>")
    stars = metrics.get("upgrade.alpenglow_stars")
    if stars:
        d = METRIC_DEFS["upgrade.alpenglow_stars"]
        rows.append(f"<tr><td class='cat'>Upgrades</td><td><strong>{d.label}</strong></td>"
                    f"<td class='num'>{stars['value']:,.0f}</td><td class='src'>{source_label(stars['source'])}</td></tr>")
    if not rows:
        return ""
    return f"""
  <section class="card table-card">
    <h2>Upgrades &amp; governance</h2>
    <table>
      <thead><tr><th>Category</th><th>Item</th><th style="text-align:right">Value</th><th>Tracked from</th></tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </section>"""


def _registry_table(metrics: dict[str, dict]) -> str:
    rows: list[str] = []
    for category in CATEGORY_ORDER:
        for d in defs_for_category(category):
            m = metrics.get(d.key)
            value = tile_value(d.key, m["value"]) if m else "—"
            source = source_label(m["source"]) if m else "unavailable"
            rows.append(f"""
            <tr>
              <td class="cat">{category}</td>
              <td><strong>{d.label}</strong></td>
              <td class="num">{value}</td>
              <td class="num" style="color:var(--muted)">{d.unit or ""}</td>
              <td class="src">{source}</td>
              <td><span class="def">{d.definition}</span></td>
            </tr>""")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_dashboard(cur_path: Path, data_dir: Path, reports_dir: Path) -> Path:
    """Assemble reports/dashboard.html from the newest snapshot + history."""
    payload = load_snapshot(cur_path)
    metrics = payload["metrics"]

    # --- per-cycle history from SQLite (network + DeFi metrics) ---
    store = Store(data_dir)
    tps_history = _ms_history(store, "network.tps")
    dex_history = _ms_history(store, "defi.dex_volume_24h_usd")
    stable_history = _ms_history(store, "defi.stablecoin_supply_usd")
    store.close()

    # --- external history (degrades gracefully) ---
    price_history = fetch_price_history(90)
    tvl_history = fetch_tvl_history(30)

    price_delta = series_delta(price_history)
    tvl_delta = series_delta(tvl_history)

    def delta_html(pct: float | None) -> tuple[str, str] | None:
        if pct is None:
            return None
        sign = "+" if pct >= 0 else "−"
        cls = "delta-up" if pct >= 0 else "delta-down"
        return f"{sign}{abs(pct):.1f}%", cls

    def m(key: str) -> dict | None:
        return metrics.get(key)

    # --- KPI tiles (server-rendered; JS upgrades charts + live refresh) ---
    sol = m("market.sol_price_usd")
    tvl = m("defi.solana_tvl_usd")
    dex = m("defi.dex_volume_24h_usd")
    stables = m("defi.stablecoin_supply_usd")
    tps = m("network.tps")
    epoch = m("network.epoch")
    progress = m("network.epoch_progress_pct")

    tiles = []
    if sol:
        tiles.append(_kpi_tile(
            "market.sol_price_usd", sol["value"], "CoinGecko · snapshot",
            live_id="live-sol-price", source_id="sol-price-src",
            delta=delta_html(price_delta)))
    if tvl:
        tiles.append(_kpi_tile(
            "defi.solana_tvl_usd", tvl["value"], "DeFiLlama · snapshot",
            live_id="live-tvl", source_id="tvl-src",
            delta=delta_html(tvl_delta)))
    if dex:
        tiles.append(_kpi_tile("defi.dex_volume_24h_usd", dex["value"], "DeFiLlama · 24h"))
    if stables:
        tiles.append(_kpi_tile("defi.stablecoin_supply_usd", stables["value"], "DeFiLlama"))
    if tps:
        tiles.append(_kpi_tile("network.tps", tps["value"], source_label(tps["source"])))
    if epoch and progress:
        tiles.append(_epoch_tile(epoch["value"], progress["value"], source_label(epoch["source"])))

    validators = m("validators.active_count")
    delinquent_stake = m("validators.delinquent_stake_pct")
    active_stake_frac = 0.0
    delinquent_stake_frac = 0.0
    if validators and delinquent_stake is not None:
        active_stake_frac = max(0.0, 100.0 - delinquent_stake["value"])
        delinquent_stake_frac = delinquent_stake["value"]

    js_payload = {
        "generated_at": payload["collected_at"],
        "tps_history": tps_history,
        "dex_history": dex_history,
        "stable_history": stable_history,
        "price_history": price_history or [],
        "tvl_history": tvl_history or [],
        "validators": {
            "active_stake": active_stake_frac,
            "delinquent_stake": delinquent_stake_frac,
        },
        "live": {
            "price_url": f"{COINGECKO_PRICE_URL}?ids=solana&vs_currencies=usd",
            "tvl_url": DEFILLAMA_CHAINS_URL,
        },
    }

    echarts_js = VENDOR_ECHARTS.read_text(encoding="utf-8")
    tps_hint = _cycle_hint(len(tps_history))
    dex_hint = _cycle_hint(len(dex_history))
    stable_hint = _cycle_hint(len(stable_history))

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0d0d0d">
<meta name="description" content="Auto-updating Solana ecosystem report: network, validators, market, DeFi and upgrade metrics, refreshed nightly.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpath d='M10 34 L70 34 L62 70 L2 70 Z' fill='%230891b2'/%3E%3Cpath d='M24 20 L84 20 L76 56 L16 56 Z' fill='%239085e9'/%3E%3Cpath d='M38 6 L98 6 L90 42 L30 42 Z' fill='%230891b2'/%3E%3C/svg%3E">
<title>Solana Ecosystem Report</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>◎</text></svg>">
<style>{PAGE_CSS}</style>
</head>
<body>
<header class="topbar">
  <canvas id="rain" aria-hidden="true"></canvas>
  <div class="brand">
    <div class="mark">◎</div>
    <div>
      <h1>Solana Ecosystem Report</h1>
      <p class="sub">Auto-updating · nightly pipeline · data lineage on every metric</p>
    </div>
  </div>
  <div class="status">
    <span class="badge live"><span class="dot"></span>LIVE refresh</span>
    <span class="updated" id="updated"></span>
  </div>
</header>
<main>
  <section class="kpis">
    {"".join(tiles)}
  </section>

  <section class="charts">
    <div class="card" id="price-card">
      <h2>SOL price — 90 days</h2>
      <div class="range-toggle">
        <button data-days="7">7D</button>
        <button data-days="30">30D</button>
        <button data-days="90" class="active">90D</button>
      </div>
      <div id="chart-price" class="chart" role="img" aria-label="SOL price over time"></div>
    </div>
    <div class="card">
      <h2>Solana TVL — 30 days</h2>
      <div id="chart-tvl" class="chart" role="img" aria-label="Solana total value locked over time"></div>
    </div>
    <div class="card">
      <h2>TPS per cycle</h2>
      {tps_hint}
      <div id="chart-tps" class="chart" role="img" aria-label="Solana transactions per second over collected cycles"></div>
    </div>
    <div class="card">
      <h2>DEX volume — per cycle</h2>
      {dex_hint}
      <div id="chart-dex" class="chart" role="img" aria-label="Solana DEX volume over collected cycles"></div>
    </div>
    <div class="card">
      <h2>Stablecoin supply — per cycle</h2>
      {stable_hint}
      <div id="chart-stable" class="chart" role="img" aria-label="Solana stablecoin supply over collected cycles"></div>
    </div>
    <div class="card">
      <h2>Validator stake split</h2>
      <p class="hint">share of total stake, from getVoteAccounts</p>
      <div id="chart-validators" class="chart" role="img" aria-label="Donut chart of active versus delinquent validator stake"></div>
    </div>
  </section>

  {_upgrades_card(payload.get("state", {}), metrics)}

  <section class="card table-card">
    <h2>Metric registry — definitions &amp; lineage</h2>
    <table>
      <thead>
        <tr><th>Category</th><th>Metric</th><th style="text-align:right">Value</th><th style="text-align:right">Unit</th><th>Source</th><th>Definition</th></tr>
      </thead>
      <tbody>
{_registry_table(metrics)}
      </tbody>
    </table>
  </section>
</main>
<footer>
  Generated {fmt_timestamp(payload["collected_at"])} UTC by solana-dashboard ·
  Sources: Solana RPC (public mainnet), DeFiLlama, CoinGecko ·
  Snapshot: {cur_path.name}
</footer>
<script id="payload" type="application/json">{json.dumps(js_payload)}</script>
<script>{echarts_js}</script>
<script>{APP_JS}</script>
<script>{RAIN_JS}</script>
</body>
</html>"""

    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    # index.html makes the Pages root URL serve the dashboard directly
    # (https://<user>.github.io/solana-dashboard/).
    (reports_dir / "index.html").write_text(html, encoding="utf-8")
    logger.info("dashboard written: %s (%d bytes)", out, out.stat().st_size)
    return out
