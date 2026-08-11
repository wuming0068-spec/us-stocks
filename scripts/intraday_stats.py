#!/usr/bin/env python3
"""
intraday_stats.py — Compute intraday volatility statistics for options swing trading.
=====================================================================================
Reads per-stock history from docs/data/history/*.json, computes for 300/200/100/60
trading-day periods:
  - Average intraday highest gain  (high vs prev_close)
  - Average intraday lowest drop   (low vs prev_close)
  - Average intraday swing range   (high-low vs prev_close)
  - 1σ / 2σ / 3σ price points for each metric
  - Empirical exceedance % at each sigma level

Output: docs/data/intraday_stats.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
STOCKS_FILE = DATA_DIR / "stocks.json"
OUTPUT_FILE = DATA_DIR / "intraday_stats.json"

PERIODS = [300, 200, 100, 60]
SIGMAS = [1, 2, 3]


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
    # Ensure sorted by date
    data.sort(key=lambda r: r.get("date", ""))
    return data


def compute_intraday_metrics(history: list[dict]) -> list[dict]:
    """Compute daily intraday metrics from OHLCV data.
    Each day: up_move = (high - prev_close) / prev_close
              down_move = (low - prev_close) / prev_close
              swing = (high - low) / prev_close
    Returns list of dicts with date, up_move_pct, down_move_pct, swing_pct.
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
        up_move = (high - prev_close) / prev_close * 100
        down_move = (low - prev_close) / prev_close * 100
        swing = (high - low) / prev_close * 100
        results.append({
            "date": curr.get("date", ""),
            "up_move_pct": round(up_move, 4),
            "down_move_pct": round(down_move, 4),
            "swing_pct": round(swing, 4),
        })
    return results


def compute_stats(metrics: list[dict], close: float) -> dict:
    """Compute mean, std, sigma price points and exceedance % for a set of metrics."""

    up = np.array([m["up_move_pct"] for m in metrics])
    down = np.array([m["down_move_pct"] for m in metrics])
    swing = np.array([m["swing_pct"] for m in metrics])

    def stats_for(arr: np.ndarray, is_down: bool = False) -> dict:
        """Compute stats for one metric array.
        is_down=True for down_move (negative values, lower means more extreme).
        """
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))  # sample std
        n = len(arr)

        result = {"mean": round(mean, 2), "std": round(std, 2), "n": n}

        for s in SIGMAS:
            key = f"sigma_{s}"
            if is_down:
                # down_move: more negative = more extreme
                target_pct = mean - s * std
            else:
                # up_move / swing: more positive = more extreme
                target_pct = mean + s * std

            price = round(close * (1 + target_pct / 100), 2)

            if is_down:
                exceed_count = int(np.sum(arr < target_pct))
            else:
                exceed_count = int(np.sum(arr > target_pct))

            exceed_pct = round(exceed_count / n * 100, 1) if n > 0 else 0

            result[key] = {
                "pct": round(target_pct, 2),
                "price": price,
                "exceed_pct": exceed_pct,
            }

        return result

    return {
        "up": stats_for(up, is_down=False),
        "down": stats_for(down, is_down=True),
        "swing": stats_for(swing, is_down=False),
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
            # Not enough history — include with null stats
            output["stocks"][sym] = {
                "name": info["name"],
                "sector": info["sector"],
                "close": info["close"],
                "periods": {},
            }
            print(f"[{i+1}/{total}] {sym} — SKIP (not enough history: {len(history) if history else 0} days)")
            continue

        metrics_all = compute_intraday_metrics(history)

        periods_data = {}
        for period in PERIODS:
            if len(metrics_all) >= period:
                subset = metrics_all[-period:]
                periods_data[str(period)] = compute_stats(subset, info["close"])
            else:
                # Use all available
                periods_data[str(period)] = compute_stats(metrics_all, info["close"])

        output["stocks"][sym] = {
            "name": info["name"],
            "sector": info["sector"],
            "close": info["close"],
            "periods": periods_data,
        }

        # Print summary
        p300 = periods_data.get("300", periods_data.get("60", {}))
        up_info = p300.get("up", {})
        down_info = p300.get("down", {})
        print(f"[{i+1}/{total}] {sym:<6} {info['name']:<8} "
              f"↑{up_info.get('mean', 0):.1f}%±{up_info.get('std', 0):.1f}%  "
              f"↓{down_info.get('mean', 0):.1f}%±{down_info.get('std', 0):.1f}%")

    # Save output
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {len(output['stocks'])} stocks → {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    run()
