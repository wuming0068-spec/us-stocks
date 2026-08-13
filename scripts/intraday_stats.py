#!/usr/bin/env python3
"""
intraday_stats.py — Intraday volatility statistics for options swing trading.
================================================================================
Reads per-stock history from docs/data/history/*.json, computes for 300/200/100/60
trading-day periods:

  - Highest intraday gain   (high vs prev_close)  → UP
  - Lowest intraday drop     (low vs prev_close)   → DOWN
  - Intraday swing range     (high-low vs prev_close) → SWING

Filtering rules:
  - UP:   exclude days where BOTH up<0 AND down<0 (pure-down day)
  - DOWN: exclude days where BOTH up>0 AND down>0 (pure-up day)
  - SWING: no filter

Statistics: P25 / P50 (median) / P75 percentiles with price equivalents.

Output: docs/data/intraday_stats.json
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
STOCKS_FILE = DATA_DIR / "stocks.json"
OUTPUT_FILE = DATA_DIR / "intraday_stats.json"

PERIODS = [300, 200, 100, 60]
PERCENTILES = [25, 50, 75]


def load_json(path: Path, default=None):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def load_history(symbol: str) -> list[dict] | None:
    """Load OHLCV history for a symbol, sorted by date ascending."""
    hist_file = HISTORY_DIR / f"{symbol}.json"
    data = load_json(hist_file)
    if not data or not isinstance(data, list):
        return None
    data.sort(key=lambda r: r.get("date", ""))
    return data


def compute_intraday_metrics(history: list[dict]) -> list[dict]:
    """Compute daily intraday metrics from OHLCV data.
    Each day:
      up    = (high - prev_close) / prev_close * 100
      down  = (low  - prev_close) / prev_close * 100
      swing = (high - low)          / prev_close * 100
    """
    results = []
    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        prev_close = prev.get("close", 0)
        if prev_close <= 0:
            continue
        high = curr.get("high", 0)
        low = curr.get("low", 0)
        results.append({
            "date": curr.get("date", ""),
            "up": round((high - prev_close) / prev_close * 100, 4),
            "down": round((low - prev_close) / prev_close * 100, 4),
            "swing": round((high - low) / prev_close * 100, 4),
        })
    return results


def compute_stats(metrics: list[dict], close: float) -> dict:
    """Compute percentile statistics with filtering.

    UP:   sorted small→large, P25 = small gains, P75 = big gains
    DOWN: sorted large→small (via negation), P25 = mild drops, P75 = deep drops
    SWING: sorted small→large
    """

    up_raw = np.array([m["up"] for m in metrics])
    down_raw = np.array([m["down"] for m in metrics])
    swing_raw = np.array([m["swing"] for m in metrics])

    # UP: exclude pure-down days (both up<0 and down<0)
    up_mask = ~((up_raw < 0) & (down_raw < 0))
    up_filtered = up_raw[up_mask]
    up_sorted = np.sort(up_filtered)  # small → large

    # DOWN: exclude pure-up days (both up>0 and down>0)
    # Negate values so "large→small" on originals = "small→large" on negated
    down_mask = ~((up_raw > 0) & (down_raw > 0))
    down_filtered = down_raw[down_mask]
    down_neg_sorted = np.sort(-down_filtered)  # ascending on negated = descending on original

    # SWING: no filter, small → large
    swing_sorted = np.sort(swing_raw)

    def pstats(arr: np.ndarray, close_price: float, negate: bool = False) -> dict:
        mean = float(np.mean(arr))
        if negate:
            mean = -mean
        n = len(arr)
        result = {"mean": round(mean, 2), "n": n, "n_raw": len(metrics)}
        for p in PERCENTILES:
            val = float(np.percentile(arr, p))
            if negate:
                val = -val
            result[f"p{p}"] = round(val, 2)
            result[f"p{p}_price"] = round(close_price * (1 + val / 100), 2)
        return result

    return {
        "up": pstats(up_sorted, close),
        "down": pstats(down_neg_sorted, close, negate=True),
        "swing": pstats(swing_sorted, close),
    }


def run():
    # Load current stocks to get names, sectors, and close prices
    stocks_data = load_json(STOCKS_FILE, {"stocks": []})
    stock_info = {}
    for s in stocks_data.get("stocks", []):
        sym = s.get("symbol", "").upper()
        if sym:
            stock_info[sym] = {
                "name": s.get("name", sym),
                "sector": s.get("sector", "其他"),
                "close": s.get("close", 0),
            }

    # Also discover from history files
    if HISTORY_DIR.exists():
        for f in HISTORY_DIR.glob("*.json"):
            sym = f.stem.upper()
            if sym not in stock_info:
                stock_info[sym] = {"name": sym, "sector": "其他", "close": 0}

    # Filter out index symbols
    INDEX_SYMBOLS = {'.SOX', '.NDX', '.IXIC', 'NQMAIN'}
    symbols = sorted([s for s in stock_info if s not in INDEX_SYMBOLS])

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "periods": list(PERIODS),
        "stocks": {},
    }

    total = len(symbols)
    for i, sym in enumerate(symbols):
        info = stock_info[sym]
        history = load_history(sym)

        if not history or len(history) < 60:
            output["stocks"][sym] = {
                "name": info["name"],
                "sector": info["sector"],
                "close": info["close"],
                "periods": {},
            }
            print(f"[{i+1}/{total}] {sym} — SKIP ({len(history) if history else 0} days)")
            continue

        metrics_all = compute_intraday_metrics(history)

        periods_data = {}
        for period in PERIODS:
            subset = metrics_all[-period:] if len(metrics_all) >= period else metrics_all
            periods_data[str(period)] = compute_stats(subset, info["close"])

        output["stocks"][sym] = {
            "name": info["name"],
            "sector": info["sector"],
            "close": info["close"],
            "periods": periods_data,
        }

        p300 = periods_data.get("300", {})
        up_info = p300.get("up", {})
        down_info = p300.get("down", {})
        print(f"[{i+1}/{total}] {sym:<6} {info['name']:<8}  "
              f"UP P50={up_info.get('p50', 0):+.1f}%  "
              f"DOWN P50={down_info.get('p50', 0):+.1f}%  "
              f"(up_n={up_info.get('n','?')} down_n={down_info.get('n','?')})")

    # Save output
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {len(output['stocks'])} stocks → {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    run()
