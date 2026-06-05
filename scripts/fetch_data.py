#!/usr/bin/env python3
"""
fetch_data.py — US Stocks Data Pipeline
========================================
Primary:   AKShare (新浪/东财, 国内直连)
Fallback:  efinance (东方财富, GitHub Actions 可用)
Fallback:  yfinance (Yahoo Finance API)
Fallback:  Playwright → Yahoo Finance page scrape

Usage:
  python scripts/fetch_data.py              # fetch all watchlist stocks
  python scripts/fetch_data.py --symbol AAPL # fetch single stock
  python scripts/fetch_data.py --days 120    # override history depth
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# --- Paths ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "docs" / "data"
HISTORY_DIR = DATA_DIR / "history"
STOCKS_FILE = DATA_DIR / "stocks.json"

# Default history depth (trading days)
DEFAULT_HISTORY_DAYS = 120

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fetch")


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


def fmt_price(p) -> str:
    return f"{p:.2f}"


# ---------------------------------------------------------------------------
# DataFetcher
# ---------------------------------------------------------------------------

class DataFetcher:
    def __init__(self, history_days: int = DEFAULT_HISTORY_DAYS):
        self.history_days = history_days
        self.end_date = datetime.now().strftime("%Y%m%d")
        self.start_date = (datetime.now() - timedelta(days=history_days * 2)).strftime("%Y%m%d")
        self.akshare_ok = False
        self.efinance_ok = False
        self._init_akshare()
        self._init_efinance()

    # ----- akshare init -----
    def _init_akshare(self):
        """Try to import akshare."""
        try:
            import akshare as ak
            self.ak = ak
            self.akshare_ok = True
            log.info("akshare loaded successfully")
        except ImportError:
            log.warning("akshare not installed")
            self.ak = None
            self.akshare_ok = False
        except Exception as e:
            log.warning(f"akshare init failed: {e}")
            self.ak = None
            self.akshare_ok = False

    # ----- efinance init -----
    def _init_efinance(self):
        """Try to import and warm up efinance."""
        try:
            os.environ.setdefault('no_proxy', 'eastmoney.com,push2his.eastmoney.com,127.0.0.1,localhost')
            import efinance as ef
            self.ef = ef
            self.efinance_ok = True
            log.info("efinance loaded successfully")
        except ImportError:
            log.warning("efinance not installed")
            self.ef = None
            self.efinance_ok = False
        except Exception as e:
            log.warning(f"efinance init failed: {e}")
            self.ef = None
            self.efinance_ok = False

    # ----- Watchlist -----
    def load_watchlist(self) -> list:
        """Read watchlist symbols from stocks.json."""
        data = load_json(STOCKS_FILE, {"stocks": []})
        stocks = data.get("stocks", [])
        symbols = []
        for s in stocks:
            sym = s.get("symbol", "").strip().upper()
            if sym:
                symbols.append(sym)
        if not symbols:
            log.warning("Watchlist is empty — using default symbols")
            symbols = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA",
                       "META", "JPM", "BAC", "GS", "JNJ", "PFE", "UNH", "NEE", "XOM"]
        log.info(f"Watchlist: {len(symbols)} symbols")
        return symbols

    # ----- AKShare fetch -----
    def fetch_with_akshare(self, symbol: str) -> pd.DataFrame | None:
        """Fetch historical daily data via AKShare (新浪/东财, 国内直连)."""
        if not self.akshare_ok or self.ak is None:
            return None

        for attempt in range(3):
            try:
                log.info(f"  akshare attempt {attempt + 1} for {symbol}")
                df = self.ak.stock_us_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=self.start_date,
                    end_date=self.end_date,
                    adjust="",
                )
                if df is None or len(df) == 0:
                    log.warning(f"  akshare returned empty for {symbol}")
                    time.sleep(3)
                    continue

                # Normalize columns
                col_map = {
                    '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
                    '最高': 'High', '最低': 'Low', '成交量': 'Volume',
                }
                df = df.rename(columns=col_map)
                df['Date'] = pd.to_datetime(df['Date'])
                for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                keep_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                df = df[[c for c in keep_cols if c in df.columns]]
                df = df.dropna(subset=['Close'])
                df = df.set_index('Date').sort_index()
                df = df[~df.index.duplicated(keep='last')]
                df = df.tail(self.history_days)

                log.info(f"  akshare OK: {len(df)} rows for {symbol}")
                return df

            except Exception as e:
                log.warning(f"  akshare attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                time.sleep(3)

        return None

    # ----- efinance fetch -----
    def fetch_with_efinance(self, symbol: str) -> pd.DataFrame | None:
        """Fetch historical daily data via efinance.
        Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        if not self.efinance_ok or self.ef is None:
            return None

        for attempt in range(3):
            try:
                log.info(f"  efinance attempt {attempt + 1} for {symbol}")
                df = self.ef.stock.get_quote_history(
                    symbol,
                    beg=self.start_date,
                    end=self.end_date,
                    klt=101,  # daily
                )
                if df is None or len(df) == 0:
                    log.warning(f"  efinance returned empty for {symbol}")
                    time.sleep(2)
                    continue

                # Normalize columns
                col_map = {
                    '日期': 'Date', '开盘': 'Open', '收盘': 'Close',
                    '最高': 'High', '最低': 'Low', '成交量': 'Volume',
                }
                df = df.rename(columns=col_map)
                df['Date'] = pd.to_datetime(df['Date'])
                for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # Keep only needed columns
                keep_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                df = df[[c for c in keep_cols if c in df.columns]]
                df = df.dropna(subset=['Close'])
                df = df.set_index('Date').sort_index()
                df = df[~df.index.duplicated(keep='last')]

                # Keep last N days
                df = df.tail(self.history_days)

                log.info(f"  efinance OK: {len(df)} rows for {symbol}")
                return df

            except Exception as e:
                log.warning(f"  efinance attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                time.sleep(2)

        return None

    # ----- yfinance fallback -----
    def fetch_with_yfinance(self, symbol: str) -> pd.DataFrame | None:
        """Fallback: use yfinance library to get Yahoo Finance data."""
        try:
            import yfinance as yf
        except ImportError:
            log.warning("  yfinance not installed")
            return None

        try:
            log.info(f"  yfinance downloading {symbol} ...")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{self.history_days * 2}d")
            if df is None or len(df) == 0:
                log.warning(f"  yfinance returned empty for {symbol}")
                return None

            # Normalize
            df = df.reset_index()
            df = df.rename(columns={
                'Date': 'Date', 'Open': 'Open', 'High': 'High',
                'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume',
            })
            if 'Date' not in df.columns:
                return None

            df['Date'] = pd.to_datetime(df['Date'])
            for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            keep_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            df = df[[c for c in keep_cols if c in df.columns]]
            df = df.dropna(subset=['Close'])
            df = df.set_index('Date').sort_index()
            df = df[~df.index.duplicated(keep='last')]
            df = df.tail(self.history_days)

            log.info(f"  yfinance OK: {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            log.warning(f"  yfinance failed for {symbol}: {type(e).__name__}: {e}")
            return None

    # ----- Playwright / Yahoo Finance fallback -----
    def fetch_with_playwright(self, symbol: str) -> pd.DataFrame | None:
        """Fallback: use Playwright to get Yahoo Finance historical data.
        Strategy: first try the CSV download endpoint (needs session cookie),
        then fall back to scraping the HTML table.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("  playwright not installed — cannot fallback")
            return None

        log.info(f"  Playwright fallback for {symbol} ...")

        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=self.history_days * 2)).timestamp())

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()

                # Step 1: Visit quote page to get session cookie
                quote_url = f"https://finance.yahoo.com/quote/{symbol}/"
                log.info(f"  Visiting {quote_url}")
                try:
                    page.goto(quote_url, timeout=20000, wait_until="domcontentloaded")
                except Exception:
                    pass

                # Handle consent dialog if present
                try:
                    consent_btn = page.locator('button[name="agree"], button:has-text("Accept"), button:has-text("Agree"), button:has-text("I Accept")')
                    if consent_btn.count() > 0:
                        consent_btn.first.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Step 2: Try CSV download endpoint
                csv_url = (
                    f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
                    f"?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
                )
                log.info(f"  Trying CSV download...")
                try:
                    response = page.goto(csv_url, timeout=15000)
                    if response and response.status() == 200:
                        body = response.body().decode('utf-8', errors='ignore')
                        if body and 'Date,Open' in body:
                            # Parse CSV
                            lines = body.strip().split('\n')
                            parsed = []
                            for line in lines[1:]:  # skip header
                                parts = line.split(',')
                                if len(parts) >= 6:
                                    try:
                                        parsed.append({
                                            'Date': pd.to_datetime(parts[0]),
                                            'Open': float(parts[1]),
                                            'High': float(parts[2]),
                                            'Low': float(parts[3]),
                                            'Close': float(parts[4]),
                                            'Volume': int(parts[5]),
                                        })
                                    except (ValueError, IndexError):
                                        continue
                            if parsed:
                                df = pd.DataFrame(parsed)
                                df = df.set_index('Date').sort_index()
                                df = df[~df.index.duplicated(keep='last')]
                                df = df.tail(self.history_days)
                                log.info(f"  CSV download OK: {len(df)} rows for {symbol}")
                                browser.close()
                                return df
                except Exception as e:
                    log.warning(f"  CSV download failed: {e}")

                # Step 3: Fall back to scraping the history page table
                history_url = (
                    f"https://finance.yahoo.com/quote/{symbol}/history/"
                    f"?period1={start_ts}&period2={end_ts}&interval=1d"
                )
                log.info(f"  Scraping history table at {history_url}")
                try:
                    page.goto(history_url, timeout=25000, wait_until="domcontentloaded")
                except Exception:
                    pass
                page.wait_for_timeout(3000)

                # Extract table data via JS with multiple fallback selectors
                rows_data = page.evaluate("""() => {
                    // Try multiple table selectors
                    const selectors = [
                        "table[data-test='historical-prices']",
                        "table.yf-1jecxso", "table.table", "table"
                    ];
                    let table = null;
                    for (const sel of selectors) {
                        table = document.querySelector(sel);
                        if (table) break;
                    }
                    if (!table) return [];
                    const rows = table.querySelectorAll("tbody tr");
                    const result = [];
                    rows.forEach(row => {
                        const cells = row.querySelectorAll("td");
                        if (cells.length >= 5) {
                            const date = cells[0].textContent.trim();
                            const open = cells[1].textContent.trim();
                            const high = cells[2].textContent.trim();
                            const low = cells[3].textContent.trim();
                            const close = cells[4].textContent.trim();
                            const volume = cells.length >= 7 ? cells[6].textContent.trim() : '0';
                            if (date && close && close !== '-') {
                                result.push({ date, open, high, low, close, volume });
                            }
                        }
                    });
                    return result;
                }""")

                browser.close()

                if not rows_data:
                    log.warning(f"  Playwright: no data rows found for {symbol}")
                    return None

                # Parse into DataFrame
                parsed = []
                for row in rows_data:
                    try:
                        parsed.append({
                            'Date': pd.to_datetime(row['date']),
                            'Open': float(row['open'].replace(',', '')),
                            'High': float(row['high'].replace(',', '')),
                            'Low': float(row['low'].replace(',', '')),
                            'Close': float(row['close'].replace(',', '')),
                            'Volume': int(float(row['volume'].replace(',', '').replace('M', 'e6').replace('B', 'e9') or 0)),
                        })
                    except (ValueError, KeyError):
                        continue

                if not parsed:
                    return None

                df = pd.DataFrame(parsed)
                df = df.set_index('Date').sort_index()
                df = df[~df.index.duplicated(keep='last')]
                df = df.tail(self.history_days)

                log.info(f"  Table scrape OK: {len(df)} rows for {symbol}")
                return df

        except Exception as e:
            log.error(f"  Playwright failed for {symbol}: {type(e).__name__}: {e}")
            return None

    # ----- Unified fetch -----
    def fetch_stock(self, symbol: str) -> pd.DataFrame | None:
        """Fetch data for a single stock. Returns DataFrame or None.
        Chain: akshare → efinance → yfinance → Playwright
        """
        log.info(f"Fetching {symbol} ...")

        # 1. Try AKShare (国内直连, most reliable in China)
        df = self.fetch_with_akshare(symbol)
        if df is not None and len(df) >= 5:
            return df

        # 2. Try efinance (works on GitHub Actions runners)
        log.info(f"  Switching to efinance fallback for {symbol}")
        df = self.fetch_with_efinance(symbol)
        if df is not None and len(df) >= 5:
            return df

        # 3. Fallback to yfinance (lightweight Yahoo Finance API)
        log.info(f"  Switching to yfinance fallback for {symbol}")
        df = self.fetch_with_yfinance(symbol)
        if df is not None and len(df) >= 5:
            return df

        # 4. Fallback to Playwright (heavy but reliable)
        log.info(f"  Switching to Playwright fallback for {symbol}")
        df = self.fetch_with_playwright(symbol)
        if df is not None and len(df) >= 5:
            return df

        log.error(f"  FAILED to fetch {symbol} via both methods")
        return None

    # ----- History persistence -----
    def load_history(self, symbol: str) -> pd.DataFrame | None:
        """Load existing historical data for a symbol."""
        hist_file = HISTORY_DIR / f"{symbol}.json"
        data = load_json(hist_file)
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        try:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['date'] if 'date' in df.columns else df['Date'])
            df = df.set_index('Date').sort_index()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            log.warning(f"  Could not parse history for {symbol}: {e}")
            return None

    def save_history(self, symbol: str, df: pd.DataFrame):
        """Merge new data into existing history and save."""
        existing = self.load_history(symbol)
        if existing is not None and len(existing) > 0:
            # Merge: new data overwrites old dates
            combined = pd.concat([existing, df])
            combined = combined[~combined.index.duplicated(keep='last')]
        else:
            combined = df

        combined = combined.sort_index().tail(self.history_days)

        # Convert to list-of-dicts
        records = []
        for idx, row in combined.iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10],
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume']),
            })

        ensure_dir(HISTORY_DIR)
        save_json(HISTORY_DIR / f"{symbol}.json", records)
        log.info(f"  Saved {len(records)} history rows for {symbol}")

    # ----- Indicator computation -----
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add MA5, MA20, KDJ columns to a DataFrame."""
        if len(df) < 5:
            return df

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

        return df

    def detect_signal(self, row: pd.Series) -> dict:
        """Determine buy/sell/watch signal from indicators."""
        k = row.get('K', 50)
        d = row.get('D', 50)
        j = row.get('J', 50)
        close = row.get('Close', 0)
        ma5 = row.get('MA5', close)
        ma20 = row.get('MA20', close)

        kdj = {
            'kOversold': k < 20,
            'kOverbought': k > 80,
            'goldenCross': k > d,
            'deathCross': k < d,
            'jBottom': j < 0,
        }

        ma = {
            'priceAboveMA5': close > ma5,
            'priceAboveMA20': close > ma20,
            'ma5AboveMA20': ma5 > ma20,
        }

        # Strong buy
        if kdj['kOversold'] and kdj['goldenCross'] and ma['priceAboveMA5']:
            return {'signal': 'buy', 'signal_strength': 'strong'}
        # Mild buy
        if kdj['goldenCross'] and ma['priceAboveMA5'] and ma['ma5AboveMA20']:
            return {'signal': 'buy', 'signal_strength': 'mild'}
        # Watch
        if kdj['goldenCross'] or (k > 70 and not kdj['kOverbought']):
            return {'signal': 'watch', 'signal_strength': None}
        # Strong sell
        if kdj['kOverbought'] and kdj['deathCross'] and not ma['priceAboveMA5']:
            return {'signal': 'sell', 'signal_strength': 'strong'}
        # Mild sell
        if kdj['deathCross'] and not ma['priceAboveMA5'] and not ma['ma5AboveMA20']:
            return {'signal': 'sell', 'signal_strength': 'mild'}
        # J bottom
        if kdj['jBottom']:
            return {'signal': 'watch', 'signal_strength': None}

        return {'signal': None, 'signal_strength': None}

    # ----- Market cap (try efinance) -----
    def fetch_market_cap(self, symbol: str) -> float | None:
        """Try to get market cap via efinance base info."""
        if not self.efinance_ok or self.ef is None:
            return None
        try:
            info = self.ef.stock.get_base_info(symbol)
            if info is not None and len(info) > 0:
                row = info.iloc[0] if hasattr(info, 'iloc') else info
                for key in ['总市值', 'totalMv', 'marketCap', '总市值(元)']:
                    if key in row:
                        val = row[key]
                        if pd.notna(val):
                            return float(val)
        except Exception:
            pass
        return None

    # ----- Snapshot generation -----
    def generate_snapshot(self, all_data: dict) -> dict:
        """Generate stocks.json snapshot from fetched data.
        all_data: { symbol: { df, name, sector, market_cap } }
        """
        stocks = []
        now_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

        # Load existing snapshot for metadata (names, sectors, market caps)
        existing = load_json(STOCKS_FILE, {"stocks": []})
        existing_map = {}
        for s in existing.get("stocks", []):
            existing_map[s.get("symbol", "").upper()] = s

        for symbol, info in all_data.items():
            df = info.get("df")
            if df is None or len(df) == 0:
                # Keep existing data if fetch failed
                if symbol in existing_map:
                    stocks.append(existing_map[symbol])
                continue

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else latest

            # Name / sector: prefer existing, fallback to info from fetch
            old = existing_map.get(symbol, {})
            name = info.get("name") or old.get("name", symbol)
            sector = info.get("sector") or old.get("sector", "其他")
            mcap = info.get("market_cap") or old.get("market_cap", 0)

            # Volume average for reference
            avg_vol = float(df['Volume'].tail(20).mean()) if len(df) >= 5 else 0

            signal = self.detect_signal(latest)

            stock = {
                "symbol": symbol,
                "name": name,
                "sector": sector,
                "market_cap": int(mcap) if mcap else 0,
                "prev_close": round(float(prev['Close']), 2),
                "open": round(float(latest['Open']), 2),
                "high": round(float(latest['High']), 2),
                "low": round(float(latest['Low']), 2),
                "close": round(float(latest['Close']), 2),
                "volume": int(latest['Volume']),
                "vwap": round(float(latest['Close']) if pd.isna(latest.get('VWAP', float('nan'))) else float(latest.get('VWAP', latest['Close'])), 2),
                "avg_volume": int(avg_vol),
                "change_pct": round(float(latest['Close'] - prev['Close']) / float(prev['Close']) * 100, 2),
                "ma5": round(float(latest.get('MA5', latest['Close'])), 2),
                "ma20": round(float(latest.get('MA20', latest['Close'])), 2),
                "k": round(float(latest.get('K', 50)), 1),
                "d": round(float(latest.get('D', 50)), 1),
                "j": round(float(latest.get('J', 50)), 1),
                "signal": signal['signal'],
                "signal_strength": signal['signal_strength'],
            }
            stocks.append(stock)

        # Sort: by market cap desc
        stocks.sort(key=lambda s: s.get('market_cap', 0), reverse=True)

        data_date = datetime.now().strftime("%Y-%m-%d")
        return {
            "updated_at": now_ts,
            "data_date": data_date,
            "stocks": stocks,
        }

    # ----- Main runner -----
    def run(self, symbols: list[str] | None = None):
        """Main pipeline: fetch all → save history → generate snapshot."""
        if symbols is None:
            symbols = self.load_watchlist()

        all_data = {}
        success = 0
        fail = 0

        for symbol in symbols:
            sym = symbol.strip().upper()
            if not sym:
                continue

            df = self.fetch_stock(sym)
            if df is not None and len(df) >= 5:
                df = self.compute_indicators(df)
                self.save_history(sym, df)

                # Get metadata from existing
                existing = load_json(STOCKS_FILE, {"stocks": []})
                existing_map = {}
                for s in existing.get("stocks", []):
                    existing_map[s.get("symbol", "").upper()] = s
                old = existing_map.get(sym, {})

                info = {
                    "df": df,
                    "name": old.get("name", sym),
                    "sector": old.get("sector", "其他"),
                    "market_cap": old.get("market_cap", 0),
                }
                all_data[sym] = info
                success += 1
            else:
                # Keep existing snapshot data if available
                existing = load_json(STOCKS_FILE, {"stocks": []})
                for s in existing.get("stocks", []):
                    if s.get("symbol", "").upper() == sym:
                        all_data[sym] = {"df": None, "name": s.get("name"), "sector": s.get("sector"), "market_cap": s.get("market_cap")}
                        break
                fail += 1

        log.info(f"Fetch complete: {success} OK, {fail} failed")

        # Generate snapshot
        snapshot = self.generate_snapshot(all_data)
        save_json(STOCKS_FILE, snapshot)
        log.info(f"Snapshot saved to {STOCKS_FILE}: {len(snapshot['stocks'])} stocks")

        return snapshot


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="US Stocks Data Fetcher")
    parser.add_argument("--symbol", type=str, help="Fetch a single symbol only")
    parser.add_argument("--days", type=int, default=DEFAULT_HISTORY_DAYS, help="History depth in trading days")
    args = parser.parse_args()

    fetcher = DataFetcher(history_days=args.days)

    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        symbols = fetcher.load_watchlist()

    snapshot = fetcher.run(symbols)

    # Print summary
    print()
    print("=" * 70)
    print(f"  Snapshot: {len(snapshot['stocks'])} stocks  |  {snapshot['updated_at']}")
    print("=" * 70)
    for s in snapshot['stocks']:
        chg = s['change_pct']
        chg_s = f"+{chg:.2f}%" if chg > 0 else f"{chg:.2f}%"
        sig = s.get('signal') or '-'
        print(f"  {s['symbol']:<6} {s['name']:<8}  ${s['close']:<10.2f} {chg_s:>8}  {sig}")


if __name__ == "__main__":
    main()
