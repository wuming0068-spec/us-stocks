#!/usr/bin/env python3
"""
fetch_data_v2.py — US Stock data: Sina Finance (OHLCV) + East Money (market caps)
=================================================================================
Primary OHLCV source: Sina Finance (国内直连, no API key)
Market cap source:   East Money ulist API (批量获取市值)
Name/Sector:         Built-in mapping

Usage:
  python scripts/fetch_data_v2.py              # fetch all watchlist stocks
  python scripts/fetch_data_v2.py --symbol AAPL # fetch single stock
  python scripts/fetch_data_v2.py --days 120    # override history depth
  python scripts/fetch_data_v2.py --no-mcap     # skip market cap fetching
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests

# --- Paths ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
STOCKS_FILE = DATA_DIR / "stocks.json"

DEFAULT_HISTORY_DAYS = 120
MCAP_BATCH_SIZE = 25  # East Money ulist max per request

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fetch_v2")

# ---------------------------------------------------------------------------
# HTTP session with retry
# ---------------------------------------------------------------------------
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
})

# ---------------------------------------------------------------------------
# Name & Sector mapping (built-in, no network needed)
# ---------------------------------------------------------------------------
STOCK_META = {
    # 芯片 (Semiconductors)
    "NVDA": ("英伟达", "芯片"), "AMD": ("AMD", "芯片"), "INTC": ("英特尔", "芯片"),
    "AVGO": ("博通", "芯片"), "TSM": ("台积电", "芯片"), "TXN": ("德州仪器", "芯片"),
    "QCOM": ("高通", "芯片"), "MU": ("美光", "芯片"), "AMAT": ("应用材料", "芯片"),
    "LRCX": ("拉姆研究", "芯片"), "KLAC": ("科磊", "芯片"), "ADI": ("ADI", "芯片"),
    "MRVL": ("迈威尔", "芯片"), "SNPS": ("新思科技", "芯片"), "CDNS": ("楷登电子", "芯片"),
    "MPWR": ("MPWR", "芯片"), "NXPI": ("恩智浦", "芯片"), "ON": ("安森美", "芯片"),
    "MCHP": ("微芯科技", "芯片"),
    # 光模块 (Optical / Interconnect)
    "AAOI": ("应用光电", "光模块"), "LITE": ("Lumentum", "光模块"),
    "COHR": ("Coherent", "光模块"), "CIEN": ("Ciena", "光模块"),
    "FN": ("Fabrinet", "光模块"), "CLS": ("Celestica", "光模块"),
    "JBL": ("捷普", "光模块"), "CRDO": ("Credo", "光模块"),
    "VIAV": ("Viavi", "光模块"), "IPGP": ("IPG光子", "光模块"),
    "FORM": ("FormFactor", "光模块"), "AEHR": ("AEHR", "光模块"),
    "TSEM": ("Tower Semi", "光模块"), "AXTI": ("AXT", "光模块"),
    "POET": ("POET", "光模块"), "LWLG": ("Lightwave", "光模块"),
    "ALAB": ("Astera Labs", "光模块"),
    # 存储 (Storage / Memory)
    "SNDK": ("闪迪", "存储"), "WDC": ("西部数据", "存储"), "STX": ("希捷", "存储"),
    "NTAP": ("NetApp", "存储"), "SIMO": ("慧荣科技", "存储"),
    "RMBS": ("Rambus", "存储"), "ALMU": ("Aeluma", "存储"),
    "PSTG": ("Pure Storage", "存储"),
    # 科技 (Big Tech)
    "AAPL": ("苹果", "科技"), "MSFT": ("微软", "科技"), "GOOGL": ("谷歌", "科技"),
    "AMZN": ("亚马逊", "科技"), "META": ("Meta", "科技"), "TSLA": ("特斯拉", "科技"),
    # 储能 (Energy / Renewables)
    "FLNC": ("Fluence", "储能"), "NEE": ("新纪元能源", "储能"),
    "ENPH": ("Enphase", "储能"), "GEV": ("GE Vernova", "储能"),
    "STEM": ("Stem Inc", "储能"), "VRT": ("Vertiv", "储能"),
    "BE": ("Bloom Energy", "储能"), "EOSE": ("Eos Energy", "储能"),
    "NRGV": ("Energy Vault", "储能"), "ETN": ("伊顿", "储能"),
    "VST": ("Vistra", "储能"), "ALB": ("雅保", "储能"),
    "GWH": ("ESS Tech", "储能"), "GNRC": ("Generac", "储能"),
    "SEDG": ("SolarEdge", "储能"), "CSIQ": ("阿特斯", "储能"),
    "QS": ("QuantumScape", "储能"), "ADSE": ("ADS-TEC", "储能"),
    "FCX": ("自由港", "储能"),
    # 大盘 (Broad Market ETFs)
    "QQQ": ("纳指100ETF", "大盘"), "QQQM": ("纳指100ETF", "大盘"),
    "TQQQ": ("纳指3倍做多", "大盘"), "SQQQ": ("纳指3倍做空", "大盘"),
    "SOXL": ("半导体3倍做多", "大盘"), "SOXS": ("半导体3倍做空", "大盘"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default=None):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: Path, data):
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Sina Finance — OHLCV
# ---------------------------------------------------------------------------
SINA_KLINE_URL = (
    "https://stock.finance.sina.com.cn/usstock/api/json_v2.php/"
    "US_MinKService.getDailyK?symbol={symbol}&type=daily&num={num}"
)


def fetch_sina_kline(symbol: str, num: int = 300) -> pd.DataFrame | None:
    """Fetch daily OHLCV from Sina Finance."""
    url = SINA_KLINE_URL.format(symbol=symbol.upper(), num=num)
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                log.warning(f"  Sina HTTP {resp.status_code} for {symbol}")
                if attempt < 2:
                    time.sleep(2)
                continue
            data = resp.json()
            if not isinstance(data, list) or len(data) == 0:
                log.warning(f"  Sina empty data for {symbol}")
                return None

            rows = []
            for r in data:
                try:
                    rows.append({
                        "Date": pd.to_datetime(r["d"]),
                        "Open": float(r["o"]),
                        "High": float(r["h"]),
                        "Low": float(r["l"]),
                        "Close": float(r["c"]),
                        "Volume": int(r["v"]),
                    })
                except (KeyError, ValueError, TypeError):
                    continue

            if not rows:
                return None

            df = pd.DataFrame(rows)
            df = df.set_index("Date").sort_index()
            df = df[~df.index.duplicated(keep="last")]
            return df

        except requests.RequestException as e:
            log.warning(f"  Sina request failed for {symbol}: {e}")
            if attempt < 2:
                time.sleep(3)
        except Exception as e:
            log.warning(f"  Sina parse failed for {symbol}: {e}")
            return None
    return None


# ---------------------------------------------------------------------------
# East Money — Market Caps
# ---------------------------------------------------------------------------
EASTMONEY_ULIST_URL = "https://push2.eastmoney.com/api/qt/ulist/get"


def fetch_market_caps(symbols: list[str], batch_size: int = MCAP_BATCH_SIZE) -> dict:
    """Fetch market caps from East Money ulist API.
    Tries market code 105 (NASDAQ/NYSE) first, then 106 (NYSE/other) for failures.
    Returns dict of {symbol: market_cap_int}.
    """
    result = {}
    remaining = list(symbols)
    first_pass = True

    for market_code in ("105", "106"):
        if not remaining:
            break
        to_fetch = list(remaining)
        remaining = []

        for i in range(0, len(to_fetch), batch_size):
            batch = to_fetch[i:i + batch_size]
            secids = ",".join(f"{market_code}.{s}" for s in batch)
            params = {
                "fltt": 1, "invt": 2,
                "fields": "f12,f20",
                "secids": secids,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "pn": 1, "np": 1, "pz": len(batch),
                "dect": 1, "wbp2u": "|0|0|0|web",
            }
            url = f"{EASTMONEY_ULIST_URL}?{urlencode(params)}"

            try:
                resp = session.get(url, timeout=10)
                if resp.status_code != 200:
                    log.warning(f"  East Money HTTP {resp.status_code} for batch {i}")
                    if first_pass:
                        remaining.extend(batch)
                    continue
                data = resp.json()
                diffs = data.get("data", {}).get("diff") or []
                got = set()
                for d in diffs:
                    sym = d.get("f12", "").upper()
                    mcap = d.get("f20", 0)
                    if sym and mcap and str(mcap) != "-":
                        result[sym] = int(mcap)
                        got.add(sym)
                missed = [s for s in batch if s not in got]
                if first_pass and missed:
                    remaining.extend(missed)
                log.info(f"  MCAP batch {i//batch_size+1}: {len(got)} OK, {len(missed)} missed (market={market_code})")
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"  East Money failed for batch {i}: {e}")
                if first_pass:
                    remaining.extend(batch)
        first_pass = False

    # Fill in zeros for known ETFs
    for sym in ("QQQ", "QQQM", "TQQQ", "SQQQ", "SOXL", "SOXS"):
        if sym in symbols and sym not in result:
            result[sym] = 0

    return result


# ---------------------------------------------------------------------------
# Indicator computation
# ---------------------------------------------------------------------------
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 5:
        return df
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    df["MA5"] = close.rolling(5).mean()
    df["MA20"] = close.rolling(20).mean()
    n = 9
    low_min = low.rolling(n).min()
    high_max = high.rolling(n).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    k_vals = np.full(len(df), np.nan)
    d_vals = np.full(len(df), np.nan)
    last_k = 50.0
    last_d = 50.0
    for i in range(len(df)):
        if i < n or pd.isna(rsv.iloc[i]):
            k_vals[i] = last_k
            d_vals[i] = last_d
        else:
            k_vals[i] = 2 / 3 * last_k + 1 / 3 * rsv.iloc[i]
            d_vals[i] = 2 / 3 * last_d + 1 / 3 * k_vals[i]
            last_k = k_vals[i]
            last_d = d_vals[i]
    df["K"] = k_vals
    df["D"] = d_vals
    df["J"] = 3 * k_vals - 2 * d_vals
    return df


def detect_signal(row: pd.Series) -> dict:
    k = row.get("K", 50)
    d = row.get("D", 50)
    j = row.get("J", 50)
    close = row.get("Close", 0)
    ma5 = row.get("MA5", close)
    ma20 = row.get("MA20", close)
    kdj = {
        "kOversold": k < 20, "kOverbought": k > 80,
        "goldenCross": k > d, "deathCross": k < d, "jBottom": j < 0,
    }
    ma = {
        "priceAboveMA5": close > ma5, "priceAboveMA20": close > ma20,
        "ma5AboveMA20": ma5 > ma20,
    }
    if kdj["kOversold"] and kdj["goldenCross"] and ma["priceAboveMA5"]:
        return {"signal": "buy", "signal_strength": "strong"}
    if kdj["goldenCross"] and ma["priceAboveMA5"] and ma["ma5AboveMA20"]:
        return {"signal": "buy", "signal_strength": "mild"}
    if kdj["goldenCross"] or (k > 70 and not kdj["kOverbought"]):
        return {"signal": "watch", "signal_strength": None}
    if kdj["kOverbought"] and kdj["deathCross"] and not ma["priceAboveMA5"]:
        return {"signal": "sell", "signal_strength": "strong"}
    if kdj["deathCross"] and not ma["priceAboveMA5"] and not ma["ma5AboveMA20"]:
        return {"signal": "sell", "signal_strength": "mild"}
    if kdj["jBottom"]:
        return {"signal": "watch", "signal_strength": None}
    return {"signal": None, "signal_strength": None}


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------
def load_history(symbol: str) -> pd.DataFrame | None:
    hist_file = HISTORY_DIR / f"{symbol}.json"
    data = load_json(hist_file)
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    try:
        df = pd.DataFrame(data)
        df["Date"] = pd.to_datetime(df["date"] if "date" in df.columns else df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return None


def save_history(symbol: str, df: pd.DataFrame, history_days: int):
    existing = load_history(symbol)
    if existing is not None and len(existing) > 0:
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep="last")]
    else:
        combined = df
    combined = combined.sort_index().tail(history_days)
    records = []
    for idx, row in combined.iterrows():
        records.append({
            "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10],
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    ensure_dir(HISTORY_DIR)
    save_json(HISTORY_DIR / f"{symbol}.json", records)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
def generate_snapshot(all_data: dict, mcap_overrides: dict | None = None) -> dict:
    """Generate stocks.json from fetched data."""
    stocks = []
    existing = load_json(STOCKS_FILE, {"stocks": []})
    existing_map = {s.get("symbol", "").upper(): s for s in existing.get("stocks", [])}

    for symbol, info in all_data.items():
        df = info.get("df")
        if df is None or len(df) == 0:
            if symbol in existing_map:
                stocks.append(existing_map[symbol])
            continue

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        # Metadata: prefer built-in mapping > existing > fallback
        meta = STOCK_META.get(symbol, (None, None))
        name = meta[0] or existing_map.get(symbol, {}).get("name", symbol)
        sector = meta[1] or existing_map.get(symbol, {}).get("sector", "其他")

        # Market cap: override > existing
        mcap = 0
        if mcap_overrides and symbol in mcap_overrides:
            mcap = mcap_overrides[symbol]
        elif symbol in existing_map:
            mcap = existing_map[symbol].get("market_cap", 0)

        avg_vol = float(df["Volume"].tail(20).mean()) if len(df) >= 5 else 0
        signal = detect_signal(latest)

        stock = {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "market_cap": int(mcap) if mcap else 0,
            "prev_close": round(float(prev["Close"]), 2),
            "open": round(float(latest["Open"]), 2),
            "high": round(float(latest["High"]), 2),
            "low": round(float(latest["Low"]), 2),
            "close": round(float(latest["Close"]), 2),
            "volume": int(latest["Volume"]),
            "vwap": round(float(latest["Close"]), 2),
            "avg_volume": int(avg_vol),
            "change_pct": round(
                float(latest["Close"] - prev["Close"]) / float(prev["Close"]) * 100, 2
            ),
            "ma5": round(float(latest.get("MA5", latest["Close"])), 2),
            "ma20": round(float(latest.get("MA20", latest["Close"])), 2),
            "k": round(float(latest.get("K", 50)), 1),
            "d": round(float(latest.get("D", 50)), 1),
            "j": round(float(latest.get("J", 50)), 1),
            "signal": signal["signal"],
            "signal_strength": signal["signal_strength"],
        }
        stocks.append(stock)

    stocks.sort(key=lambda s: s.get("market_cap", 0), reverse=True)

    # Determine actual data date from latest row across all data
    data_dates = []
    for info in all_data.values():
        df = info.get("df")
        if df is not None and len(df) > 0:
            data_dates.append(df.index.max())
    data_date = max(data_dates).strftime("%Y-%m-%d") if data_dates else datetime.now().strftime("%Y-%m-%d")

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "data_date": data_date,
        "stocks": stocks,
    }


def load_watchlist() -> list:
    """Load symbols from stocks.json, falling back to history files on disk."""
    data = load_json(STOCKS_FILE, {"stocks": []})
    symbols = []
    for s in data.get("stocks", []):
        sym = s.get("symbol", "").strip().upper()
        if sym:
            symbols.append(sym)

    # If stocks.json has few entries, discover from history files
    if len(symbols) < 30 and HISTORY_DIR.exists():
        history_syms = sorted([
            f.stem.upper() for f in HISTORY_DIR.glob("*.json")
            if f.stem.upper() not in {".SOX", ".NDX", ".IXIC", "NQMAIN"}
        ])
        existing_set = set(symbols)
        for s in history_syms:
            if s not in existing_set:
                symbols.append(s)
        log.info(f"Watchlist expanded: {len(symbols)} symbols (from stocks.json + history)")

    return symbols if symbols else ["AAPL", "NVDA", "MSFT"]


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run(symbols: list[str] | None = None, history_days: int = DEFAULT_HISTORY_DAYS,
        no_mcap: bool = False):
    if symbols is None:
        symbols = load_watchlist()

    # Filter out index symbols
    INDEX_SYMBOLS = {'.SOX', '.NDX', '.IXIC', 'NQMAIN'}
    symbols = [s.upper() for s in symbols if s.strip().upper() not in INDEX_SYMBOLS]

    existing = load_json(STOCKS_FILE, {"stocks": []})
    existing_map = {}
    for s in existing.get("stocks", []):
        sym = s.get("symbol", "").upper()
        if sym:
            existing_map[sym] = s

    all_data = {}
    for sym in set(list(existing_map.keys()) + symbols):
        meta = STOCK_META.get(sym, (sym, "其他"))
        all_data[sym] = {
            "df": None,
            "name": meta[0],
            "sector": meta[1],
            "market_cap": existing_map.get(sym, {}).get("market_cap", 0),
        }

    success = 0
    fail = 0
    total = len(symbols)

    # ---- Phase 1: Fetch OHLCV from Sina ----
    log.info(f"Phase 1: Fetching OHLCV for {total} symbols from Sina Finance...")
    for i, sym in enumerate(symbols):
        log.info(f"[{i+1}/{total}] {sym} ...")
        df = fetch_sina_kline(sym, num=history_days * 2)
        if df is not None and len(df) >= 5:
            df = compute_indicators(df)
            df = df.tail(history_days)
            save_history(sym, df, history_days)
            all_data[sym] = {
                "df": df,
                "name": STOCK_META.get(sym, (sym, "其他"))[0],
                "sector": STOCK_META.get(sym, (sym, "其他"))[1],
                "market_cap": existing_map.get(sym, {}).get("market_cap", 0),
            }
            success += 1
            latest = df.iloc[-1]
            log.info(f"  OK: {len(df)} rows, close={latest['Close']:.2f} ({latest.name.date()})")
        else:
            fail += 1
            log.warning(f"  FAILED: no data")
        time.sleep(0.15)

    log.info(f"OHLCV complete: {success} OK, {fail} failed")

    # ---- Phase 2: Fetch market caps ----
    mcap_overrides = {}
    if not no_mcap:
        need_mcap = [s for s in all_data if all_data[s]["market_cap"] == 0]
        if need_mcap:
            log.info(f"Phase 2: Fetching market caps for {len(need_mcap)} stocks...")
            mcap_overrides = fetch_market_caps(need_mcap)
            updated = 0
            for sym, mcap in mcap_overrides.items():
                if sym in all_data:
                    all_data[sym]["market_cap"] = mcap
                    updated += 1
            log.info(f"Market caps: {updated} updated, {len(need_mcap) - updated} missed")
        else:
            # All already have market caps from existing data
            mcap_overrides = {}
    else:
        log.info("Phase 2: Market caps skipped (--no-mcap)")

    # ---- Generate snapshot ----
    snapshot = generate_snapshot(all_data, mcap_overrides)

    # Keep only stocks with valid data (close > 0)
    snapshot["stocks"] = [s for s in snapshot["stocks"] if s.get("close", 0) > 0]

    save_json(STOCKS_FILE, snapshot)
    log.info(f"Snapshot saved: {len(snapshot['stocks'])} stocks to {STOCKS_FILE}")

    # ---- Print summary ----
    print()
    print("=" * 70)
    print(f"  Snapshot: {len(snapshot['stocks'])} stocks  |  {snapshot['updated_at']}")
    print(f"  Data date: {snapshot['data_date']}")
    print("=" * 70)
    for s in snapshot["stocks"]:
        chg = s["change_pct"]
        chg_s = f"+{chg:.2f}%" if chg > 0 else f"{chg:.2f}%"
        sig = s.get("signal") or "-"
        mcap_s = f"${s['market_cap']/1e12:.2f}T" if s['market_cap'] >= 1e12 else f"${s['market_cap']/1e9:.1f}B" if s['market_cap'] >= 1e9 else f"${s['market_cap']/1e6:.0f}M" if s['market_cap'] >= 1e6 else ""
        print(f"  {s['symbol']:<6} {s['name']:<8}  ${s['close']:<10.2f} {chg_s:>8}  {sig:<5}  [{s['sector']}] {mcap_s}")

    return snapshot


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="US Stocks Data Fetcher v2 (Sina + East Money)")
    parser.add_argument("--symbol", type=str, help="Fetch a single symbol only")
    parser.add_argument("--days", type=int, default=DEFAULT_HISTORY_DAYS, help="History depth")
    parser.add_argument("--no-mcap", action="store_true", help="Skip market cap fetching")
    args = parser.parse_args()

    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        symbols = load_watchlist()

    run(symbols, history_days=args.days, no_mcap=args.no_mcap)


if __name__ == "__main__":
    main()
