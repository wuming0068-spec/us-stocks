#!/usr/bin/env python3
"""
server.py — Local dev server for US Stocks Monitor
====================================================
Serves static files from docs/ and provides API endpoints
for managing the watchlist. All changes are persisted to
docs/data/stocks.json immediately.

Usage:
  python scripts/server.py              # default port 8080
  python scripts/server.py --port 3000  # custom port
  python scripts/server.py --no-fetch   # skip auto-fetch on add
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
STOCKS_FILE = DATA_DIR / "stocks.json"
HISTORY_DIR = DATA_DIR / "history"
FETCH_SCRIPT = ROOT / "scripts" / "fetch_data.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("server")


def load_stocks() -> dict:
    if STOCKS_FILE.exists():
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"stocks": [], "updated_at": "", "data_date": ""}


def save_stocks(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def get_existing_symbols() -> set:
    data = load_stocks()
    return {s["symbol"].upper() for s in data.get("stocks", [])}


def get_existing_stock(symbol: str) -> dict | None:
    data = load_stocks()
    for s in data.get("stocks", []):
        if s["symbol"].upper() == symbol.upper():
            return s
    return None


class APIHandler(SimpleHTTPRequestHandler):
    """Serve docs/ as static files + handle /api/* endpoints."""

    auto_fetch = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def log_message(self, format, *args):
        log.info("%s - %s", self.client_address[0], format % args)

    # ---- API routing ----
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/add":
            self.handle_add()
        elif path == "/api/remove":
            self.handle_remove()
        elif path == "/api/set-industry":
            self.handle_set_industry()
        elif path == "/api/batch-add":
            self.handle_batch_add()
        elif path == "/api/fetch":
            self.handle_fetch()
        elif path == "/api/sync-watchlist":
            self.handle_sync_watchlist()
        else:
            self.send_error(404, "Unknown API endpoint")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/search":
            self.handle_search()
        elif path == "/api/status":
            self.handle_status()
        elif path == "/api/trigger-fetch":
            self.handle_fetch()
        else:
            # Serve static files from docs/
            super().do_GET()

    # ---- Helpers ----
    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def send_ok(self, extra=None):
        resp = {"ok": True}
        if extra:
            resp.update(extra)
        self.send_json(resp)

    def send_error(self, code, msg):
        self.send_json({"ok": False, "error": msg}, status=code)

    # CORS preflight
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- API handlers ----
    def handle_search(self):
        """Search stock symbols by query string."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        q = (params.get("q", [""])[0] or "").strip().upper()
        results = []
        if q and len(q) >= 1:
            symbols_file = DATA_DIR / "symbols.json"
            if symbols_file.exists():
                with open(symbols_file, "r", encoding="utf-8") as f:
                    all_symbols = json.load(f)
                for s in all_symbols:
                    sym = s.get("symbol", "").upper()
                    name = s.get("name", "")
                    if q in sym or q in name.upper():
                        results.append(s)
                        if len(results) >= 20:
                            break
        self.send_json(results)

    def handle_status(self):
        data = load_stocks()
        self.send_ok({
            "count": len(data.get("stocks", [])),
            "updated_at": data.get("updated_at", ""),
            "data_date": data.get("data_date", ""),
        })

    def handle_add(self):
        body = self.read_body()
        symbol = body.get("symbol", "").strip().upper()
        industry = body.get("industry", "").strip()

        if not symbol or not re.match(r"^[A-Z0-9.]+$", symbol):
            self.send_error(400, f"Invalid symbol: {symbol}")
            return

        data = load_stocks()
        existing = {s["symbol"].upper() for s in data["stocks"]}

        if symbol in existing:
            self.send_error(409, f"{symbol} already in watchlist")
            return

        # Add placeholder entry (will be filled by fetch_data.py)
        new_stock = {
            "symbol": symbol,
            "name": symbol,
            "sector": industry or "其他",
            "market_cap": 0,
            "prev_close": 0,
            "open": 0, "high": 0, "low": 0, "close": 0,
            "volume": 0, "vwap": 0, "avg_volume": 0,
            "change_pct": 0,
            "ma5": 0, "ma20": 0,
            "k": 50, "d": 50, "j": 50,
            "signal": None, "signal_strength": None,
        }
        data["stocks"].append(new_stock)
        save_stocks(data)

        log.info(f"Added {symbol}" + (f" ({industry})" if industry else ""))

        # Auto-fetch data for the new stock
        fetch_result = None
        if self.auto_fetch:
            fetch_result = self.run_fetch(symbol)

        self.send_ok({"symbol": symbol, "fetched": fetch_result})

    def handle_remove(self):
        body = self.read_body()
        symbol = body.get("symbol", "").strip().upper()

        data = load_stocks()
        original_count = len(data["stocks"])
        data["stocks"] = [s for s in data["stocks"] if s["symbol"].upper() != symbol]
        removed = len(data["stocks"]) < original_count
        save_stocks(data)

        if removed:
            log.info(f"Removed {symbol}")
            self.send_ok({"symbol": symbol})
        else:
            self.send_error(404, f"{symbol} not found in watchlist")

    def handle_set_industry(self):
        body = self.read_body()
        symbol = body.get("symbol", "").strip().upper()
        industry = body.get("industry", "").strip()

        data = load_stocks()
        for s in data["stocks"]:
            if s["symbol"].upper() == symbol:
                s["sector"] = industry if industry else "其他"
                save_stocks(data)
                log.info(f"Set {symbol} industry → {industry or '其他'}")
                self.send_ok({"symbol": symbol, "industry": industry or "其他"})
                return

        self.send_error(404, f"{symbol} not found")

    def handle_batch_add(self):
        body = self.read_body()
        items = body.get("items", [])  # [{symbol, industry}, ...]
        data = load_stocks()
        existing = {s["symbol"].upper() for s in data["stocks"]}

        added = []
        for item in items:
            sym = item.get("symbol", "").strip().upper()
            ind = item.get("industry", "").strip()
            if not sym or not re.match(r"^[A-Z0-9.]+$", sym):
                continue
            if sym in existing:
                continue
            data["stocks"].append({
                "symbol": sym, "name": sym, "sector": ind or "其他",
                "market_cap": 0,
                "prev_close": 0, "open": 0, "high": 0, "low": 0, "close": 0,
                "volume": 0, "vwap": 0, "avg_volume": 0, "change_pct": 0,
                "ma5": 0, "ma20": 0, "k": 50, "d": 50, "j": 50,
                "signal": None, "signal_strength": None,
            })
            existing.add(sym)
            added.append(sym)

        if added:
            save_stocks(data)
            log.info(f"Batch added: {added}")

            if self.auto_fetch:
                self.run_fetch_batch(added)

        self.send_ok({"added": added, "count": len(added)})

    def handle_fetch(self):
        """Trigger data fetch for all stocks or a specific symbol."""
        body = self.read_body() if self.headers.get("Content-Length") else {}
        symbol = body.get("symbol", "").strip().upper() if body else None

        if symbol:
            result = self.run_fetch(symbol)
        else:
            result = self.run_fetch()

        self.send_ok({"fetched": result})

    def handle_sync_watchlist(self):
        """Receive full watchlist from web page, sync to stocks.json.
        Adds new symbols, preserves existing data for known symbols."""
        body = self.read_body()
        symbols = body.get("symbols", [])  # list of symbols from page

        data = load_stocks()
        existing_map = {s["symbol"].upper(): s for s in data["stocks"]}

        new_stocks = []
        new_symbols = []
        for sym in symbols:
            sym = sym.strip().upper()
            if not sym or not re.match(r"^[A-Z0-9.]+$", sym):
                continue
            if sym in existing_map:
                new_stocks.append(existing_map[sym])
            else:
                new_symbols.append(sym)
                new_stocks.append({
                    "symbol": sym, "name": sym, "sector": "其他",
                    "market_cap": 0,
                    "prev_close": 0, "open": 0, "high": 0, "low": 0, "close": 0,
                    "volume": 0, "vwap": 0, "avg_volume": 0, "change_pct": 0,
                    "ma5": 0, "ma20": 0, "k": 50, "d": 50, "j": 50,
                    "signal": None, "signal_strength": None,
                })

        data["stocks"] = new_stocks
        save_stocks(data)
        log.info(f"Synced watchlist: {len(new_stocks)} stocks ({len(new_symbols)} new)")

        if new_symbols and self.auto_fetch:
            self.run_fetch_batch(new_symbols)

        self.send_ok({"total": len(new_stocks), "new": len(new_symbols)})

    # ---- Fetch integration ----
    def run_fetch(self, symbol: str | None = None) -> bool:
        """Run fetch_data.py. Returns True if successful."""
        try:
            cmd = [sys.executable, str(FETCH_SCRIPT), "--no-verify"]
            if symbol:
                cmd += ["--symbol", symbol]
            log.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
            if result.returncode == 0:
                log.info("Fetch completed successfully")
                return True
            else:
                log.error(f"Fetch failed (exit {result.returncode}): {result.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            log.error("Fetch timed out")
            return False
        except Exception as e:
            log.error(f"Fetch error: {e}")
            return False

    def run_fetch_batch(self, symbols: list[str]) -> bool:
        """Run full fetch for all stocks (simpler and handles new symbols correctly)."""
        try:
            cmd = [sys.executable, str(FETCH_SCRIPT), "--no-verify"]
            log.info(f"Running full fetch after adding {len(symbols)} new symbols...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
            ok = result.returncode == 0
            log.info(f"Fetch {'OK' if ok else 'FAILED'}")
            return ok
        except Exception as e:
            log.error(f"Batch fetch error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="US Stocks Monitor Dev Server")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--no-fetch", action="store_true", help="Skip auto-fetch on add")
    args = parser.parse_args()

    APIHandler.auto_fetch = not args.no_fetch

    server = HTTPServer(("0.0.0.0", args.port), APIHandler)
    banner = f"""
╔══════════════════════════════════════════════╗
║       US Stocks Monitor Server              ║
╠══════════════════════════════════════════════╣
║  URL:       http://localhost:{args.port}       ║
║  API:       http://localhost:{args.port}/api/  ║
║  Auto-fetch: {'ON ' if APIHandler.auto_fetch else 'OFF'}                            ║
╚══════════════════════════════════════════════╝
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        # Windows console fallback
        print(f"US Stocks Monitor Server")
        print(f"URL: http://localhost:{args.port}")
        print(f"API: http://localhost:{args.port}/api/")
        print(f"Auto-fetch: {'ON' if APIHandler.auto_fetch else 'OFF'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
