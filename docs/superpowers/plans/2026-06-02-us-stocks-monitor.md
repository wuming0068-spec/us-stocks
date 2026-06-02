# 美股自选股智能监控分析系统 V1.0 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-user US stocks watchlist monitor with daily data refresh, industry-grouped display, KDJ/MA indicators, and pushplus morning report.

**Architecture:** Static HTML/CSS/JS frontend served from GitHub Pages, reading stocks.json generated daily by a Python script (akshare) run via GitHub Actions. User's watchlist stored in localStorage. Pushplus API delivers morning briefing to WeChat.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, Python 3 (akshare, pandas, numpy), GitHub Actions

---

## File Structure

```
us-stocks-monitor/
├── .github/workflows/
│   └── daily-update.yml          # Task 9
├── scripts/
│   ├── requirements.txt           # Task 8
│   └── fetch_and_calc.py          # Task 7
├── docs/                          # GitHub Pages root
│   ├── index.html                 # Task 3
│   ├── css/
│   │   └── app.css               # Task 4
│   ├── js/
│   │   ├── app.js                 # Task 5
│   │   └── indicators.js          # Task 6
│   └── data/
│       └── stocks.json            # Task 2 (sample data)
└── README.md                      # Task 10
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `docs/index.html` (empty placeholder)
- Create: `docs/css/app.css` (empty placeholder)
- Create: `docs/js/app.js` (empty placeholder)
- Create: `docs/js/indicators.js` (empty placeholder)
- Create: `docs/data/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `.gitignore`

- [ ] **Step 1: Create all directories and placeholder files**

```bash
mkdir -p docs/css docs/js docs/data scripts .github/workflows
touch docs/index.html docs/css/app.css docs/js/app.js docs/js/indicators.js docs/data/.gitkeep scripts/.gitkeep
```

- [ ] **Step 2: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
venv/
.env
.DS_Store
.superpowers/
```

- [ ] **Step 3: Commit scaffold**

```bash
git init
git add -A
git commit -m "chore: project scaffold"
```

---

### Task 2: Sample stocks.json

**Files:**
- Create: `docs/data/stocks.json`

- [ ] **Step 1: Write sample data with 15 diverse stocks across 4 sectors**

```json
{
  "updated_at": "2026-06-02T08:00:00+08:00",
  "data_date": "2026-06-01",
  "stocks": [
    {
      "symbol": "AAPL",
      "name": "苹果",
      "sector": "科技",
      "market_cap": 2890000000000,
      "prev_close": 183.53,
      "open": 184.10,
      "high": 186.20,
      "low": 183.80,
      "close": 185.32,
      "volume": 52340000,
      "vwap": 184.95,
      "change_pct": 0.97,
      "ma5": 184.20,
      "ma20": 182.10,
      "k": 62.3,
      "d": 58.1,
      "j": 70.7,
      "signal": "buy",
      "signal_strength": "strong"
    },
    {
      "symbol": "NVDA",
      "name": "英伟达",
      "sector": "科技",
      "market_cap": 2760000000000,
      "prev_close": 1123.45,
      "open": 1128.90,
      "high": 1155.30,
      "low": 1122.10,
      "close": 1146.98,
      "volume": 38400000,
      "vwap": 1140.50,
      "change_pct": 2.10,
      "ma5": 1130.20,
      "ma20": 1098.40,
      "k": 72.1,
      "d": 65.3,
      "j": 85.7,
      "signal": "watch",
      "signal_strength": null
    },
    {
      "symbol": "MSFT",
      "name": "微软",
      "sector": "科技",
      "market_cap": 3010000000000,
      "prev_close": 425.30,
      "open": 424.80,
      "high": 427.50,
      "low": 421.60,
      "close": 423.98,
      "volume": 18200000,
      "vwap": 424.60,
      "change_pct": -0.31,
      "ma5": 426.10,
      "ma20": 430.50,
      "k": 35.2,
      "d": 40.8,
      "j": 24.0,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "GOOGL",
      "name": "谷歌",
      "sector": "科技",
      "market_cap": 1980000000000,
      "prev_close": 178.90,
      "open": 179.20,
      "high": 181.30,
      "low": 178.50,
      "close": 180.45,
      "volume": 22100000,
      "vwap": 179.80,
      "change_pct": 0.87,
      "ma5": 179.50,
      "ma20": 177.80,
      "k": 55.4,
      "d": 52.1,
      "j": 62.0,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "AMZN",
      "name": "亚马逊",
      "sector": "科技",
      "market_cap": 2140000000000,
      "prev_close": 218.30,
      "open": 219.10,
      "high": 222.40,
      "low": 218.00,
      "close": 221.15,
      "volume": 31200000,
      "vwap": 220.20,
      "change_pct": 1.31,
      "ma5": 219.30,
      "ma20": 215.60,
      "k": 58.9,
      "d": 55.2,
      "j": 66.3,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "TSLA",
      "name": "特斯拉",
      "sector": "科技",
      "market_cap": 788000000000,
      "prev_close": 242.80,
      "open": 240.50,
      "high": 245.30,
      "low": 238.20,
      "close": 239.65,
      "volume": 45600000,
      "vwap": 241.30,
      "change_pct": -1.30,
      "ma5": 244.10,
      "ma20": 248.70,
      "k": 28.5,
      "d": 33.2,
      "j": 19.1,
      "signal": "sell",
      "signal_strength": "mild"
    },
    {
      "symbol": "META",
      "name": "Meta",
      "sector": "科技",
      "market_cap": 1520000000000,
      "prev_close": 532.10,
      "open": 535.20,
      "high": 540.80,
      "low": 531.50,
      "close": 538.90,
      "volume": 15200000,
      "vwap": 536.40,
      "change_pct": 1.28,
      "ma5": 534.60,
      "ma20": 525.30,
      "k": 61.7,
      "d": 57.4,
      "j": 70.3,
      "signal": "watch",
      "signal_strength": null
    },
    {
      "symbol": "JPM",
      "name": "摩根大通",
      "sector": "金融",
      "market_cap": 580000000000,
      "prev_close": 198.45,
      "open": 197.80,
      "high": 199.20,
      "low": 196.50,
      "close": 197.30,
      "volume": 9800000,
      "vwap": 197.80,
      "change_pct": -0.58,
      "ma5": 198.90,
      "ma20": 201.20,
      "k": 42.3,
      "d": 46.5,
      "j": 33.9,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "BAC",
      "name": "美国银行",
      "sector": "金融",
      "market_cap": 365000000000,
      "prev_close": 42.15,
      "open": 42.30,
      "high": 42.60,
      "low": 41.95,
      "close": 42.05,
      "volume": 25400000,
      "vwap": 42.25,
      "change_pct": -0.24,
      "ma5": 42.40,
      "ma20": 43.10,
      "k": 38.1,
      "d": 41.2,
      "j": 31.9,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "GS",
      "name": "高盛",
      "sector": "金融",
      "market_cap": 195000000000,
      "prev_close": 445.20,
      "open": 446.80,
      "high": 450.30,
      "low": 444.10,
      "close": 448.90,
      "volume": 1800000,
      "vwap": 447.50,
      "change_pct": 0.83,
      "ma5": 444.50,
      "ma20": 440.20,
      "k": 56.8,
      "d": 53.1,
      "j": 64.2,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "JNJ",
      "name": "强生",
      "sector": "医疗",
      "market_cap": 450000000000,
      "prev_close": 162.30,
      "open": 162.80,
      "high": 164.20,
      "low": 161.90,
      "close": 163.50,
      "volume": 7500000,
      "vwap": 163.10,
      "change_pct": 0.74,
      "ma5": 162.80,
      "ma20": 161.40,
      "k": 54.2,
      "d": 51.8,
      "j": 59.0,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "PFE",
      "name": "辉瑞",
      "sector": "医疗",
      "market_cap": 210000000000,
      "prev_close": 28.90,
      "open": 28.70,
      "high": 29.10,
      "low": 28.50,
      "close": 28.55,
      "volume": 31200000,
      "vwap": 28.75,
      "change_pct": -1.21,
      "ma5": 29.10,
      "ma20": 30.20,
      "k": 22.4,
      "d": 27.8,
      "j": 11.6,
      "signal": "sell",
      "signal_strength": "strong"
    },
    {
      "symbol": "UNH",
      "name": "联合健康",
      "sector": "医疗",
      "market_cap": 520000000000,
      "prev_close": 525.60,
      "open": 526.40,
      "high": 530.10,
      "low": 524.80,
      "close": 528.30,
      "volume": 3200000,
      "vwap": 527.10,
      "change_pct": 0.51,
      "ma5": 526.50,
      "ma20": 522.30,
      "k": 51.3,
      "d": 49.8,
      "j": 54.3,
      "signal": null,
      "signal_strength": null
    },
    {
      "symbol": "NEE",
      "name": "新纪元能源",
      "sector": "能源",
      "market_cap": 155000000000,
      "prev_close": 75.20,
      "open": 75.80,
      "high": 76.90,
      "low": 75.10,
      "close": 76.45,
      "volume": 8700000,
      "vwap": 76.10,
      "change_pct": 1.66,
      "ma5": 75.80,
      "ma20": 74.60,
      "k": 60.5,
      "d": 56.8,
      "j": 67.9,
      "signal": "buy",
      "signal_strength": "mild"
    },
    {
      "symbol": "XOM",
      "name": "埃克森美孚",
      "sector": "能源",
      "market_cap": 480000000000,
      "prev_close": 115.30,
      "open": 115.60,
      "high": 116.80,
      "low": 114.90,
      "close": 115.10,
      "volume": 14200000,
      "vwap": 115.60,
      "change_pct": -0.17,
      "ma5": 115.80,
      "ma20": 116.50,
      "k": 44.7,
      "d": 47.2,
      "j": 39.7,
      "signal": null,
      "signal_strength": null
    }
  ]
}
```

- [ ] **Step 2: Validate JSON is well-formed**

```bash
python -m json.tool docs/data/stocks.json > /dev/null && echo "Valid JSON"
```

- [ ] **Step 3: Commit**

```bash
git add docs/data/stocks.json
git commit -m "feat: add sample stocks.json with 15 stocks across 4 sectors"
```

---

### Task 3: index.html — Page Structure

**Files:**
- Create: `docs/index.html`

This is the main page with all UI sections: top bar, data freshness banner, search/management bar, signals area, industry accordion, stock detail card template.

- [ ] **Step 1: Write complete HTML**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>美股自选监控</title>
<link rel="stylesheet" href="css/app.css">
</head>
<body>

<!-- Top Bar -->
<header id="top-bar">
  <div class="top-row">
    <h1 class="title">📈 美股自选</h1>
    <div class="top-actions">
      <button id="btn-refresh" class="btn-icon" title="刷新数据">
        🔄 <span class="btn-text">刷新</span>
        <span id="refresh-count" class="badge">剩10次</span>
      </button>
      <button id="btn-manage" class="btn-icon" title="管理自选股">⚙</button>
    </div>
  </div>
  <div id="data-status" class="status-bar">
    📡 数据更新: <span id="update-time">加载中...</span> (基于前一日收盘数据)
  </div>
</header>

<!-- Main Content -->
<main id="content">

  <!-- Search / Add Bar -->
  <section id="search-section">
    <div class="search-row">
      <div class="search-input-wrap">
        <input type="text" id="search-input" placeholder="🔍 搜索代码或名称..." autocomplete="off">
        <div id="search-suggestions" class="suggestions-dropdown hidden"></div>
      </div>
      <button id="btn-add" class="btn-primary">+ 添加</button>
    </div>
    <div id="add-form" class="add-form hidden">
      <input type="text" id="add-symbol" placeholder="输入美股代码，如 AAPL" autocomplete="off">
      <div id="add-suggestions" class="suggestions-dropdown hidden"></div>
      <div class="add-actions">
        <button id="btn-confirm-add" class="btn-primary btn-sm">确认添加</button>
        <button id="btn-cancel-add" class="btn-ghost btn-sm">取消</button>
      </div>
    </div>
  </section>

  <!-- Signals Area -->
  <section id="signals-section">
    <h2 class="section-title">🎯 今日信号</h2>
    <div id="signals-list"></div>
    <div id="signals-empty" class="empty-state hidden">暂无明确信号</div>
  </section>

  <!-- Industry Accordion -->
  <section id="industries-section">
    <h2 class="section-title">📊 行业概览</h2>
    <div id="industries-list"></div>
    <div id="industries-empty" class="empty-state hidden">没有自选股数据。点击上方「+ 添加」开始添加自选股。</div>
  </section>

</main>

<!-- Detail Card Template (hidden) -->
<template id="tmpl-detail-card">
  <div class="detail-card">
    <div class="detail-price-row">
      <div class="detail-header">
        <span class="detail-symbol"></span>
        <span class="detail-name"></span>
      </div>
      <div class="detail-price-info">
        <span class="detail-close"></span>
        <span class="detail-change"></span>
      </div>
    </div>
    <div class="detail-metrics">
      <div class="metric"><span class="metric-label">昨收</span><span class="metric-value prev-close"></span></div>
      <div class="metric"><span class="metric-label">开盘</span><span class="metric-value open"></span></div>
      <div class="metric"><span class="metric-label">成交量</span><span class="metric-value volume"></span></div>
      <div class="metric"><span class="metric-label">市值</span><span class="metric-value mcap"></span></div>
    </div>
    <div class="detail-ma-row">
      <span class="ma-item">MA5 <strong class="ma5-val"></strong></span>
      <span class="ma-desc"></span>
      <span class="ma-item">MA20 <strong class="ma20-val"></strong></span>
      <span class="ma-align"></span>
    </div>
    <div class="detail-kdj-row">
      <span class="kdj-label">KDJ</span>
      <span class="kdj-item k-val"></span>
      <span class="kdj-item d-val"></span>
      <span class="kdj-item j-val"></span>
    </div>
  </div>
</template>

<!-- Watchlist Manager Modal Template -->
<template id="tmpl-manage-modal">
  <div class="modal-overlay">
    <div class="modal-content">
      <div class="modal-header">
        <h3>📋 管理自选股</h3>
        <button class="btn-close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="manage-search">
          <input type="text" placeholder="🔍 筛选自选股..." class="manage-filter">
        </div>
        <div class="manage-list"></div>
        <div class="manage-empty empty-state hidden">自选股列表为空</div>
        <div class="manage-batch">
          <textarea placeholder="批量添加代码&#10;一行一个，如：&#10;AAPL&#10;NVDA&#10;MSFT" class="batch-input" rows="6"></textarea>
          <button class="btn-primary btn-batch-add">批量添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<!-- Toast Container -->
<div id="toast-container"></div>

<script src="js/indicators.js"></script>
<script src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add docs/index.html
git commit -m "feat: add index.html with all UI sections"
```

---

### Task 4: app.css — Complete Styling

**Files:**
- Create: `docs/css/app.css`

All styles including mobile responsive, accordion animation, detail card, signal badges, modal, toast. CSS custom properties for theming.

- [ ] **Step 1: Write complete CSS**

```css
/* === CSS Custom Properties === */
:root {
  --color-bg: #f5f6fa;
  --color-card: #ffffff;
  --color-primary: #1976d2;
  --color-success: #2e7d32;
  --color-danger: #c62828;
  --color-warning: #e65100;
  --color-text: #1a1a2e;
  --color-text-secondary: #666;
  --color-border: #e8e8e8;
  --color-blue-bg: #e3f2fd;
  --color-blue-text: #1565c0;
  --color-buy-bg: #e8f5e9;
  --color-sell-bg: #ffebee;
  --color-watch-bg: #fff3e0;
  --color-overbought: #e53935;
  --color-oversold: #43a047;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-modal: 0 8px 32px rgba(0,0,0,0.2);
  --radius: 10px;
  --radius-sm: 6px;
  --max-width: 768px;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { font-size: 16px; -webkit-text-size-adjust: 100%; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.5;
  max-width: var(--max-width);
  margin: 0 auto;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* === Top Bar === */
#top-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--color-card);
  box-shadow: var(--shadow-card);
}

.top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
}

.title {
  font-size: 1.125rem;
  font-weight: 800;
  white-space: nowrap;
}

.top-actions {
  display: flex;
  gap: 6px;
}

.btn-icon {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #f5f5f5;
  border: 1px solid var(--color-border);
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.btn-icon:active { background: #e0e0e0; }

.badge {
  font-size: 0.65rem;
  color: var(--color-text-secondary);
}

.status-bar {
  padding: 8px 14px;
  background: var(--color-blue-bg);
  color: var(--color-blue-text);
  font-size: 0.75rem;
  text-align: center;
  font-weight: 500;
}

/* === Main Content === */
#content {
  padding: 12px 14px 32px;
}

/* === Search Section === */
#search-section {
  margin-bottom: 14px;
}

.search-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input-wrap {
  flex: 1;
  position: relative;
}

#search-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s;
}

#search-input:focus { border-color: var(--color-primary); }

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  max-height: 200px;
  overflow-y: auto;
  z-index: 50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.suggestions-dropdown.hidden { display: none; }

.suggestion-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.suggestion-item:last-child { border-bottom: none; }
.suggestion-item:hover { background: #f0f4ff; }
.suggestion-item .sugg-symbol { font-weight: 700; }
.suggestion-item .sugg-name { color: var(--color-text-secondary); font-size: 0.75rem; }

.btn-primary {
  background: var(--color-primary);
  color: #fff;
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  cursor: pointer;
  white-space: nowrap;
  font-weight: 600;
  transition: background 0.15s;
}

.btn-primary:active { background: #1565c0; }

.btn-ghost {
  background: transparent;
  border: 1px solid var(--color-border);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.btn-sm { padding: 6px 12px; font-size: 0.78rem; }

/* Add Form */
.add-form {
  margin-top: 8px;
  background: var(--color-card);
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.add-form.hidden { display: none; }

#add-symbol {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  outline: none;
}

.add-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  justify-content: flex-end;
}

/* === Section Title === */
.section-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid var(--color-primary);
  display: inline-block;
}

/* === Signals Area === */
#signals-section {
  margin-bottom: 18px;
}

#signals-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.signal-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: transform 0.1s;
}

.signal-card:active { transform: scale(0.98); }

.signal-card.buy { border-left: 4px solid var(--color-success); }
.signal-card.sell { border-left: 4px solid var(--color-danger); }
.signal-card.watch { border-left: 4px solid var(--color-warning); }

.signal-info { display: flex; align-items: center; gap: 8px; }
.signal-symbol { font-weight: 700; font-size: 0.9rem; }
.signal-name { color: var(--color-text-secondary); font-size: 0.75rem; }
.signal-change { font-weight: 600; }
.signal-change.up { color: var(--color-success); }
.signal-change.down { color: var(--color-danger); }

.signal-badge {
  font-size: 0.7rem;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.signal-badge.buy { background: var(--color-buy-bg); color: var(--color-success); }
.signal-badge.sell { background: var(--color-sell-bg); color: var(--color-danger); }
.signal-badge.watch { background: var(--color-watch-bg); color: var(--color-warning); }

/* === Industry Accordion === */
#industries-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.industry-group {
  background: var(--color-card);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.industry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.industry-header:active { background: #f9f9f9; }

.industry-name {
  font-weight: 700;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.industry-count {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  font-weight: 400;
}

.industry-change {
  font-weight: 600;
  font-size: 0.85rem;
}

.industry-change.up { color: var(--color-success); }
.industry-change.down { color: var(--color-danger); }

.industry-arrow {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  transition: transform 0.2s;
  margin-left: 4px;
}

.industry-group.open .industry-arrow { transform: rotate(180deg); }

.industry-stocks {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.industry-group.open .industry-stocks {
  max-height: 5000px;
}

.stock-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-top: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.1s;
  gap: 8px;
}

.stock-row:active { background: #f9f9f9; }

.stock-row-left { flex: 1; min-width: 0; }
.stock-row-symbol { font-weight: 700; font-size: 0.85rem; }
.stock-row-name { color: var(--color-text-secondary); font-size: 0.7rem; margin-left: 4px; }

.stock-row-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-row-price { font-weight: 600; font-size: 0.85rem; font-family: var(--font-mono); }
.stock-row-change { font-weight: 600; font-size: 0.78rem; font-family: var(--font-mono); }
.stock-row-change.up { color: var(--color-success); }
.stock-row-change.down { color: var(--color-danger); }

.stock-row-signal {
  font-size: 0.6rem;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.stock-row-signal.buy { background: var(--color-buy-bg); color: var(--color-success); }
.stock-row-signal.sell { background: var(--color-sell-bg); color: var(--color-danger); }
.stock-row-signal.watch { background: var(--color-watch-bg); color: var(--color-warning); }

/* === Detail Card (inside stock row expansion) === */
.stock-detail-wrap {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  border-top: none;
}

.stock-detail-wrap.open {
  max-height: 300px;
}

.detail-card {
  padding: 12px 14px;
  background: #fafbfc;
  border-top: 1px solid var(--color-border);
}

.detail-price-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.detail-symbol { font-weight: 700; font-size: 1rem; }
.detail-name { color: var(--color-text-secondary); font-size: 0.75rem; margin-left: 4px; }
.detail-close { font-size: 1.2rem; font-weight: 700; font-family: var(--font-mono); }
.detail-change { font-size: 0.85rem; font-weight: 600; margin-left: 6px; font-family: var(--font-mono); }
.detail-change.up { color: var(--color-success); }
.detail-change.down { color: var(--color-danger); }

.detail-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 6px;
  margin-bottom: 10px;
}

.metric {
  background: #f0f1f3;
  border-radius: var(--radius-sm);
  padding: 8px;
  text-align: center;
}

.metric-label { display: block; font-size: 0.6rem; color: var(--color-text-secondary); }
.metric-value { display: block; font-weight: 600; font-size: 0.8rem; margin-top: 2px; }

.detail-ma-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-top: 1px solid #eee;
  font-size: 0.75rem;
  gap: 4px;
  flex-wrap: wrap;
}

.ma-item { white-space: nowrap; }
.ma-item strong { color: var(--color-primary); font-size: 0.8rem; }
.ma-desc { color: var(--color-success); font-size: 0.65rem; }
.ma-desc.bearish { color: var(--color-danger); }
.ma-align { font-size: 0.65rem; }
.ma-align.bullish { color: var(--color-success); }
.ma-align.bearish { color: var(--color-danger); }

.detail-kdj-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid #eee;
  font-size: 0.75rem;
}

.kdj-label { color: var(--color-text-secondary); font-size: 0.65rem; }
.kdj-item {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.72rem;
}

.kdj-item.k-val { background: var(--color-blue-bg); color: var(--color-blue-text); }
.kdj-item.d-val { background: #f3e5f5; color: #7b1fa2; }
.kdj-item.j-val { background: var(--color-watch-bg); color: var(--color-warning); }

/* === Manage Modal === */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.modal-content {
  background: var(--color-card);
  border-radius: 16px 16px 0 0;
  width: 100%;
  max-width: var(--max-width);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  animation: slideUp 0.25s ease;
}

@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 { font-size: 1rem; }

.btn-close-modal {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 4px 8px;
}

.modal-body {
  padding: 14px;
  overflow-y: auto;
  flex: 1;
}

.manage-search { margin-bottom: 12px; }

.manage-filter {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  outline: none;
}

.manage-list { display: flex; flex-direction: column; }

.manage-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.manage-item-name { font-size: 0.85rem; }
.manage-item-symbol { font-weight: 700; }
.manage-item-desc { color: var(--color-text-secondary); font-size: 0.7rem; margin-left: 6px; }

.btn-delete {
  background: none;
  border: none;
  color: var(--color-danger);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.btn-delete:active { background: var(--color-sell-bg); }

.manage-batch {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 2px solid var(--color-border);
}

.batch-input {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  resize: vertical;
  outline: none;
}

.btn-batch-add {
  margin-top: 8px;
  width: 100%;
}

/* === Toast === */
#toast-container {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 300;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 90%;
  max-width: 400px;
}

.toast {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 500;
  text-align: center;
  animation: fadeIn 0.2s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.toast.success { background: var(--color-success); }
.toast.error { background: var(--color-danger); }
.toast.info { background: var(--color-primary); }

@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* === Empty State === */
.empty-state {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 24px 14px;
  font-size: 0.85rem;
}

.hidden { display: none !important; }

/* === Mobile Responsive === */
@media (max-width: 480px) {
  .detail-metrics {
    grid-template-columns: 1fr 1fr;
  }
  .top-row {
    padding: 8px 10px;
  }
  #content {
    padding: 10px 10px 24px;
  }
  .btn-text { display: none; }
  .status-bar { font-size: 0.7rem; padding: 6px 10px; }
}

/* === Scrollbar === */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #ccc; border-radius: 2px; }

/* === KDJ Status Colors === */
.overbought { color: var(--color-overbought); font-weight: 700; }
.oversold { color: var(--color-oversold); font-weight: 700; }
```

- [ ] **Step 2: Commit**

```bash
git add docs/css/app.css
git commit -m "feat: add complete stylesheet with mobile responsive"
```

---

### Task 5: indicators.js — Signal Detection & Formatting

**Files:**
- Create: `docs/js/indicators.js`

Utility functions for KDJ status interpretation, MA alignment judgment, signal classification, number formatting, market cap formatting.

- [ ] **Step 1: Write indicators.js**

```javascript
// indicators.js — KDJ/MA signal detection & formatting utilities

const Indicators = {

  /**
   * Interpret KDJ values and return status labels.
   * Returns { kStatus, dStatus, jStatus }
   */
  getKDJStatus(k, d, j) {
    return {
      kStatus: k > 80 ? '超买' : (k < 20 ? '超卖' : '正常'),
      dStatus: d > 80 ? '超买' : (d < 20 ? '超卖' : '正常'),
      jStatus: j > 100 ? '顶部风险' : (j < 0 ? '底部信号' : '正常'),
      kOverbought: k > 80,
      kOversold: k < 20,
      jTop: j > 100,
      jBottom: j < 0,
      goldenCross: k > d,    // K线上穿D线
      deathCross: k < d      // K线下穿D线
    };
  },

  /**
   * Judge MA alignment.
   * Returns { priceAboveMA5, priceAboveMA20, ma5AboveMA20, alignment }
   */
  getMAAlignment(close, ma5, ma20) {
    const priceAboveMA5 = close > ma5;
    const priceAboveMA20 = close > ma20;
    const ma5AboveMA20 = ma5 > ma20;
    let alignment = '整理中';
    if (priceAboveMA5 && ma5AboveMA20) alignment = '多头排列';
    else if (!priceAboveMA5 && !ma5AboveMA20) alignment = '空头排列';
    return { priceAboveMA5, priceAboveMA20, ma5AboveMA20, alignment };
  },

  /**
   * Detect trading signal based on KDJ + MA for V1.0 (simple rules).
   * V2.0 will add volume/options factors.
   */
  detectSignal(stock) {
    const { k, d, j, close, ma5, ma20 } = stock;
    const kdj = this.getKDJStatus(k, d, j);
    const ma = this.getMAAlignment(close, ma5, ma20);

    // Strong buy: K oversold recovery + golden cross + price above MA5
    if (kdj.kOversold && kdj.goldenCross && ma.priceAboveMA5) {
      return { signal: 'buy', strength: 'strong' };
    }
    // Mild buy: golden cross + bullish alignment
    if (kdj.goldenCross && ma.alignment === '多头排列') {
      return { signal: 'buy', strength: 'mild' };
    }
    // Watch: approaching overbought or golden cross alone
    if (kdj.goldenCross || (k > 70 && kdj.kOverbought === false)) {
      return { signal: 'watch', strength: null };
    }
    // Strong sell: K overbought + death cross + below MA5
    if (kdj.kOverbought && kdj.deathCross && !ma.priceAboveMA5) {
      return { signal: 'sell', strength: 'strong' };
    }
    // Mild sell: death cross + bearish alignment
    if (kdj.deathCross && ma.alignment === '空头排列') {
      return { signal: 'sell', strength: 'mild' };
    }
    // J bottom signal
    if (kdj.jBottom) {
      return { signal: 'watch', strength: null };
    }
    return { signal: null, strength: null };
  },

  /** Format large number to human-readable */
  formatVolume(vol) {
    if (vol >= 1e9) return (vol / 1e9).toFixed(2) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
    return String(vol);
  },

  /** Format market cap */
  formatMarketCap(mcap) {
    if (mcap >= 1e12) return (mcap / 1e12).toFixed(2) + 'T';
    if (mcap >= 1e9) return (mcap / 1e9).toFixed(0) + 'B';
    if (mcap >= 1e6) return (mcap / 1e6).toFixed(0) + 'M';
    return String(mcap);
  },

  /** Format percentage change with sign */
  formatChange(pct) {
    const sign = pct > 0 ? '+' : '';
    return sign + pct.toFixed(2) + '%';
  },

  /** Format price to 2 decimal places */
  formatPrice(p) {
    return p.toFixed(2);
  },

  /** Get CSS class for change direction */
  changeClass(pct) {
    return pct > 0 ? 'up' : (pct < 0 ? 'down' : '');
  },

  /** Get signal display text */
  signalText(signal) {
    const map = { buy: '建议买入', sell: '建议卖出', watch: '建议观察' };
    return map[signal] || '';
  },

  /** Format date string */
  formatDate(d) {
    const dt = new Date(d);
    const m = String(dt.getMonth() + 1).padStart(2, '0');
    const day = String(dt.getDate()).padStart(2, '0');
    const h = String(dt.getHours()).padStart(2, '0');
    const min = String(dt.getMinutes()).padStart(2, '0');
    return `${m}-${day} ${h}:${min}`;
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add docs/js/indicators.js
git commit -m "feat: add indicators.js with signal detection and formatting"
```

---

### Task 6: app.js — Core Application Logic

**Files:**
- Create: `docs/js/app.js`

All application logic: data loading, filtering by watchlist, rendering signals, industry accordion, stock detail expansion, search, add/remove management, manual refresh, modal, toast.

- [ ] **Step 1: Write app.js part 1 — State & Init**

```javascript
// app.js — US Stocks Monitor Core Application

const App = {
  // === State ===
  allStocks: [],          // All stocks from stocks.json
  watchlist: [],          // User's selected symbols (from localStorage)
  filteredSymbols: null,  // Current search filter (null = show all)
  expandStock: null,      // Currently expanded stock symbol
  refreshCount: 10,       // Remaining manual force-refresh count today

  // === Init ===
  async init() {
    this.loadWatchlist();
    this.loadRefreshCount();
    await this.fetchData();
    this.bindEvents();
    this.render();
  },

  // === Helpers ===
  $(sel) { return document.querySelector(sel); },
  $$(sel) { return document.querySelectorAll(sel); },

  // === Data Loading ===
  async fetchData(forceRefresh = false) {
    try {
      const ts = Date.now();
      const url = forceRefresh
        ? `data/stocks.json?t=${ts}`
        : 'data/stocks.json';
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const json = await resp.json();
      this.allStocks = json.stocks || [];
      // Apply stored signals for V1.0 (use data signals, fall back to detection)
      this.allStocks.forEach(s => {
        s._signal = s.signal || null;
        if (!s._signal) {
          const detected = Indicators.detectSignal(s);
          s._signal = detected.signal;
          s._signalStrength = detected.strength;
        }
      });
      this.updateTime = json.updated_at;
      this.dataDate = json.data_date;
      this.lastFetchOk = true;
    } catch (err) {
      console.error('Failed to fetch stocks.json:', err);
      this.lastFetchOk = false;
      if (this.allStocks.length === 0) {
        this.toast('无法加载数据，请稍后重试', 'error');
      }
    }
  },

  /** Load watchlist from localStorage. If empty, seed with sample stocks. */
  loadWatchlist() {
    try {
      const raw = localStorage.getItem('us_watchlist');
      this.watchlist = raw ? JSON.parse(raw) : [];
    } catch(e) {
      this.watchlist = [];
    }
    // Seed with defaults on first visit
    if (this.watchlist.length === 0) {
      this.watchlist = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
                        'META', 'JPM', 'BAC', 'GS', 'JNJ', 'PFE', 'UNH', 'NEE', 'XOM'];
      this.saveWatchlist();
    }
  },

  saveWatchlist() {
    localStorage.setItem('us_watchlist', JSON.stringify(this.watchlist));
  },

  loadRefreshCount() {
    const today = new Date().toDateString();
    const stored = localStorage.getItem('us_refresh_date');
    if (stored === today) {
      this.refreshCount = parseInt(localStorage.getItem('us_refresh_count') || '10');
    } else {
      this.refreshCount = 10;
      localStorage.setItem('us_refresh_date', today);
      localStorage.setItem('us_refresh_count', '10');
    }
  },

  saveRefreshCount() {
    localStorage.setItem('us_refresh_count', String(this.refreshCount));
  },

  /** Get stocks filtered by user's watchlist, then by search */
  getFilteredStocks() {
    let list = this.allStocks.filter(s => this.watchlist.includes(s.symbol));
    if (this.filteredSymbols) {
      list = list.filter(s => this.filteredSymbols.includes(s.symbol));
    }
    return list;
  },

  /** Group stocks by sector, sorted by market cap desc within each group */
  groupBySector(stocks) {
    const groups = {};
    stocks.forEach(s => {
      const sec = s.sector || '其他';
      if (!groups[sec]) groups[sec] = [];
      groups[sec].push(s);
    });
    // Sort stocks within each sector by market cap desc
    Object.values(groups).forEach(arr => {
      arr.sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0));
    });
    return groups;
  }
};
```

- [ ] **Step 2: Write app.js part 2 — Rendering**

```javascript
// === Rendering ===
App.render = function() {
  this.updateStatusBar();
  this.renderSignals();
  this.renderIndustries();
};

/** Update data freshness bar */
App.prototype.updateStatusBar = function() {
  const el = this.$('#update-time');
  if (this.updateTime) {
    const dt = new Date(this.updateTime);
    const dateStr = dt.toLocaleDateString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit' });
    const timeStr = dt.toLocaleTimeString('zh-CN', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    el.textContent = `${dateStr} ${timeStr}`;
  } else {
    el.textContent = '暂无数据';
  }
  this.$('#refresh-count').textContent = `剩${this.refreshCount}次`;
};

/** Render signal cards */
App.prototype.renderSignals = function() {
  const stocks = this.getFilteredStocks();
  const signals = stocks.filter(s => s._signal && s._signal !== 'watch');
  // Also include watch signals
  const watchStocks = stocks.filter(s => s._signal === 'watch');

  const list = this.$('#signals-list');
  const empty = this.$('#signals-empty');
  list.innerHTML = '';

  const allSignals = [...signals, ...watchStocks];

  if (allSignals.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  allSignals.forEach(stock => {
    const card = document.createElement('div');
    card.className = `signal-card ${stock._signal}`;
    card.innerHTML = `
      <div class="signal-info">
        <span class="signal-symbol">${stock.symbol}</span>
        <span class="signal-name">${stock.name || ''}</span>
        <span class="signal-change ${Indicators.changeClass(stock.change_pct)}">
          ${Indicators.formatChange(stock.change_pct)}
        </span>
      </div>
      <span class="signal-badge ${stock._signal}">${Indicators.signalText(stock._signal)}</span>
    `;
    card.addEventListener('click', () => this.scrollToStock(stock.symbol));
    list.appendChild(card);
  });
};

/** Render industry accordion */
App.prototype.renderIndustries = function() {
  const stocks = this.getFilteredStocks();
  const container = this.$('#industries-list');
  const empty = this.$('#industries-empty');

  container.innerHTML = '';

  if (stocks.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  const groups = this.groupBySector(stocks);

  Object.entries(groups).forEach(([sector, sectorStocks]) => {
    const avgChange = sectorStocks.reduce((sum, s) => sum + (s.change_pct || 0), 0) / sectorStocks.length;

    const groupEl = document.createElement('div');
    groupEl.className = 'industry-group open'; // default open
    groupEl.innerHTML = `
      <div class="industry-header">
        <span class="industry-name">
          ${this.sectorIcon(sector)} ${sector}
          <span class="industry-count">${sectorStocks.length}只</span>
        </span>
        <span>
          <span class="industry-change ${Indicators.changeClass(avgChange)}">
            ${Indicators.formatChange(avgChange)}
          </span>
          <span class="industry-arrow">▼</span>
        </span>
      </div>
      <div class="industry-stocks">
        ${sectorStocks.map(s => this.stockRowHTML(s)).join('')}
      </div>
    `;

    // Toggle accordion
    const header = groupEl.querySelector('.industry-header');
    header.addEventListener('click', () => {
      groupEl.classList.toggle('open');
    });

    container.appendChild(groupEl);
  });

  // Attach stock row events
  this.$$('.stock-row').forEach(row => {
    row.addEventListener('click', (e) => {
      // Don't toggle detail if clicking on a nested interactive element
      const symbol = row.dataset.symbol;
      this.toggleDetail(symbol, row);
    });
  });
};

App.prototype.sectorIcon = function(sector) {
  const map = { '科技': '💻', '金融': '🏦', '医疗': '🏥', '能源': '⚡', '消费': '🛒', '工业': '🏭', '房地产': '🏠', '通讯': '📡' };
  return map[sector] || '📌';
};

App.prototype.stockRowHTML = function(stock) {
  const chgClass = Indicators.changeClass(stock.change_pct);
  const signalBadge = stock._signal
    ? `<span class="stock-row-signal ${stock._signal}">${Indicators.signalText(stock._signal)}</span>`
    : '';
  return `
    <div class="stock-row" data-symbol="${stock.symbol}">
      <div class="stock-row-left">
        <span class="stock-row-symbol">${stock.symbol}</span>
        <span class="stock-row-name">${stock.name || ''}</span>
      </div>
      <div class="stock-row-right">
        <span class="stock-row-price">$${Indicators.formatPrice(stock.close)}</span>
        <span class="stock-row-change ${chgClass}">${Indicators.formatChange(stock.change_pct)}</span>
        ${signalBadge}
      </div>
    </div>
    <div class="stock-detail-wrap" id="detail-${stock.symbol}">
      <div class="detail-card"></div>
    </div>
  `;
};
```

- [ ] **Step 3: Write app.js part 3 — Detail Expansion**

```javascript
/** Toggle stock detail card */
App.prototype.toggleDetail = function(symbol, rowEl) {
  const wrapEl = this.$(`#detail-${symbol}`);
  if (!wrapEl) return;

  const isOpen = wrapEl.classList.contains('open');

  // Close all others
  this.$$('.stock-detail-wrap.open').forEach(el => el.classList.remove('open'));

  if (!isOpen) {
    // Build detail content
    const stock = this.allStocks.find(s => s.symbol === symbol);
    if (!stock) return;

    const card = wrapEl.querySelector('.detail-card');
    if (!card) return;

    const kdj = Indicators.getKDJStatus(stock.k, stock.d, stock.j);
    const ma = Indicators.getMAAlignment(stock.close, stock.ma5, stock.ma20);
    const chgClass = Indicators.changeClass(stock.change_pct);

    card.innerHTML = `
      <div class="detail-price-row">
        <div class="detail-header">
          <span class="detail-symbol">${stock.symbol}</span>
          <span class="detail-name">${stock.name || ''}</span>
        </div>
        <div class="detail-price-info">
          <span class="detail-close">$${Indicators.formatPrice(stock.close)}</span>
          <span class="detail-change ${chgClass}">${Indicators.formatChange(stock.change_pct)}</span>
        </div>
      </div>
      <div class="detail-metrics">
        <div class="metric">
          <span class="metric-label">昨收</span>
          <span class="metric-value">$${Indicators.formatPrice(stock.prev_close)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">开盘</span>
          <span class="metric-value">$${Indicators.formatPrice(stock.open)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">成交量</span>
          <span class="metric-value">${Indicators.formatVolume(stock.volume)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">市值</span>
          <span class="metric-value">${Indicators.formatMarketCap(stock.market_cap)}</span>
        </div>
      </div>
      <div class="detail-metrics" style="margin-top:0;">
        <div class="metric">
          <span class="metric-label">最高</span>
          <span class="metric-value">$${Indicators.formatPrice(stock.high)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">最低</span>
          <span class="metric-value">$${Indicators.formatPrice(stock.low)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">成交均价</span>
          <span class="metric-value">$${Indicators.formatPrice(stock.vwap)}</span>
        </div>
        <div class="metric">
          <span class="metric-label">数据日期</span>
          <span class="metric-value">${this.dataDate || '-'}</span>
        </div>
      </div>
      <div class="detail-ma-row">
        <span class="ma-item">MA5 <strong>$${Indicators.formatPrice(stock.ma5)}</strong></span>
        <span class="ma-desc ${ma.priceAboveMA5 ? '' : 'bearish'}">
          ${ma.priceAboveMA5 ? '⬆ 价格在MA5上方' : '⬇ 价格在MA5下方'}
        </span>
        <span class="ma-item">MA20 <strong>$${Indicators.formatPrice(stock.ma20)}</strong></span>
        <span class="ma-align ${ma.alignment === '多头排列' ? 'bullish' : (ma.alignment === '空头排列' ? 'bearish' : '')}">
          ${ma.alignment === '多头排列' ? '⬆ 多头排列' : (ma.alignment === '空头排列' ? '⬇ 空头排列' : ma.alignment)}
        </span>
      </div>
      <div class="detail-kdj-row">
        <span class="kdj-label">KDJ</span>
        <span class="kdj-item k-val ${stock.k > 80 ? 'overbought' : (stock.k < 20 ? 'oversold' : '')}">
          K: ${stock.k.toFixed(1)}
        </span>
        <span class="kdj-item d-val">
          D: ${stock.d.toFixed(1)}
        </span>
        <span class="kdj-item j-val ${stock.j > 100 ? 'overbought' : (stock.j < 0 ? 'oversold' : '')}">
          J: ${stock.j.toFixed(1)}
        </span>
      </div>
    `;

    wrapEl.classList.add('open');
    // Scroll into view smoothly
    setTimeout(() => {
      wrapEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }
};

/** Scroll to a stock's row and expand it */
App.prototype.scrollToStock = function(symbol) {
  const row = document.querySelector(`.stock-row[data-symbol="${symbol}"]`);
  if (!row) return;
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  this.toggleDetail(symbol, row);
};
```

- [ ] **Step 4: Write app.js part 4 — Search, Add, Remove, Refresh, Toast**

```javascript
// === Search ===
App.prototype.onSearchInput = function(e) {
  const query = e.target.value.trim().toUpperCase();
  if (!query) {
    this.filteredSymbols = null;
    this.render();
    return;
  }
  // Filter watchlist symbols matching query
  const matches = this.watchlist.filter(sym => {
    const stock = this.allStocks.find(s => s.symbol === sym);
    return sym.includes(query) || (stock && stock.name && stock.name.includes(query));
  });
  this.filteredSymbols = matches.length ? matches : ['__NONE__'];
  this.render();
};

// === Add Stock ===
App.prototype.showAddForm = function() {
  const form = this.$('#add-form');
  form.classList.remove('hidden');
  this.$('#add-symbol').focus();
};

App.prototype.hideAddForm = function() {
  this.$('#add-form').classList.add('hidden');
  this.$('#add-symbol').value = '';
};

App.prototype.confirmAdd = function() {
  const symbol = this.$('#add-symbol').value.trim().toUpperCase();
  if (!symbol) {
    this.toast('请输入美股代码', 'info');
    return;
  }
  if (this.watchlist.includes(symbol)) {
    this.toast(`${symbol} 已经在自选列表中`, 'info');
    return;
  }
  // Check if symbol exists in our data
  const exists = this.allStocks.find(s => s.symbol === symbol);
  if (!exists) {
    this.toast(`${symbol} 不在数据源中，但已添加到监控列表`, 'info');
  }
  this.watchlist.unshift(symbol);
  this.saveWatchlist();
  this.hideAddForm();
  this.render();
  this.toast(`${symbol} 已添加到自选`, 'success');
};

// === Remove Stock ===
App.prototype.removeStock = function(symbol) {
  this.watchlist = this.watchlist.filter(s => s !== symbol);
  this.saveWatchlist();
  this.render();
  this.toast(`${symbol} 已从自选移除`, 'info');
};

// === Manual Refresh ===
App.prototype.onRefresh = async function() {
  this.toast('正在刷新数据...', 'info');
  await this.fetchData(true);
  if (this.lastFetchOk) {
    this.render();
    this.toast('数据已刷新', 'success');
  } else {
    this.toast('数据刷新失败，请检查网络', 'error');
  }
};

// === Manage Modal ===
App.prototype.showManageModal = function() {
  const existing = document.querySelector('.modal-overlay');
  if (existing) existing.remove();

  const tmpl = this.$('#tmpl-manage-modal');
  const clone = tmpl.content.cloneNode(true);
  document.body.appendChild(clone);

  const overlay = document.querySelector('.modal-overlay');
  const list = overlay.querySelector('.manage-list');
  const filterInput = overlay.querySelector('.manage-filter');
  const batchInput = overlay.querySelector('.batch-input');

  // Render watchlist
  const renderManageList = (filter = '') => {
    list.innerHTML = '';
    const q = filter.toUpperCase();
    const filtered = this.watchlist.filter(sym => !q || sym.includes(q));
    if (filtered.length === 0) {
      overlay.querySelector('.manage-empty').classList.remove('hidden');
    } else {
      overlay.querySelector('.manage-empty').classList.add('hidden');
    }
    filtered.forEach(sym => {
      const stock = this.allStocks.find(s => s.symbol === sym);
      const item = document.createElement('div');
      item.className = 'manage-item';
      item.innerHTML = `
        <div class="manage-item-name">
          <span class="manage-item-symbol">${sym}</span>
          <span class="manage-item-desc">${stock ? stock.name : '未知'}</span>
        </div>
        <button class="btn-delete" data-symbol="${sym}">✕</button>
      `;
      item.querySelector('.btn-delete').addEventListener('click', () => {
        this.removeStock(sym);
        renderManageList(filterInput.value);
        // Update batch textarea too
      });
      list.appendChild(item);
    });
  };

  renderManageList();

  filterInput.addEventListener('input', (e) => renderManageList(e.target.value));

  // Batch add
  overlay.querySelector('.btn-batch-add').addEventListener('click', () => {
    const raw = batchInput.value.trim();
    if (!raw) return;
    const symbols = raw.split(/[\n,;]+/).map(s => s.trim().toUpperCase()).filter(Boolean);
    let added = 0;
    symbols.forEach(sym => {
      if (!this.watchlist.includes(sym)) {
        this.watchlist.unshift(sym);
        added++;
      }
    });
    if (added > 0) {
      this.saveWatchlist();
      renderManageList(filterInput.value);
      batchInput.value = '';
      this.toast(`已添加 ${added} 只股票`, 'success');
    } else {
      this.toast('所有代码已在自选列表中', 'info');
    }
  });

  // Close
  overlay.querySelector('.btn-close-modal').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
};

// === Toast ===
App.prototype.toast = function(msg, type = 'info') {
  const container = this.$('#toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 2000);
};
```

- [ ] **Step 5: Write app.js part 5 — Event Binding & Bootstrap**

```javascript
// === Event Binding ===
App.prototype.bindEvents = function() {
  // Search input
  this.$('#search-input').addEventListener('input', (e) => this.onSearchInput(e));

  // Add button
  this.$('#btn-add').addEventListener('click', () => this.showAddForm());
  this.$('#btn-confirm-add').addEventListener('click', () => this.confirmAdd());
  this.$('#btn-cancel-add').addEventListener('click', () => this.hideAddForm());

  // Enter key in add input
  this.$('#add-symbol').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') this.confirmAdd();
    if (e.key === 'Escape') this.hideAddForm();
  });

  // Refresh button
  this.$('#btn-refresh').addEventListener('click', () => this.onRefresh());

  // Manage modal
  this.$('#btn-manage').addEventListener('click', () => this.showManageModal());

  // Escape key to close add form
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      this.hideAddForm();
      const modal = document.querySelector('.modal-overlay');
      if (modal) modal.remove();
    }
  });
};
```

- [ ] **Step 6: Write the bootstrap at the bottom of app.js**

```javascript
// === Bootstrap ===
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
```

- [ ] **Step 7: Commit**

```bash
git add docs/js/app.js
git commit -m "feat: add core app logic - rendering, search, signals, detail, manage, refresh"
```

---

### Task 7: Python Data Fetch Script

**Files:**
- Create: `scripts/fetch_and_calc.py`
- Create: `scripts/requirements.txt`

- [ ] **Step 1: Write requirements.txt**

```
akshare>=1.12.0
pandas>=2.0.0
numpy>=1.24.0
```

- [ ] **Step 2: Write fetch_and_calc.py**

```python
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

# Sector mapping
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
```

- [ ] **Step 3: Commit**

```bash
git add scripts/requirements.txt scripts/fetch_and_calc.py
git commit -m "feat: add Python data fetcher with akshare and KDJ/MA calculation"
```

---

### Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily-update.yml`

- [ ] **Step 1: Write workflow YAML**

```yaml
name: Daily Stock Data Update

on:
  schedule:
    # UTC 00:00 = Beijing 08:00
    - cron: '0 0 * * 1-5'   # Weekdays only (Mon-Fri, US market days)
  workflow_dispatch:          # Manual trigger via GitHub UI

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r scripts/requirements.txt

      - name: Fetch stock data
        run: python scripts/fetch_and_calc.py
        env:
          PYTHONUNBUFFERED: 1

      - name: Commit and push updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data/stocks.json
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "data: daily update $(date +%Y-%m-%d)"
            git push
          fi

      - name: Send pushplus notification
        if: success()
        env:
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
        run: |
          # Count stats from stocks.json
          STOCKS=$(cat docs/data/stocks.json | python -c "
  import json, sys
  data = json.load(sys.stdin)
  stocks = data['stocks']
  up = sum(1 for s in stocks if s['change_pct'] > 0)
  down = sum(1 for s in stocks if s['change_pct'] < 0)
  flat = sum(1 for s in stocks if s['change_pct'] == 0)
  # Build summary
  lines = []
  # Signals
  buy_stocks = [s for s in stocks if s.get('_signal') == 'buy' or s.get('signal') == 'buy']
  if buy_stocks:
      lines.append('📈 建议买入:')
      for s in buy_stocks[:5]:
          lines.append(f\"  {s['symbol']} {s.get('name','')} {s['change_pct']:+.2f}%\")
  # Sector summary
  sectors = {}
  for s in stocks:
      sec = s.get('sector', '其他')
      if sec not in sectors:
          sectors[sec] = {'count': 0, 'total_change': 0}
      sectors[sec]['count'] += 1
      sectors[sec]['total_change'] += s['change_pct']
  if sectors:
      lines.append('📊 行业表现:')
      for sec, info in sorted(sectors.items()):
          avg = info['total_change'] / info['count']
          lines.append(f\"  {sec}: {info['count']}只 | {avg:+.2f}%\")
  lines.append(f'📋 共{len(stocks)}只 | 涨{up} 跌{down} 平{flat}')
  lines.append(f'详情 → ${{ github.server_url }}/${{ github.repository }}')
  print('||'.join(lines))
  ")
          # Send via pushplus
          TITLE="【美股晨报】$(date +%Y-%m-%d)"
          curl -s -X POST "http://www.pushplus.plus/send" \
            -H "Content-Type: application/json" \
            -d "{\"token\":\"${PUSHPLUS_TOKEN}\",\"title\":\"${TITLE}\",\"content\":\"${STOCKS//\"/\\\"}\"}"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily-update.yml
git commit -m "feat: add GitHub Actions workflow for daily data update + pushplus"
```

---

### Task 9: README & Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# 美股自选股监控系统

个人美股自选股每日监控，基于 akshare 数据 + GitHub Actions 定时更新 + GitHub Pages 展示 + pushplus 微信推送。

## 功能

- 📊 自选股数据展示：开盘/收盘/昨收、涨跌幅、成交量、成交均价、MA5/MA20、KDJ
- 🏭 按行业分组，市值排序
- 🎯 买卖信号识别（基于 KDJ + MA）
- 🔄 每日早晨 8:00（北京时间）自动更新数据
- 📱 移动端适配
- 📲 pushplus 微信晨报推送

## 使用方式

### 前端
访问 `https://<your-username>.github.io/<repo-name>/`

### 自选股管理
- 点击「+ 添加」输入美股代码
- 点击 ⚙ 进入管理面板，支持批量添加和删除
- 自选股列表保存在浏览器 localStorage

### 手动刷新
点击「🔄 刷新」按钮（每日限 10 次强制更新）

## 部署

1. Fork 或创建 GitHub 仓库
2. 在仓库 Settings → Pages 中启用 GitHub Pages，选择 `docs/` 目录
3. 在 Settings → Secrets → Actions 中添加 `PUSHPLUS_TOKEN`
4. GitHub Actions 会在每个交易日 UTC 00:00 自动运行

## 自定义自选股

编辑 `scripts/watchlist.txt`，每行一个股票代码：
```
AAPL
NVDA
MSFT
```

## 技术栈

- 前端：HTML + CSS + Vanilla JS
- 数据：akshare (Python)
- 定时：GitHub Actions
- 推送：pushplus
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

### Task 10: Integration Test — Open in Browser

- [ ] **Step 1: Start a simple HTTP server and verify the page loads**

```bash
cd docs
python -m http.server 8080
```

- [ ] **Step 2: Open browser and verify:**
  - Top bar with title and action buttons
  - Blue status bar with data timestamp
  - Search bar and Add button
  - Signal area showing stocks with buy/sell/watch signals
  - Industry accordion with 4 sectors (科技, 金融, 医疗, 能源)
  - Click industry header to collapse/expand
  - Click stock row to expand detail card with all metrics
  - Click ⚙ to open management modal
  - Delete a stock, verify it disappears from list
  - Add a new stock code, verify it appears
  - Test refresh button
  - Resize to mobile width and verify responsive layout

- [ ] **Step 3: If everything works, commit any fixes**

```bash
git add -A
git commit -m "chore: integration fixes and polish"
```
