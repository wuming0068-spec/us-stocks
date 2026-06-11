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
# CircuitBreaker — skip dead sources after N consecutive failures
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Per-source health tracker. After *threshold* consecutive failures,
    the source is marked 'dead' and skipped for the rest of the run.
    A single success resets the counter."""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._failures: dict[str, int] = {}
        self._dead: set[str] = set()

    def fail(self, source: str):
        self._failures[source] = self._failures.get(source, 0) + 1
        if self._failures[source] >= self.threshold:
            self._dead.add(source)

    def ok(self, source: str):
        self._failures[source] = 0
        self._dead.discard(source)

    def dead(self, source: str) -> bool:
        return source in self._dead


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
        self.cb = CircuitBreaker(threshold=2)
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
        if self.cb.dead("akshare"):
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
                self.cb.ok("akshare")
                return df

            except Exception as e:
                log.warning(f"  akshare attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                time.sleep(3)

        self.cb.fail("akshare")
        return None

    # ----- efinance fetch -----
    def fetch_with_efinance(self, symbol: str) -> pd.DataFrame | None:
        """Fetch historical daily data via efinance.
        Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        if not self.efinance_ok or self.ef is None:
            return None
        if self.cb.dead("efinance"):
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
                self.cb.ok("efinance")
                return df

            except Exception as e:
                log.warning(f"  efinance attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                time.sleep(2)

        self.cb.fail("efinance")
        return None

    # ----- yfinance fallback -----
    def fetch_with_yfinance(self, symbol: str) -> pd.DataFrame | None:
        """Fallback: use yfinance library to get Yahoo Finance data."""
        if self.cb.dead("yfinance"):
            return None
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
                self.cb.fail("yfinance")
                return None

            # Normalize
            df = df.reset_index()
            df = df.rename(columns={
                'Date': 'Date', 'Open': 'Open', 'High': 'High',
                'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume',
            })
            if 'Date' not in df.columns:
                self.cb.fail("yfinance")
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
            self.cb.ok("yfinance")
            return df

        except Exception as e:
            log.warning(f"  yfinance failed for {symbol}: {type(e).__name__}: {e}")
            self.cb.fail("yfinance")
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

    # ----- Batch Playwright (browser reuse + concurrency) -----
    def _fetch_one_playwright(self, symbol: str) -> pd.DataFrame | None:
        """Fetch one symbol via Playwright. Used standalone or from thread pool."""
        return self.fetch_with_playwright(symbol)

    def fetch_playwright_batch(self, symbols: list[str], concurrency: int = 4) -> dict[str, pd.DataFrame | None]:
        """Fetch multiple symbols via Playwright using a thread pool.
        Each thread opens its own browser — avoids the overhead of sequential
        browser launch/close while staying compatible with sync Playwright."""
        results: dict[str, pd.DataFrame | None] = {}
        if not symbols:
            return results

        try:
            from playwright.sync_api import sync_playwright  # noqa: F811
            sync_playwright()  # quick check that it's importable
        except ImportError:
            log.error("playwright not installed — cannot batch-fetch")
            return {s: None for s in symbols}

        from concurrent.futures import ThreadPoolExecutor, as_completed

        log.info(f"Playwright batch: {len(symbols)} symbols (concurrency={concurrency})")

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(self._fetch_one_playwright, s): s for s in symbols}
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    results[sym] = future.result()
                except Exception as e:
                    log.error(f"  Playwright batch failed for {sym}: {e}")
                    results[sym] = None

        ok = sum(1 for v in results.values() if v is not None and len(v) >= 5)
        log.info(f"Playwright batch done: {ok}/{len(symbols)} OK")
        return results

    # ----- Unified fetch (non-Playwright sources only) -----
    # ----- Sina Finance fetch (most reliable for China users) -----
    def fetch_with_sina(self, symbol: str) -> pd.DataFrame | None:
        """Fetch daily kline from Sina Finance US stock API.
        No API key needed, works well from mainland China.
        """
        if self.cb.dead("sina"):
            return None
        try:
            import requests
        except ImportError:
            return None

        url = (
            f"https://stock.finance.sina.com.cn/usstock/api/json_v2.php/"
            f"US_MinKService.getDailyK?symbol={symbol}&type=daily&num={self.history_days * 2}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.sina.com.cn/",
        }

        for attempt in range(3):
            try:
                log.info(f"  sina attempt {attempt + 1} for {symbol}")
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    log.warning(f"  sina HTTP {resp.status_code} for {symbol}")
                    time.sleep(2)
                    continue
                data = resp.json()
                if not isinstance(data, list) or len(data) == 0:
                    log.warning(f"  sina empty for {symbol}")
                    time.sleep(2)
                    continue

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
                df = df.tail(self.history_days)

                log.info(f"  sina OK: {len(df)} rows for {symbol}")
                self.cb.ok("sina")
                return df

            except Exception as e:
                log.warning(f"  sina attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                time.sleep(2)

        self.cb.fail("sina")
        return None

    def fetch_stock_quick(self, symbol: str) -> pd.DataFrame | None:
        """Try fast sources only: sina → akshare → efinance → yfinance.
        Returns DataFrame or None (caller should fall back to Playwright)."""
        df = self.fetch_with_sina(symbol)
        if df is not None and len(df) >= 5:
            return df

        df = self.fetch_with_akshare(symbol)
        if df is not None and len(df) >= 5:
            return df

        df = self.fetch_with_efinance(symbol)
        if df is not None and len(df) >= 5:
            return df

        df = self.fetch_with_yfinance(symbol)
        if df is not None and len(df) >= 5:
            return df

        return None

    # ----- Unified fetch (all sources, backward-compatible) -----
    def fetch_stock(self, symbol: str) -> pd.DataFrame | None:
        """Fetch data for a single stock. Returns DataFrame or None.
        Chain: akshare → efinance → yfinance → Playwright
        Use fetch_stock_quick + fetch_playwright_batch in batch mode for speed."""
        log.info(f"Fetching {symbol} ...")

        df = self.fetch_stock_quick(symbol)
        if df is not None:
            return df

        # Fallback to Playwright
        log.info(f"  Switching to Playwright fallback for {symbol}")
        df = self.fetch_with_playwright(symbol)
        if df is not None and len(df) >= 5:
            return df

        log.error(f"  FAILED to fetch {symbol} via all methods")
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

    # ----- Market cap (multi-source) -----
    def fetch_market_cap(self, symbol: str) -> float | None:
        """Try to get market cap via multiple sources."""
        # Try efinance first
        if self.efinance_ok and self.ef is not None:
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

        # Try Playwright → Yahoo Finance quote page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None

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
                try:
                    page.goto(f"https://finance.yahoo.com/quote/{symbol}/", timeout=15000, wait_until="domcontentloaded")
                except Exception:
                    browser.close()
                    return None

                page.wait_for_timeout(1500)

                mcap_val = page.evaluate("""() => {
                    const els = document.querySelectorAll('fin-streamer[data-field="marketCap"]');
                    if (els.length > 0) {
                        return els[0].textContent.trim();
                    }
                    return null;
                }""")
                browser.close()

                if mcap_val:
                    return self._parse_num(mcap_val)
        except Exception:
            pass
        return None

    # ----- Verification via Yahoo Finance -----
    def verify_stock_via_playwright(self, symbol: str, local_data: dict) -> dict | None:
        """Verify a single stock's data against Yahoo Finance quote page.
        Returns dict with discrepancies, or None if verification failed to run.
        local_data should have: close, prev_close, open, high, low, volume
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.warning("  Playwright not installed — cannot verify")
            return None

        log.info(f"  Verifying {symbol} via Yahoo Finance ...")
        result = {"symbol": symbol, "warnings": [], "errors": [], "yahoo": {}}

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

                # Navigate to quote page
                quote_url = f"https://finance.yahoo.com/quote/{symbol}/"
                try:
                    page.goto(quote_url, timeout=20000, wait_until="domcontentloaded")
                except Exception:
                    browser.close()
                    return None

                page.wait_for_timeout(2000)

                # Handle consent dialog
                try:
                    consent_btn = page.locator(
                        'button[name="agree"], button:has-text("Accept"), '
                        'button:has-text("Agree"), button:has-text("I Accept")'
                    )
                    if consent_btn.count() > 0:
                        consent_btn.first.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Extract data via JS
                yahoo_data = page.evaluate("""() => {
                    const result = {};
                    document.querySelectorAll('fin-streamer').forEach(el => {
                        const field = el.getAttribute('data-field');
                        const symbol = el.getAttribute('data-symbol');
                        if (field && (!symbol || symbol.toUpperCase() === arguments[0].toUpperCase())) {
                            result[field] = el.textContent.trim();
                        }
                    });

                    // Fallback: get any fin-streamer regardless of symbol attribute
                    if (!result.regularMarketPrice) {
                        document.querySelectorAll('fin-streamer').forEach(el => {
                            const field = el.getAttribute('data-field');
                            if (field && !result[field]) {
                                result[field] = el.textContent.trim();
                            }
                        });
                    }
                    return result;
                }""", symbol)

                browser.close()

                if not yahoo_data or not yahoo_data.get('regularMarketPrice'):
                    log.warning(f"    Yahoo data incomplete for {symbol}")
                    return None

                result["yahoo"] = yahoo_data

                # --- Compare fields ---
                local_close = float(local_data.get('close', 0))
                local_prev = float(local_data.get('prev_close', 0))
                local_open = float(local_data.get('open', 0))
                local_high = float(local_data.get('high', 0))
                local_low = float(local_data.get('low', 0))
                local_vol = int(local_data.get('volume', 0))

                # Previous close comparison (most reliable — yesterday's final data)
                yahoo_prev_close = self._parse_num(yahoo_data.get('regularMarketPreviousClose'))
                if yahoo_prev_close and yahoo_prev_close > 0 and local_prev > 0:
                    prev_diff_pct = abs(local_prev - yahoo_prev_close) / yahoo_prev_close * 100
                    if prev_diff_pct > 2.0:
                        result["errors"].append(
                            f"prev_close mismatch: local={local_prev:.2f} vs yahoo={yahoo_prev_close:.2f} ({prev_diff_pct:.1f}%)"
                        )
                    elif prev_diff_pct > 0.1:
                        result["warnings"].append(
                            f"prev_close slight diff: local={local_prev:.2f} vs yahoo={yahoo_prev_close:.2f} ({prev_diff_pct:.2f}%)"
                        )

                # Open comparison
                yahoo_open = self._parse_num(yahoo_data.get('regularMarketOpen'))
                if yahoo_open and yahoo_open > 0 and local_open > 0:
                    open_diff_pct = abs(local_open - yahoo_open) / yahoo_open * 100
                    if open_diff_pct > 1.0:
                        result["errors"].append(
                            f"open mismatch: local={local_open:.2f} vs yahoo={yahoo_open:.2f} ({open_diff_pct:.1f}%)"
                        )

                # Volume comparison (allow larger tolerance — may be intraday vs final)
                yahoo_vol = self._parse_num(yahoo_data.get('regularMarketVolume'))
                if yahoo_vol and yahoo_vol > 0 and local_vol > 0:
                    vol_diff_pct = abs(local_vol - yahoo_vol) / yahoo_vol * 100
                    if vol_diff_pct > 80:
                        result["errors"].append(
                            f"volume major mismatch: local={local_vol:,} vs yahoo={yahoo_vol:,} ({vol_diff_pct:.0f}%)"
                        )
                    elif vol_diff_pct > 30:
                        result["warnings"].append(
                            f"volume diff: local={local_vol:,} vs yahoo={yahoo_vol:,} ({vol_diff_pct:.0f}%)"
                        )

                # Day range: our high/low should be within or close to Yahoo's range
                yahoo_range_str = yahoo_data.get('regularMarketDayRange', '')
                if yahoo_range_str and ' - ' in yahoo_range_str:
                    parts = yahoo_range_str.split(' - ')
                    yahoo_low = self._parse_num(parts[0])
                    yahoo_high = self._parse_num(parts[1])
                    if yahoo_low and yahoo_high:
                        if local_high > 0 and local_high > yahoo_high * 1.02:
                            result["warnings"].append(
                                f"high outside range: local={local_high:.2f} vs yahoo_high={yahoo_high:.2f}"
                            )
                        if local_low > 0 and local_low < yahoo_low * 0.98:
                            result["warnings"].append(
                                f"low outside range: local={local_low:.2f} vs yahoo_low={yahoo_low:.2f}"
                            )

                # Close price comparison (only if market closed — intraday will differ)
                yahoo_price = self._parse_num(yahoo_data.get('regularMarketPrice'))
                if yahoo_price and yahoo_price > 0 and local_close > 0:
                    close_diff_pct = abs(local_close - yahoo_price) / yahoo_price * 100
                    if close_diff_pct > 2.0:
                        result["errors"].append(
                            f"close major mismatch: local={local_close:.2f} vs yahoo={yahoo_price:.2f} ({close_diff_pct:.1f}%)"
                        )
                    elif close_diff_pct > 0.2:
                        result["warnings"].append(
                            f"close diff: local={local_close:.2f} vs yahoo={yahoo_price:.2f} ({close_diff_pct:.2f}%)"
                        )

                # Determine overall status
                status = "ok"
                if result["errors"]:
                    status = "error"
                elif result["warnings"]:
                    status = "warning"
                result["status"] = status

                # Build corrected data from Yahoo if errors exist
                if result["errors"]:
                    corrected = {}
                    if yahoo_prev_close:
                        corrected["prev_close"] = yahoo_prev_close
                    if yahoo_open:
                        corrected["open"] = yahoo_open
                    if yahoo_price:
                        corrected["close"] = yahoo_price
                    if yahoo_vol:
                        corrected["volume"] = int(yahoo_vol)
                    if yahoo_range_str and ' - ' in yahoo_range_str:
                        parts = yahoo_range_str.split(' - ')
                        corrected_low = self._parse_num(parts[0])
                        corrected_high = self._parse_num(parts[1])
                        if corrected_low:
                            corrected["low"] = corrected_low
                        if corrected_high:
                            corrected["high"] = corrected_high
                    result["corrected"] = corrected

                level = "ERROR" if result["errors"] else ("WARN" if result["warnings"] else "OK")
                log.info(f"    {symbol}: {level} ({len(result['errors'])} errors, {len(result['warnings'])} warnings)")
                return result

        except Exception as e:
            log.error(f"  Verification failed for {symbol}: {type(e).__name__}: {e}")
            return None

    @staticmethod
    def _parse_num(val) -> float | None:
        """Parse a numeric value from string, handling commas, M/B suffixes."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        try:
            s = str(val).replace(',', '').replace('%', '').replace('+', '').strip()
            if s.upper().endswith('T'):
                return float(s[:-1]) * 1e12
            if s.upper().endswith('B'):
                return float(s[:-1]) * 1e9
            if s.upper().endswith('M'):
                return float(s[:-1]) * 1e6
            if s.upper().endswith('K'):
                return float(s[:-1]) * 1e3
            return float(s)
        except (ValueError, TypeError):
            return None

    def verify_snapshot(self, snapshot: dict, sample_size: int = 5) -> dict:
        """Verify a sample of stocks against Yahoo Finance.
        Returns verification report with per-stock results and summary.
        """
        stocks = snapshot.get("stocks", [])
        if not stocks:
            return {"status": "empty", "results": [], "summary": "No stocks to verify"}

        # Verify at least sample_size stocks, prioritizing:
        # 1. Stocks with change > 5% (suspicious)
        # 2. Stocks with close=0 (broken)
        # 3. Largest market cap stocks (important)
        # 4. Random sampling

        to_verify = []
        verified = set()
        remaining = list(stocks)

        # Priority 1: extreme movers
        extreme = [s for s in remaining if abs(s.get('change_pct', 0)) > 5]
        to_verify.extend(extreme)
        remaining = [s for s in remaining if s not in extreme]
        verified.update(s['symbol'] for s in extreme)

        # Priority 2: broken stocks (close=0)
        broken = [s for s in remaining if s.get('close', 0) == 0]
        to_verify.extend(broken)
        remaining = [s for s in remaining if s not in broken]
        verified.update(s['symbol'] for s in broken)

        # Priority 3: top market cap
        top = [s for s in remaining if s.get('market_cap', 0) > 0][:3]
        to_verify.extend(top)
        remaining = [s for s in remaining if s not in top]
        verified.update(s['symbol'] for s in top)

        # Priority 4: top by volume (most actively traded)
        by_vol = sorted(remaining, key=lambda s: s.get('volume', 0), reverse=True)[:3]
        to_verify.extend(by_vol)
        remaining = [s for s in remaining if s not in by_vol]
        verified.update(s['symbol'] for s in by_vol)

        # Fill remaining slots randomly
        need = max(0, sample_size - len(to_verify))
        if need > 0 and remaining:
            import random
            extras = random.sample(remaining, min(need, len(remaining)))
            to_verify.extend(extras)

        log.info(f"Verifying {len(to_verify)} stocks: {[s['symbol'] for s in to_verify]}")

        results = []
        errors_count = 0
        warnings_count = 0
        ok_count = 0

        for stock in to_verify:
            sym = stock['symbol']
            # Skip index-like symbols that Yahoo Finance can't quote
            if sym.startswith('.') or sym in ('NQMAIN',):
                log.info(f"  Skipping {sym} (index/invalid symbol for Yahoo quote)")
                ok_count += 1
                continue

            result = self.verify_stock_via_playwright(sym, stock)
            if result is None:
                ok_count += 1  # verification failed to run, not a data error
                continue

            results.append(result)
            if result['status'] == 'error':
                errors_count += 1
            elif result['status'] == 'warning':
                warnings_count += 1
            else:
                ok_count += 1

        total = len(results)
        summary = f"Verified {total} stocks: {errors_count} errors, {warnings_count} warnings, {ok_count} OK"

        if errors_count > 0:
            summary += f" — DATA QUALITY ISSUES FOUND!"

        log.info(f"Verification complete: {summary}")

        return {
            "status": "error" if errors_count > 0 else ("warning" if warnings_count > 0 else "ok"),
            "results": results,
            "errors_count": errors_count,
            "warnings_count": warnings_count,
            "ok_count": ok_count,
            "summary": summary,
        }

    def auto_correct(self, snapshot: dict, verification_report: dict) -> dict:
        """Apply corrections from verification report to snapshot.
        Only corrects fields where Yahoo Finance data is clearly more reliable
        (prev_close, open, high, low) — volume and close are corrected only if
        the discrepancy is large enough to indicate clearly wrong data.
        """
        results = verification_report.get("results", [])
        corrected_count = 0
        stocks_map = {s['symbol']: s for s in snapshot.get('stocks', [])}

        for r in results:
            if r['status'] != 'error' or 'corrected' not in r:
                continue
            sym = r['symbol']
            corrected = r['corrected']
            if sym not in stocks_map:
                continue

            stock = stocks_map[sym]
            for field in ['prev_close', 'open', 'high', 'low', 'close', 'volume']:
                if field in corrected and field in stock:
                    old_val = stock[field]
                    new_val = corrected[field]
                    if field == 'volume':
                        new_val = int(new_val)
                    else:
                        new_val = round(float(new_val), 2)
                    if abs(float(old_val or 0) - float(new_val or 0)) > 0.001:
                        log.info(f"  Correcting {sym}.{field}: {old_val} → {new_val}")
                        stock[field] = new_val

            # Recalculate change_pct if prev_close or close was corrected
            if 'prev_close' in corrected or 'close' in corrected:
                stock['change_pct'] = round(
                    float(stock['close'] - stock['prev_close']) / float(stock['prev_close']) * 100, 2
                )
            corrected_count += 1

        if corrected_count > 0:
            # Re-save snapshot
            save_json(STOCKS_FILE, snapshot)
            log.info(f"Auto-corrected {corrected_count} stocks, snapshot re-saved")

        return snapshot

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
    def run(self, symbols: list[str] | None = None, no_verify: bool = False, no_mcap: bool = False):
        """Two-phase pipeline:
        Phase 1 — try akshare/efinance/yfinance for each stock (fast, with circuit breaker).
        Phase 2 — batch-fetch remaining stocks via Playwright (browser reuse + concurrency).
        Phase 3 — verify data accuracy against Yahoo Finance & auto-correct.
        Then save history and generate snapshot.
        """
        if symbols is None:
            symbols = self.load_watchlist()

        # Remove index symbols that can't be fetched through stock APIs
        # These symbols either have no data or require different API endpoints
        INDEX_SYMBOLS = {'.SOX', '.NDX', '.IXIC', 'NQMAIN'}
        symbols = [s for s in symbols if s.strip().upper() not in INDEX_SYMBOLS]
        removed = [s for s in symbols if s.strip().upper() in INDEX_SYMBOLS]
        if removed:
            log.warning(f"Skipping index symbols (not supported by stock APIs): {removed}")

        # Load ALL existing stocks so we never drop data for stocks
        # that weren't in the current fetch set
        existing = load_json(STOCKS_FILE, {"stocks": []})
        existing_map = {}
        for s in existing.get("stocks", []):
            existing_map[s.get("symbol", "").upper()] = s

        # Pre-populate all_data with every existing stock (df=None means
        # generate_snapshot will reuse the old snapshot entry verbatim)
        all_data = {}
        for sym, s in existing_map.items():
            # Skip index symbols in existing data too
            if sym in INDEX_SYMBOLS:
                continue
            all_data[sym] = {
                "df": None,
                "name": s.get("name", sym),
                "sector": s.get("sector", "其他"),
                "market_cap": s.get("market_cap", 0),
            }

        success = 0
        fail = 0
        need_playwright: list[str] = []
        need_mcap: list[str] = []   # stocks that still have market_cap=0

        # ---- Phase 1: fast sources only ----
        log.info(f"Phase 1: fast sources for {len(symbols)} symbols")
        for symbol in symbols:
            sym = symbol.strip().upper()
            if not sym:
                continue

            log.info(f"Fetching {sym} ...")
            df = self.fetch_stock_quick(sym)
            if df is not None and len(df) >= 5:
                df = self.compute_indicators(df)
                self.save_history(sym, df)

                old = existing_map.get(sym, {})
                mcap = old.get("market_cap", 0)
                if mcap == 0 and not no_mcap:
                    need_mcap.append(sym)

                info = {
                    "df": df,
                    "name": old.get("name", sym),
                    "sector": old.get("sector", "其他"),
                    "market_cap": mcap,
                }
                all_data[sym] = info
                success += 1
            else:
                need_playwright.append(sym)

        # ---- Phase 2: batch Playwright ----
        if need_playwright:
            log.info(f"Phase 2: Playwright batch for {len(need_playwright)} symbols")
            pw_results = self.fetch_playwright_batch(need_playwright, concurrency=4)
            for sym, df in pw_results.items():
                if df is not None and len(df) >= 5:
                    df = self.compute_indicators(df)
                    self.save_history(sym, df)

                    old = existing_map.get(sym, {})
                    mcap = old.get("market_cap", 0)
                    if mcap == 0 and not no_mcap:
                        need_mcap.append(sym)

                    info = {
                        "df": df,
                        "name": old.get("name", sym),
                        "sector": old.get("sector", "其他"),
                        "market_cap": mcap,
                    }
                    all_data[sym] = info
                    success += 1
                else:
                    fail += 1

        # ---- Market cap batch fetch ----
        if need_mcap and not no_mcap:
            log.info(f"Fetching market caps for {len(need_mcap)} stocks via Playwright ...")
            for sym in need_mcap:
                try:
                    mcap = self.fetch_market_cap(sym)
                    if mcap and mcap > 0:
                        # Store in all_data for snapshot generation
                        if sym in all_data:
                            all_data[sym]['market_cap'] = int(mcap)
                        log.info(f"  {sym} market cap: {mcap:,.0f}")
                    time.sleep(0.5)  # rate limit
                except Exception as e:
                    log.warning(f"  Market cap fetch failed for {sym}: {e}")

        log.info(f"Fetch complete: {success} OK, {fail} failed (circuit-breaker: "
                 f"akshare={'dead' if self.cb.dead('akshare') else 'alive'}, "
                 f"efinance={'dead' if self.cb.dead('efinance') else 'alive'}, "
                 f"yfinance={'dead' if self.cb.dead('yfinance') else 'alive'})")

        # Generate snapshot
        snapshot = self.generate_snapshot(all_data)

        # ---- Phase 3: Verify & auto-correct ----
        if not no_verify:
            log.info("Phase 3: Verify data accuracy via Yahoo Finance ...")
            try:
                report = self.verify_snapshot(snapshot, sample_size=8)
                if report.get("errors_count", 0) > 0:
                    log.warning(f"  Verification found {report['errors_count']} stock(s) with errors!")
                    snapshot = self.auto_correct(snapshot, report)
            except Exception as e:
                log.warning(f"  Verification skipped due to error: {type(e).__name__}: {e}")
        else:
            log.info("Phase 3: Verification skipped (--no-verify)")

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
    parser.add_argument("--skip-akshare", action="store_true", help="Skip akshare (domestic CN source)")
    parser.add_argument("--skip-efinance", action="store_true", help="Skip efinance (domestic CN source)")
    parser.add_argument("--skip-yfinance", action="store_true", help="Skip yfinance (Yahoo API)")
    parser.add_argument("--no-verify", action="store_true", help="Skip Yahoo Finance verification step")
    parser.add_argument("--no-mcap", action="store_true", help="Skip market cap fetching")
    args = parser.parse_args()

    fetcher = DataFetcher(history_days=args.days)

    # Pre-kill sources that were explicitly skipped
    if args.skip_akshare:
        fetcher.cb._failures["akshare"] = 999
        fetcher.cb._dead.add("akshare")
        log.info("akshare disabled via --skip-akshare")
    if args.skip_efinance:
        fetcher.cb._failures["efinance"] = 999
        fetcher.cb._dead.add("efinance")
        log.info("efinance disabled via --skip-efinance")
    if args.skip_yfinance:
        fetcher.cb._failures["yfinance"] = 999
        fetcher.cb._dead.add("yfinance")
        log.info("yfinance disabled via --skip-yfinance")

    if args.symbol:
        symbols = [args.symbol.strip().upper()]
    else:
        symbols = fetcher.load_watchlist()

    snapshot = fetcher.run(symbols, no_verify=args.no_verify, no_mcap=args.no_mcap)

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
