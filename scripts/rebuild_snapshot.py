#!/usr/bin/env python3
"""Rebuild stocks.json from existing history files without network fetch."""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
STOCKS_FILE = DATA_DIR / "stocks.json"

# Load existing stocks.json for metadata
with open(STOCKS_FILE, encoding='utf-8') as f:
    existing = json.load(f)
existing_map = {s['symbol']: s for s in existing['stocks']}

stocks = []

for hist_file in sorted(HISTORY_DIR.glob('*.json')):
    symbol = hist_file.stem
    with open(hist_file) as f:
        data = json.load(f)
    if not data:
        print(f"  SKIP {symbol}: empty history")
        continue

    df = pd.DataFrame(data)

    # Normalize columns from history format
    # Handle date separately (it's a string, not numeric)
    df['Date'] = pd.to_datetime(df['date'])

    numeric_cols = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
    for old_col, new_col in numeric_cols.items():
        if old_col in df.columns:
            df[new_col] = pd.to_numeric(df[old_col], errors='coerce')

    df = df.set_index('Date').sort_index()
    df = df[~df.index.duplicated(keep='last')]

    if len(df) < 5:
        print(f"  SKIP {symbol}: only {len(df)} rows")
        continue

    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # MA
    df['MA5'] = close.rolling(5).mean()
    df['MA20'] = close.rolling(20).mean()

    # KDJ
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
            k_vals[i] = 2/3 * last_k + 1/3 * rsv.iloc[i]
            d_vals[i] = 2/3 * last_d + 1/3 * k_vals[i]
            last_k = k_vals[i]
            last_d = d_vals[i]

    df['K'] = k_vals
    df['D'] = d_vals
    df['J'] = 3 * k_vals - 2 * d_vals

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    avg_vol = float(df['Volume'].tail(20).mean()) if 'Volume' in df.columns and len(df) >= 5 else 0

    meta = existing_map.get(symbol, {})

    # Signal detection
    k = float(latest['K'])
    d = float(latest['D'])
    j = float(latest['J'])
    close_p = float(latest['Close'])
    ma5 = float(latest['MA5'])
    ma20 = float(latest['MA20'])

    kdj_oversold = k < 20
    kdj_overbought = k > 80
    kdj_golden = k > d
    kdj_death = k < d
    kdj_j_bottom = j < 0
    ma_above5 = close_p > ma5
    ma_above20 = close_p > ma20
    ma5_above20 = ma5 > ma20

    signal = None
    signal_strength = None

    if kdj_oversold and kdj_golden and ma_above5:
        signal, signal_strength = 'buy', 'strong'
    elif kdj_golden and ma_above5 and ma5_above20:
        signal, signal_strength = 'buy', 'mild'
    elif kdj_golden or (k > 70 and not kdj_overbought):
        signal, signal_strength = 'watch', None
    elif kdj_overbought and kdj_death and not ma_above5:
        signal, signal_strength = 'sell', 'strong'
    elif kdj_death and not ma_above5 and not ma5_above20:
        signal, signal_strength = 'sell', 'mild'
    elif kdj_j_bottom:
        signal, signal_strength = 'watch', None

    change_pct = round(float(latest['Close'] - prev['Close']) / float(prev['Close']) * 100, 2)

    stock = {
        'symbol': symbol,
        'name': meta.get('name', symbol),
        'sector': meta.get('sector', 'Other'),
        'market_cap': meta.get('market_cap', 0),
        'prev_close': round(float(prev['Close']), 2),
        'open': round(float(latest['Open']), 2),
        'high': round(float(latest['High']), 2),
        'low': round(float(latest['Low']), 2),
        'close': round(float(latest['Close']), 2),
        'volume': int(latest['Volume']),
        'vwap': round(float(latest['Close']), 2),
        'avg_volume': int(avg_vol),
        'change_pct': change_pct,
        'ma5': round(float(ma5), 2),
        'ma20': round(float(ma20), 2),
        'k': round(float(k), 1),
        'd': round(float(d), 1),
        'j': round(float(j), 1),
        'signal': signal,
        'signal_strength': signal_strength,
    }
    stocks.append(stock)
    print(f"  {symbol:<6}: close=${stock['close']:.2f}  change={change_pct:+.2f}%  signal={signal or '-'}  date={latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)[:10]}")

stocks.sort(key=lambda s: s.get('market_cap', 0), reverse=True)

data_date = datetime.now().strftime('%Y-%m-%d')
snapshot = {
    'updated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'data_date': data_date,
    'stocks': stocks,
}

with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)

print(f"\nRebuilt stocks.json: {len(stocks)} stocks, data_date={data_date}")
