# Stock Monitor Enhancements Design

Date: 2026-06-03

## Summary

Enhance the US stocks monitor with four major features: enriched card indicators, left sidebar navigation, user-defined industries, and expanded detail analysis.

## Feature 1: Card Indicator Enrichment

### Signal Cards (top section)
Add a second row below the existing symbol/name/change row showing:
- MA5 direction: ↑ (green) if price > MA5, ↓ (red) if price < MA5
- MA20 direction: ↑ (green) if price > MA20, ↓ (red) if price < MA20
- K/D/J values: compact display like "K:65 D:58 J:79"
- Golden cross indicator: ✨ icon shown when K > D (golden cross active)

### Stock Rows (industry section)
Same indicator row added to each stock row in the industry accordion.

## Feature 2: Left Sidebar Navigation

- Fixed left sidebar (~170px width) with two sections:
  - "今日信号" link — scrolls to signals section
  - Industry list — dynamically generated from user's stock industries
- Clicking an industry filters the main content to show only that industry
- Active industry is highlighted
- Body layout changes from centered single column to sidebar + content

## Feature 3: User-Defined Industries

- When adding a stock, a free-text "行业" input field is shown
- Industry data stored per-stock in localStorage (`us_stock_industries`)
- Frontend overrides any sector data from stocks.json with user-defined values
- Python script's SECTORS dict becomes a fallback default
- Manage modal allows editing a stock's industry
- Sidebar industry list rebuilds dynamically when industries change

## Feature 4: Expanded Detail Analysis

When a stock row is expanded, below existing metrics, add five analysis sections:
1. **成交量分析**: Compare current volume to 20-day average volume; label as 放量/缩量/正常
2. **KDJ 分析**: Interpret K/D/J values — overbought/oversold status, trend direction, cross signals
3. **MA5 分析**: Short-term trend — price position relative to MA5, direction
4. **MA20 分析**: Medium-term trend — price position relative to MA20, alignment with MA5
5. **总结**: One-paragraph synthesis of all factors into actionable insight

## Data Flow

- `stocks.json` → `App.allStocks` → filtered by `App.watchlist` → rendered
- Industry overrides: `localStorage.us_stock_industries` merges into stock data on load
- Sidebar industry list: computed from unique industries across watchlist stocks
- Detail analysis: computed on-the-fly in `Indicators` module when expanding

## Files Changed

- `docs/index.html` — new sidebar markup, updated add-form with industry field
- `docs/css/app.css` — sidebar styles, enhanced card styles, analysis section styles
- `docs/js/indicators.js` — new analysis functions (volume, KDJ, MA5, MA20, summary)
- `docs/js/app.js` — sidebar rendering, industry management, enhanced card rendering, detail expansion
- `scripts/fetch_and_calc.py` — minor: SECTORS as fallback-only, add note about frontend override
