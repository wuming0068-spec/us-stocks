"""
fetch_and_calc.py
Daily US stocks data fetcher.
Fetches daily OHLCV data for watchlist symbols via akshare,
calculates MA5/MA20/KDJ indicators, outputs docs/data/stocks.json.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("Error: akshare not installed. Run: pip install akshare pandas numpy")
    sys.exit(1)

# === Config ===
OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "data", "stocks.json"
)
WATCHLIST_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "watchlist.txt"
)

# Default watchlist (used if watchlist.txt doesn't exist)
DEFAULT_WATCHLIST = [
    "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META",
    "JPM", "BAC", "GS", "JNJ", "PFE", "UNH", "NEE", "XOM"
]

# Stock name mapping (akshare might need help with some symbols)
STOCK_NAMES = {}

# Sector mapping (fallback only — frontend allows user-defined industries
# stored in localStorage. These values are overridden by user settings in the UI.)
SECTORS = {
    "AAPL": "科技", "NVDA": "科技", "MSFT": "科技", "GOOGL": "科技",
    "AMZN": "科技", "TSLA": "科技", "META": "科技", "NFLX": "科技",
    "ADBE": "科技", "CRM": "科技", "AMD": "科技", "INTC": "科技",
    "JPM": "金融", "BAC": "金融", "GS": "金融", "MS": "金融",
    "WFC": "金融", "C": "金融", "V": "金融", "MA": "金融",
    "JNJ": "医疗", "PFE": "医疗", "UNH": "医疗", "MRK": "医疗",
    "ABBV": "医疗", "LLY": "医疗", "TMO": "医疗",
    "NEE": "能源", "XOM": "能源", "CVX": "能源", "COP": "能源",
    "SLB": "能源", "EOG": "能源",
    "AMZN": "科技", "TSLA": "科技", "COST": "消费", "WMT": "消费",
    "HD": "消费", "MCD": "消费", "NKE": "消费", "SBUX": "消费",
    "BA": "工业", "CAT": "工业", "GE": "工业", "HON": "工业",
    "T": "通讯", "VZ": "通讯", "DIS": "通讯",
}


def load_watchlist():
    """Load watchlist from file or use default."""
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            symbols = [
                line.strip().upper()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
            if symbols:
                return symbols
    return DEFAULT_WATCHLIST


def fetch_stock_data(symbol):
    """Fetch daily OHLCV data for a single US stock via akshare."""
    # akshare uses "105.AAPL" format for US stocks
    akshare_symbol = f"105.{symbol}"

    # Calculate date range: need at least 30 trading days for MA20 calc
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

    for attempt in range(3):
        try:
            df = ak.stock_us_hist(
                symbol=akshare_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
            if df is not None and len(df) > 20:
                return df
            print(f"  Attempt {attempt+1}: not enough data ({len(df) if df is not None else 0} rows), retrying...")
        except Exception as e:
            print(f"  Attempt {attempt+1}: {type(e).__name__}: {e}")
            time.sleep(3)

    return None


def clean_and_standardize(df):
    """Rename columns and standardize data format."""
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    # Handle English column names (some akshare versions return English)
    df = df.rename(columns={
        "Date": "date", "Open": "open", "Close": "close",
        "High": "high", "Low": "low", "Volume": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "close", "high", "low", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def calculate_indicators(df):
    """Calculate MA5, MA20, and KDJ indicators."""
    # Moving averages
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma20"] = df["close"].rolling(20).mean()

    # KDJ (n=9)
    n = 9
    low_min = df["low"].rolling(n).min()
    high_max = df["high"].rolling(n).max()
    rsv = (df["close"] - low_min) / (high_max - low_min) * 100

    k_vals = np.zeros(len(df))
    d_vals = np.zeros(len(df))

    for i in range(len(df)):
        if i < n or pd.isna(rsv.iloc[i]):
            k_vals[i] = 50.0
            d_vals[i] = 50.0
        else:
            k_vals[i] = 2/3 * k_vals[i-1] + 1/3 * rsv.iloc[i]
            d_vals[i] = 2/3 * d_vals[i-1] + 1/3 * k_vals[i]

    df["k"] = k_vals
    df["d"] = d_vals
    df["j"] = 3 * k_vals - 2 * d_vals

    return df


def extract_latest_data(df, symbol):
    """Extract the latest trading day's data plus calculated indicators."""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    # Calculate VWAP approximation: (high + low + close) / 3 * volume / volume
    # That's just average price. For true VWAP we'd need tick data.
    vwap = round((latest["high"] + latest["low"] + latest["close"]) / 3, 2)
    prev_close = prev["close"]

    change_pct = round((latest["close"] - prev_close) / prev_close * 100, 2)

    return {
        "symbol": symbol,
        "name": STOCK_NAMES.get(symbol, ""),
        "sector": SECTORS.get(symbol, "其他"),
        "market_cap": 0,  # Will need separate source for market cap
        "prev_close": round(float(prev_close), 2),
        "open": round(float(latest["open"]), 2),
        "high": round(float(latest["high"]), 2),
        "low": round(float(latest["low"]), 2),
        "close": round(float(latest["close"]), 2),
        "volume": int(latest["volume"]) if not pd.isna(latest["volume"]) else 0,
        "vwap": vwap,
        "change_pct": change_pct,
        "ma5": round(float(latest["ma5"]), 2) if not pd.isna(latest["ma5"]) else None,
        "ma20": round(float(latest["ma20"]), 2) if not pd.isna(latest["ma20"]) else None,
        "k": round(float(latest["k"]), 1) if not pd.isna(latest["k"]) else None,
        "d": round(float(latest["d"]), 1) if not pd.isna(latest["d"]) else None,
        "j": round(float(latest["j"]), 1) if not pd.isna(latest["j"]) else None,
        "signal": None,
        "signal_strength": None,
    }


def main():
    print("=" * 60)
    print("US Stocks Monitor — Daily Data Fetcher")
    print(f"Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    symbols = load_watchlist()
    print(f"\nWatchlist: {len(symbols)} symbols")
    print(f"Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    stocks = []
    success = 0
    fail = 0

    for i, symbol in enumerate(symbols):
        print(f"\n[{i+1}/{len(symbols)}] {symbol} ...")
        df = fetch_stock_data(symbol)

        if df is None or len(df) < 20:
            print(f"  FAILED: insufficient data for {symbol}")
            fail += 1
            continue

        df = clean_and_standardize(df)
        df = calculate_indicators(df)

        try:
            stock_data = extract_latest_data(df, symbol)
            stocks.append(stock_data)
            print(f"  OK: close=${stock_data['close']:.2f} change={stock_data['change_pct']:+.2f}%")
            success += 1
        except Exception as e:
            print(f"  ERROR extracting data: {e}")
            fail += 1

        # Rate limiting
        if i < len(symbols) - 1:
            time.sleep(1)

    print(f"\nDone. Success: {success}, Failed: {fail}")

    # Build output
    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "data_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "stocks": stocks,
    }

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput written to: {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH):,} bytes")
    print(f"Stock count: {len(stocks)}")


if __name__ == "__main__":
    main()
