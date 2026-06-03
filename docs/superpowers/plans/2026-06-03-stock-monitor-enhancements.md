# Stock Monitor Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sidebar navigation, enriched card indicators, user-defined industries, and expanded detail analysis to the US stocks monitor.

**Architecture:** Add a fixed left sidebar for industry filtering, enhance card rendering with MA/KDJ/golden-cross indicators, make industries user-defined via localStorage, and add five analysis sections to the expanded detail view. All client-side; no backend changes needed beyond making SECTORS a fallback.

**Tech Stack:** Vanilla HTML/CSS/JS, localStorage for persistence

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `docs/js/indicators.js` | Modify | Add analysis functions (volume, KDJ interpretation, MA interpretation, summary) |
| `docs/index.html` | Modify | Add sidebar markup, update add-form with industry field, update detail template |
| `docs/css/app.css` | Modify | Sidebar layout, enhanced card styles, analysis section styles, responsive |
| `docs/js/app.js` | Modify | Sidebar rendering, industry management, enhanced card rendering, detail expansion |
| `scripts/fetch_and_calc.py` | Modify | Add comment that SECTORS is fallback; frontend overrides industry |

---

### Task 1: Add analysis functions to indicators.js

**Files:**
- Modify: `docs/js/indicators.js`

- [ ] **Step 1: Add volume analysis function**

Add to the `Indicators` object before the closing `};`:

```javascript
  /**
   * Analyze volume: compare current volume to recent average.
   * Returns { ratio, label, color }
   */
  analyzeVolume(currentVolume, avgVolume) {
    if (!avgVolume || avgVolume === 0) return { ratio: null, label: '无对比数据', color: '' };
    const ratio = currentVolume / avgVolume;
    let label, color;
    if (ratio > 1.5) { label = '放量'; color = 'up'; }
    else if (ratio > 1.1) { label = '温和放量'; color = 'up'; }
    else if (ratio < 0.5) { label = '缩量'; color = 'down'; }
    else if (ratio < 0.8) { label = '温和缩量'; color = 'down'; }
    else { label = '正常'; color = ''; }
    return { ratio: parseFloat(ratio.toFixed(2)), label, color };
  },

  /**
   * Full KDJ analysis returning interpretive text.
   */
  analyzeKDJ(k, d, j) {
    const status = this.getKDJStatus(k, d, j);
    const parts = [];
    // Overbought/oversold
    if (status.kOverbought) parts.push('K值处于超买区(>80)，短期有回调风险');
    else if (status.kOversold) parts.push('K值处于超卖区(<20)，短期有反弹机会');
    else parts.push('K值处于正常区间');
    // Cross
    if (status.goldenCross) parts.push('K线上穿D线形成金叉，短期看多信号');
    else if (status.deathCross) parts.push('K线下穿D线形成死叉，短期看空信号');
    else parts.push('K线与D线未形成交叉');
    // J value
    if (status.jTop) parts.push('J值>100，顶部风险警示');
    else if (status.jBottom) parts.push('J值<0，底部超卖信号');
    return parts.join('；') + '。';
  },

  /**
   * MA5 short-term trend analysis.
   */
  analyzeMA5(close, ma5, prevClose) {
    if (!ma5) return 'MA5数据不可用。';
    const aboveMA5 = close > ma5;
    const pctFromMA5 = ((close - ma5) / ma5 * 100).toFixed(2);
    const direction = aboveMA5 ? '上方' : '下方';
    const strength = Math.abs(parseFloat(pctFromMA5)) > 3 ? '显著' : '小幅';
    const trend = prevClose && close > prevClose ? '上涨' : (close < prevClose ? '下跌' : '持平');
    return `股价在MA5${direction}${pctFromMA5}%，${strength}${aboveMA5 ? '偏离' : '跌破'}；当日${trend}。`;
  },

  /**
   * MA20 medium-term trend analysis.
   */
  analyzeMA20(close, ma20, ma5) {
    if (!ma20) return 'MA20数据不可用。';
    const aboveMA20 = close > ma20;
    const pctFromMA20 = ((close - ma20) / ma20 * 100).toFixed(2);
    const direction = aboveMA20 ? '上方' : '下方';
    const ma = this.getMAAlignment(close, ma5, ma20);
    const arrangement = ma.alignment === '多头排列' ? '多头排列，中期趋势向好' :
                        ma.alignment === '空头排列' ? '空头排列，中期趋势偏弱' : '均线交织，趋势不明朗';
    return `股价在MA20${direction}${pctFromMA20}%；${arrangement}。`;
  },

  /**
   * Generate comprehensive summary from all indicators.
   */
  generateSummary(stock) {
    const { close, ma5, ma20, k, d, j, change_pct } = stock;
    const kdj = this.getKDJStatus(k, d, j);
    const ma = this.getMAAlignment(close, ma5, ma20);
    const points = [];
    // Trend assessment
    if (ma.alignment === '多头排列' && kdj.goldenCross) {
      points.push('技术面偏多，均线多头排列且KDJ金叉，短期有上行动力');
    } else if (ma.alignment === '空头排列' && kdj.deathCross) {
      points.push('技术面偏空，均线空头排列且KDJ死叉，短期承压');
    } else if (ma.alignment === '多头排列' && !kdj.deathCross) {
      points.push('中期趋势向好但短期指标中性，可关注回调机会');
    } else if (ma.alignment === '空头排列' && !kdj.goldenCross) {
      points.push('中期趋势偏弱，建议等待明确反转信号');
    } else {
      points.push('技术指标多空交织，趋势不明朗，建议观望');
    }
    // Overbought/oversold
    if (kdj.kOverbought) points.push('注意KDJ超买风险，追高需谨慎');
    if (kdj.kOversold) points.push('KDJ超卖，可能存在超跌反弹机会');
    // Price action
    if (change_pct > 2) points.push('当日涨幅较大，短期获利盘可能回吐');
    if (change_pct < -2) points.push('当日跌幅较大，恐慌情绪可能过度');
    return points.join('；') + '。';
  },

  /**
   * Check if golden cross is currently active (K > D).
   */
  hasGoldenCross(k, d) {
    return k > d;
  }
```

- [ ] **Step 2: Verify the file syntax**

Run: `node --check docs/js/indicators.js`

---

### Task 2: Update index.html with sidebar, industry field, and enhanced templates

**Files:**
- Modify: `docs/index.html`

- [ ] **Step 1: Replace the entire `<body>` content**

Replace everything from `<body>` to `</body>` with:

```html
<body>

<!-- Left Sidebar -->
<nav id="sidebar">
  <div class="sidebar-header">
    <span class="sidebar-logo">📈</span>
    <span class="sidebar-title">美股自选</span>
  </div>
  <ul class="sidebar-nav">
    <li class="sidebar-item active" data-nav="signals">
      <span class="sidebar-icon">🎯</span>
      <span>今日信号</span>
      <span id="sidebar-signal-count" class="sidebar-badge hidden">0</span>
    </li>
    <li class="sidebar-divider"></li>
  </ul>
  <div id="sidebar-industries" class="sidebar-industries">
    <!-- Dynamically filled -->
  </div>
</nav>

<!-- Main Content Area -->
<div id="main-wrap">

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
      <input type="text" id="add-industry" placeholder="输入行业，如 科技、AI芯片" autocomplete="off" class="add-industry-input">
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

</div><!-- /#main-wrap -->

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
          <textarea placeholder="批量添加代码&#10;格式: 代码,行业&#10;如：&#10;AAPL,科技&#10;NVDA,AI芯片&#10;MSFT,科技" class="batch-input" rows="6"></textarea>
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
```

---

### Task 3: Rewrite app.css with sidebar layout and new styles

**Files:**
- Modify: `docs/css/app.css`

- [ ] **Step 1: Replace entire CSS file**

Replace the entire content of `docs/css/app.css` with:

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
  --sidebar-width: 170px;
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
  display: flex;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* === Sidebar === */
#sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  z-index: 150;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-logo { font-size: 1.2rem; }
.sidebar-title { font-weight: 700; font-size: 0.9rem; color: #fff; }

.sidebar-nav {
  list-style: none;
  padding: 8px 0;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.15s;
  color: #b0b0c0;
}

.sidebar-item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.sidebar-item.active { background: rgba(255,255,255,0.12); color: #fff; border-left: 3px solid var(--color-primary); padding-left: 11px; }

.sidebar-icon { font-size: 0.9rem; }

.sidebar-badge {
  margin-left: auto;
  background: var(--color-danger);
  color: #fff;
  font-size: 0.6rem;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.08);
  margin: 4px 14px;
}

.sidebar-industries {
  flex: 1;
  overflow-y: auto;
}

.sidebar-industry-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 0.75rem;
  color: #b0b0c0;
  transition: background 0.15s;
}

.sidebar-industry-item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.sidebar-industry-item.active { background: rgba(255,255,255,0.12); color: #fff; border-left: 3px solid var(--color-success); padding-left: 11px; }

.sidebar-industry-icon { font-size: 0.8rem; }
.sidebar-industry-count { margin-left: auto; font-size: 0.65rem; color: #888; }

/* === Main Wrap === */
#main-wrap {
  margin-left: var(--sidebar-width);
  flex: 1;
  min-width: 0;
  max-width: 768px;
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

#add-symbol, .add-industry-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  outline: none;
}

.add-industry-input { margin-top: 6px; }

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
  flex-direction: column;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--color-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: transform 0.1s;
  gap: 6px;
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

/* Signal indicator row */
.signal-indicators {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.7rem;
  flex-wrap: wrap;
}

.sig-ind {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 1px 5px;
  border-radius: 3px;
  background: #f5f5f5;
}

.sig-ind.bull { color: var(--color-success); }
.sig-ind.bear { color: var(--color-danger); }
.sig-ind.golden { background: #fff9c4; color: #f57f17; font-weight: 700; }

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
  flex-direction: column;
  padding: 10px 14px;
  border-top: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.1s;
  gap: 4px;
}

.stock-row:active { background: #f9f9f9; }

.stock-row-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

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

/* Stock row indicator bar */
.stock-indicators {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.68rem;
  flex-wrap: wrap;
}

.stock-ind {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.stock-ind.bull { color: var(--color-success); }
.stock-ind.bear { color: var(--color-danger); }
.stock-ind.golden { background: #fff9c4; color: #f57f17; font-weight: 700; padding: 0 4px; border-radius: 3px; }

/* === Detail Card (inside stock row expansion) === */
.stock-detail-wrap {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.4s ease;
  border-top: none;
}

.stock-detail-wrap.open {
  max-height: 900px;
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

/* === Detail Analysis Sections === */
.detail-analysis {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 2px solid var(--color-primary);
}

.analysis-section {
  margin-bottom: 8px;
  padding: 10px 12px;
  background: #fff;
  border-radius: var(--radius-sm);
  border-left: 3px solid #ddd;
}

.analysis-section.volume { border-left-color: #ff9800; }
.analysis-section.kdj { border-left-color: #9c27b0; }
.analysis-section.ma5 { border-left-color: #2196f3; }
.analysis-section.ma20 { border-left-color: #4caf50; }
.analysis-section.summary { border-left-color: var(--color-primary); background: var(--color-blue-bg); }

.analysis-title {
  font-size: 0.75rem;
  font-weight: 700;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.analysis-body {
  font-size: 0.72rem;
  color: #444;
  line-height: 1.6;
}

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
  max-width: 500px;
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
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  gap: 8px;
}

.manage-item-name { font-size: 0.85rem; flex: 1; min-width: 0; }
.manage-item-symbol { font-weight: 700; }
.manage-item-desc { color: var(--color-text-secondary); font-size: 0.7rem; margin-left: 6px; }

.manage-item-industry {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
  max-width: 80px;
  text-align: center;
}

.manage-item-industry:focus {
  outline: none;
  border-color: var(--color-primary);
  background: #fff;
}

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
@media (max-width: 600px) {
  #sidebar {
    width: 50px;
    --sidebar-width: 50px;
  }
  .sidebar-title, .sidebar-item span:not(.sidebar-icon):not(.sidebar-badge),
  .sidebar-industry-item span:not(.sidebar-industry-icon):not(.sidebar-industry-count) {
    display: none;
  }
  .sidebar-industry-count { display: none; }
  #main-wrap { margin-left: 50px; }
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

#sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); }

/* === KDJ Status Colors === */
.overbought { color: var(--color-overbought); font-weight: 700; }
.oversold { color: var(--color-oversold); font-weight: 700; }
```

---

### Task 4: Rewrite app.js with all new functionality

**Files:**
- Modify: `docs/js/app.js`

- [ ] **Step 1: Replace the entire app.js file**

Replace the entire content of `docs/js/app.js` with the complete new implementation (see below for full code). The key changes are:

1. New `App.stockIndustries` state (loaded from localStorage)
2. New `App.activeIndustry` state for sidebar filtering
3. `loadIndustries()` / `saveIndustries()` methods
4. `getIndustry(symbol)` — returns user-defined industry or fallback
5. `renderSidebar()` — builds sidebar nav dynamically
6. Enhanced `renderSignals()` with indicator row
7. Enhanced `stockRowHTML()` with indicator row
8. Enhanced `toggleDetail()` with five analysis sections
9. Updated `confirmAdd()` with industry input
10. Updated `showManageModal()` with inline industry editing
11. Updated `batchAdd` to support "SYMBOL,INDUSTRY" format

Full replacement code for `docs/js/app.js`:

```javascript
// app.js — US Stocks Monitor Core Application
// ============================================================
// PART 1: State & Init
// ============================================================

const App = {
  // === State ===
  allStocks: [],          // All stocks from stocks.json
  watchlist: [],          // User's selected symbols (from localStorage)
  stockIndustries: {},    // User-defined industries: { symbol: industry }
  filteredSymbols: null,  // Current search filter (null = show all)
  activeIndustry: null,   // Currently selected industry from sidebar (null = show all)
  refreshCount: 10,       // Remaining manual force-refresh count today
  updateTime: null,       // Timestamp from stocks.json
  dataDate: null,         // Data date from stocks.json
  lastFetchOk: false,     // Whether last fetch succeeded

  // === Init ===
  async init() {
    this.loadWatchlist();
    this.loadIndustries();
    this.loadRefreshCount();
    await this.fetchData();
    this.bindEvents();
    this.render();
    this.renderSidebar();
  },

  // === DOM Helpers ===
  $(sel) { return document.querySelector(sel); },
  $$(sel) { return document.querySelectorAll(sel); },

  // === Data Loading ===
  async fetchData(forceRefresh = false) {
    try {
      const ts = Date.now();
      const url = forceRefresh
        ? 'data/stocks.json?t=' + ts
        : 'data/stocks.json';
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const json = await resp.json();
      this.allStocks = json.stocks || [];
      // Apply stored signals for V1.0 (use data signals, fall back to detection)
      this.allStocks.forEach(function(s) {
        s._signal = s.signal || null;
        s._signalStrength = null;
        if (!s._signal) {
          var detected = Indicators.detectSignal(s);
          s._signal = detected.signal;
          s._signalStrength = detected.strength;
        } else {
          // Use signal_strength from JSON if available
          s._signalStrength = s.signal_strength || null;
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
      var raw = localStorage.getItem('us_watchlist');
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
    try {
      localStorage.setItem('us_watchlist', JSON.stringify(this.watchlist));
    } catch(e) {
      console.warn('Failed to save watchlist:', e);
    }
  },

  /** Load user-defined industries from localStorage */
  loadIndustries() {
    try {
      var raw = localStorage.getItem('us_stock_industries');
      this.stockIndustries = raw ? JSON.parse(raw) : {};
    } catch(e) {
      this.stockIndustries = {};
    }
  },

  saveIndustries() {
    try {
      localStorage.setItem('us_stock_industries', JSON.stringify(this.stockIndustries));
    } catch(e) {
      console.warn('Failed to save industries:', e);
    }
  },

  /** Get industry for a symbol: user-defined first, then stock data fallback */
  getIndustry(symbol) {
    if (this.stockIndustries[symbol]) return this.stockIndustries[symbol];
    // Fallback to stock data sector
    for (var i = 0; i < this.allStocks.length; i++) {
      if (this.allStocks[i].symbol === symbol) {
        return this.allStocks[i].sector || '其他';
      }
    }
    return '其他';
  },

  /** Set industry for a symbol */
  setIndustry(symbol, industry) {
    if (industry && industry.trim()) {
      this.stockIndustries[symbol] = industry.trim();
    } else {
      delete this.stockIndustries[symbol];
    }
    this.saveIndustries();
  },

  loadRefreshCount() {
    try {
      var today = new Date().toDateString();
      var stored = localStorage.getItem('us_refresh_date');
      if (stored === today) {
        this.refreshCount = parseInt(localStorage.getItem('us_refresh_count') || '10', 10);
      } else {
        this.refreshCount = 10;
        localStorage.setItem('us_refresh_date', today);
        localStorage.setItem('us_refresh_count', '10');
      }
    } catch(e) {
      this.refreshCount = 10;
      console.warn('Failed to load refresh count:', e);
    }
  },

  saveRefreshCount() {
    try {
      localStorage.setItem('us_refresh_count', String(this.refreshCount));
    } catch(e) {
      console.warn('Failed to save refresh count:', e);
    }
  },

  /** Get stocks filtered by user's watchlist, then by search query, then by active industry */
  getFilteredStocks() {
    var self = this;
    var list = this.allStocks.filter(function(s) {
      return self.watchlist.indexOf(s.symbol) !== -1;
    });
    if (this.filteredSymbols) {
      list = list.filter(function(s) {
        return self.filteredSymbols.indexOf(s.symbol) !== -1;
      });
    }
    if (this.activeIndustry) {
      list = list.filter(function(s) {
        return self.getIndustry(s.symbol) === self.activeIndustry;
      });
    }
    return list;
  },

  /** Group stocks by sector (using user-defined industries), sorted by market cap desc within each group */
  groupBySector(stocks) {
    var self = this;
    var groups = {};
    stocks.forEach(function(s) {
      var sec = self.getIndustry(s.symbol);
      if (!groups[sec]) groups[sec] = [];
      groups[sec].push(s);
    });
    // Sort stocks within each sector by market cap desc
    Object.keys(groups).forEach(function(key) {
      groups[key].sort(function(a, b) {
        return (b.market_cap || 0) - (a.market_cap || 0);
      });
    });
    return groups;
  },

  /** Get unique sorted list of industries from watchlist */
  getIndustryList() {
    var self = this;
    var industries = {};
    this.watchlist.forEach(function(sym) {
      var ind = self.getIndustry(sym);
      industries[ind] = (industries[ind] || 0) + 1;
    });
    // Sort by count desc
    var sorted = Object.keys(industries).sort(function(a, b) {
      return industries[b] - industries[a];
    });
    return sorted.map(function(ind) {
      return { name: ind, count: industries[ind] };
    });
  }
};

// ============================================================
// PART 2: Sidebar Rendering
// ============================================================

/** Render the left sidebar navigation */
App.renderSidebar = function() {
  var industriesEl = this.$('#sidebar-industries');
  if (!industriesEl) return;

  var industries = this.getIndustryList();
  var self = this;

  // Build industry items
  var html = '';
  industries.forEach(function(ind) {
    var activeClass = self.activeIndustry === ind.name ? ' active' : '';
    var icon = self.sectorIcon(ind.name);
    html +=
      '<div class="sidebar-industry-item' + activeClass + '" data-industry="' + ind.name + '">' +
        '<span class="sidebar-industry-icon">' + icon + '</span>' +
        '<span>' + ind.name + '</span>' +
        '<span class="sidebar-industry-count">' + ind.count + '</span>' +
      '</div>';
  });

  if (industries.length === 0) {
    html = '<div style="padding:12px 14px;font-size:0.7rem;color:#888;">暂无行业</div>';
  }

  industriesEl.innerHTML = html;

  // Update signal count badge
  var stocks = this.getFilteredStocks();
  var signalCount = stocks.filter(function(s) {
    return s._signal && s._signal !== 'watch';
  }).length;
  var badge = this.$('#sidebar-signal-count');
  if (badge) {
    if (signalCount > 0) {
      badge.textContent = signalCount;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  // Update active state on signals nav item
  var signalsItem = document.querySelector('.sidebar-item[data-nav="signals"]');
  if (signalsItem) {
    if (this.activeIndustry === null) {
      signalsItem.classList.add('active');
    } else {
      signalsItem.classList.remove('active');
    }
  }

  // Bind clicks on industry items
  var items = this.$$('.sidebar-industry-item');
  items.forEach(function(item) {
    item.addEventListener('click', function() {
      var ind = item.getAttribute('data-industry');
      if (self.activeIndustry === ind) {
        // Deselect: show all
        self.activeIndustry = null;
      } else {
        self.activeIndustry = ind;
      }
      self.renderSidebar();
      self.render();
      // Scroll to industries section
      self.$('#industries-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // Bind click on signals nav item
  if (signalsItem) {
    signalsItem.addEventListener('click', function() {
      self.activeIndustry = null;
      self.renderSidebar();
      self.render();
      self.$('#signals-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
};

/** Return emoji icon for a given sector name */
App.sectorIcon = function(sector) {
  var map = {
    '科技': '💻', 'AI': '🤖', 'AI芯片': '🧠', '半导体': '🔲', '软件': '💿',
    '金融': '🏦', '银行': '🏦', '保险': '🛡️', '支付': '💳',
    '医疗': '🏥', '医药': '💊', '生物科技': '🧬', '健康': '❤️',
    '能源': '⚡', '新能源': '🔋', '石油': '🛢️', '太阳能': '☀️',
    '消费': '🛒', '零售': '🏪', '电商': '📦', '餐饮': '🍔',
    '工业': '🏭', '制造': '🔧', '航空': '✈️', '汽车': '🚗',
    '房地产': '🏠', '通讯': '📡', '电信': '📞', '媒体': '📺',
    '交通': '🚂', '教育': '📚', '游戏': '🎮'
  };
  if (map[sector]) return map[sector];
  // Fuzzy match
  for (var key in map) {
    if (sector.indexOf(key) !== -1 || key.indexOf(sector) !== -1) return map[key];
  }
  return '📌';
};

// ============================================================
// PART 3: Main Rendering
// ============================================================

/** Build indicator HTML string for a stock (used in cards and signals) */
App.indicatorRowHTML = function(stock) {
  var close = stock.close, ma5 = stock.ma5, ma20 = stock.ma20;
  var k = stock.k, d = stock.d;

  // MA5 comparison
  var ma5Above = close > ma5;
  var ma5Class = ma5Above ? 'bull' : 'bear';
  var ma5Arrow = ma5Above ? '↑' : '↓';
  var ma5Pct = ma5 ? ((close - ma5) / ma5 * 100).toFixed(1) : '-';

  // MA20 comparison
  var ma20Above = close > ma20;
  var ma20Class = ma20Above ? 'bull' : 'bear';
  var ma20Arrow = ma20Above ? '↑' : '↓';
  var ma20Pct = ma20 ? ((close - ma20) / ma20 * 100).toFixed(1) : '-';

  // Golden cross
  var hasGC = Indicators.hasGoldenCross(k, d);

  var html = '';

  // MA5 indicator
  html += '<span class="stock-ind ' + ma5Class + '">MA5:' + ma5Arrow + ma5Pct + '%</span>';
  // MA20 indicator
  html += '<span class="stock-ind ' + ma20Class + '">MA20:' + ma20Arrow + ma20Pct + '%</span>';
  // KDJ values
  if (k != null && d != null && stock.j != null) {
    html += '<span class="stock-ind">K:' + k.toFixed(1) + ' D:' + d.toFixed(1) + ' J:' + stock.j.toFixed(1) + '</span>';
  }
  // Golden cross indicator
  if (hasGC) {
    html += '<span class="stock-ind golden">✨金叉</span>';
  }

  return html;
};

/** Main render: update status bar, signals, and industry accordion */
App.render = function() {
  this.updateStatusBar();
  this.renderSignals();
  this.renderIndustries();
};

/** Update data freshness bar */
App.updateStatusBar = function() {
  var el = this.$('#update-time');
  if (this.updateTime) {
    var dt = new Date(this.updateTime);
    var dateStr = dt.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    var timeStr = dt.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.textContent = dateStr + ' ' + timeStr;
  } else {
    el.textContent = '暂无数据';
  }
  this.$('#refresh-count').textContent = '剩' + this.refreshCount + '次';
};

/** Render signal cards for buy/sell/watch stocks */
App.renderSignals = function() {
  var stocks = this.getFilteredStocks();
  var signals = stocks.filter(function(s) {
    return s._signal && s._signal !== 'watch';
  });
  // Also include watch signals
  var watchStocks = stocks.filter(function(s) {
    return s._signal === 'watch';
  });

  var list = this.$('#signals-list');
  var empty = this.$('#signals-empty');
  list.innerHTML = '';

  var allSignals = signals.concat(watchStocks);

  if (allSignals.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  var self = this;
  allSignals.forEach(function(stock) {
    var card = document.createElement('div');
    card.className = 'signal-card ' + (stock._signal || '');
    card.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:space-between;">' +
        '<div class="signal-info">' +
          '<span class="signal-symbol">' + stock.symbol + '</span>' +
          '<span class="signal-name">' + (stock.name || '') + '</span>' +
          '<span class="signal-change ' + Indicators.changeClass(stock.change_pct) + '">' +
            Indicators.formatChange(stock.change_pct) +
          '</span>' +
        '</div>' +
        '<span class="signal-badge ' + (stock._signal || '') + '">' + Indicators.signalText(stock._signal) + '</span>' +
      '</div>' +
      '<div class="signal-indicators">' + self.indicatorRowHTML(stock) + '</div>';

    (function(sym) {
      card.addEventListener('click', function() {
        self.scrollToStock(sym);
      });
    })(stock.symbol);

    list.appendChild(card);
  });
};

/** Render industry accordion with grouped stock rows */
App.renderIndustries = function() {
  var stocks = this.getFilteredStocks();
  var container = this.$('#industries-list');
  var empty = this.$('#industries-empty');

  container.innerHTML = '';

  if (stocks.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  var groups = this.groupBySector(stocks);
  var self = this;

  Object.keys(groups).forEach(function(sector) {
    var sectorStocks = groups[sector];
    var sumChange = 0;
    sectorStocks.forEach(function(s) { sumChange += (s.change_pct || 0); });
    var avgChange = sumChange / sectorStocks.length;

    var groupEl = document.createElement('div');
    groupEl.className = 'industry-group open'; // default open
    groupEl.setAttribute('data-industry', sector);
    groupEl.innerHTML =
      '<div class="industry-header">' +
        '<span class="industry-name">' +
          self.sectorIcon(sector) + ' ' + sector +
          '<span class="industry-count">' + sectorStocks.length + '只</span>' +
        '</span>' +
        '<span>' +
          '<span class="industry-change ' + Indicators.changeClass(avgChange) + '">' +
            Indicators.formatChange(avgChange) +
          '</span>' +
          '<span class="industry-arrow">&#9660;</span>' +
        '</span>' +
      '</div>' +
      '<div class="industry-stocks">' +
        sectorStocks.map(function(s) { return self.stockRowHTML(s); }).join('') +
      '</div>';

    // Toggle accordion on header click
    var header = groupEl.querySelector('.industry-header');
    header.addEventListener('click', function() {
      groupEl.classList.toggle('open');
    });

    container.appendChild(groupEl);
  });

  // Attach stock row click events for detail expansion
  this.$$('.stock-row').forEach(function(row) {
    row.addEventListener('click', function(e) {
      // Don't toggle if clicking on indicator area (allow text selection)
      var symbol = row.getAttribute('data-symbol');
      self.toggleDetail(symbol, row);
    });
  });
};

/** Generate HTML string for a single stock row + its detail wrap container */
App.stockRowHTML = function(stock) {
  var chgClass = Indicators.changeClass(stock.change_pct);
  var signalBadge = stock._signal
    ? '<span class="stock-row-signal ' + stock._signal + '">' + Indicators.signalText(stock._signal) + '</span>'
    : '';
  var indRow = this.indicatorRowHTML(stock);
  return (
    '<div class="stock-row" data-symbol="' + stock.symbol + '">' +
      '<div class="stock-row-main">' +
        '<div class="stock-row-left">' +
          '<span class="stock-row-symbol">' + stock.symbol + '</span>' +
          '<span class="stock-row-name">' + (stock.name || '') + '</span>' +
        '</div>' +
        '<div class="stock-row-right">' +
          '<span class="stock-row-price">$' + Indicators.formatPrice(stock.close) + '</span>' +
          '<span class="stock-row-change ' + chgClass + '">' + Indicators.formatChange(stock.change_pct) + '</span>' +
          signalBadge +
        '</div>' +
      '</div>' +
      '<div class="stock-indicators">' + indRow + '</div>' +
    '</div>' +
    '<div class="stock-detail-wrap" id="detail-' + stock.symbol + '">' +
      '<div class="detail-card"></div>' +
    '</div>'
  );
};

// ============================================================
// PART 4: Detail Expansion
// ============================================================

/** Toggle stock detail card: close all others, then open this one if it was closed */
App.toggleDetail = function(symbol, rowEl) {
  var wrapEl = this.$('#detail-' + symbol);
  if (!wrapEl) return;

  var isOpen = wrapEl.classList.contains('open');

  // Close all other open detail wraps
  var allOpen = this.$$('.stock-detail-wrap.open');
  for (var i = 0; i < allOpen.length; i++) {
    allOpen[i].classList.remove('open');
  }

  if (!isOpen) {
    // Build detail content
    var stock = null;
    for (var j = 0; j < this.allStocks.length; j++) {
      if (this.allStocks[j].symbol === symbol) {
        stock = this.allStocks[j];
        break;
      }
    }
    if (!stock) return;

    var card = wrapEl.querySelector('.detail-card');
    if (!card) return;

    var kdj = Indicators.getKDJStatus(stock.k, stock.d, stock.j);
    var ma = Indicators.getMAAlignment(stock.close, stock.ma5, stock.ma20);
    var chgClass = Indicators.changeClass(stock.change_pct);

    var kOverClass = stock.k > 80 ? ' overbought' : (stock.k < 20 ? ' oversold' : '');
    var jOverClass = stock.j > 100 ? ' overbought' : (stock.j < 0 ? ' oversold' : '');
    var maDescClass = ma.priceAboveMA5 ? '' : ' bearish';
    var maAlignClass = '';
    if (ma.alignment === '多头排列') maAlignClass = ' bullish';
    else if (ma.alignment === '空头排列') maAlignClass = ' bearish';

    // Volume analysis
    var volAnalysis = Indicators.analyzeVolume(stock.volume, stock.avg_volume || 0);
    var volLabel = volAnalysis.label;
    var volClass = volAnalysis.color === 'up' ? 'up' : (volAnalysis.color === 'down' ? 'down' : '');

    // Full analyses
    var kdjAnalysis = Indicators.analyzeKDJ(stock.k, stock.d, stock.j);
    var ma5Analysis = Indicators.analyzeMA5(stock.close, stock.ma5, stock.prev_close);
    var ma20Analysis = Indicators.analyzeMA20(stock.close, stock.ma20, stock.ma5);
    var summary = Indicators.generateSummary(stock);

    card.innerHTML =
      // Price row
      '<div class="detail-price-row">' +
        '<div class="detail-header">' +
          '<span class="detail-symbol">' + stock.symbol + '</span>' +
          '<span class="detail-name">' + (stock.name || '') + ' · ' + this.getIndustry(stock.symbol) + '</span>' +
        '</div>' +
        '<div class="detail-price-info">' +
          '<span class="detail-close">$' + Indicators.formatPrice(stock.close) + '</span>' +
          '<span class="detail-change ' + chgClass + '">' + Indicators.formatChange(stock.change_pct) + '</span>' +
        '</div>' +
      '</div>' +
      // Metrics grid 1: price basics
      '<div class="detail-metrics">' +
        '<div class="metric"><span class="metric-label">昨收</span><span class="metric-value">$' + Indicators.formatPrice(stock.prev_close) + '</span></div>' +
        '<div class="metric"><span class="metric-label">开盘</span><span class="metric-value">$' + Indicators.formatPrice(stock.open) + '</span></div>' +
        '<div class="metric"><span class="metric-label">成交量</span><span class="metric-value">' + Indicators.formatVolume(stock.volume) + '</span></div>' +
        '<div class="metric"><span class="metric-label">市值</span><span class="metric-value">' + Indicators.formatMarketCap(stock.market_cap) + '</span></div>' +
      '</div>' +
      // Metrics grid 2: range + date
      '<div class="detail-metrics" style="margin-top:0;">' +
        '<div class="metric"><span class="metric-label">最高</span><span class="metric-value">$' + Indicators.formatPrice(stock.high) + '</span></div>' +
        '<div class="metric"><span class="metric-label">最低</span><span class="metric-value">$' + Indicators.formatPrice(stock.low) + '</span></div>' +
        '<div class="metric"><span class="metric-label">成交均价</span><span class="metric-value">$' + Indicators.formatPrice(stock.vwap) + '</span></div>' +
        '<div class="metric"><span class="metric-label">数据日期</span><span class="metric-value">' + (this.dataDate || '-') + '</span></div>' +
      '</div>' +
      // MA row
      '<div class="detail-ma-row">' +
        '<span class="ma-item">MA5 <strong>$' + Indicators.formatPrice(stock.ma5) + '</strong></span>' +
        '<span class="ma-desc' + maDescClass + '">' +
          (ma.priceAboveMA5 ? '⬆ 价格在MA5上方' : '⬇ 价格在MA5下方') +
        '</span>' +
        '<span class="ma-item">MA20 <strong>$' + Indicators.formatPrice(stock.ma20) + '</strong></span>' +
        '<span class="ma-align' + maAlignClass + '">' +
          (ma.alignment === '多头排列' ? '⬆ 多头排列' : (ma.alignment === '空头排列' ? '⬇ 空头排列' : ma.alignment)) +
        '</span>' +
      '</div>' +
      // KDJ row
      '<div class="detail-kdj-row">' +
        '<span class="kdj-label">KDJ</span>' +
        '<span class="kdj-item k-val' + kOverClass + '">K: ' + stock.k.toFixed(1) + '</span>' +
        '<span class="kdj-item d-val">D: ' + stock.d.toFixed(1) + '</span>' +
        '<span class="kdj-item j-val' + jOverClass + '">J: ' + stock.j.toFixed(1) + '</span>' +
        (Indicators.hasGoldenCross(stock.k, stock.d) ? '<span style="font-size:0.7rem;color:#f57f17;font-weight:700;">✨金叉</span>' : '') +
      '</div>' +
      // Analysis sections
      '<div class="detail-analysis">' +
        // Volume analysis
        '<div class="analysis-section volume">' +
          '<div class="analysis-title">📊 成交量分析</div>' +
          '<div class="analysis-body">' +
            '当日成交量: ' + Indicators.formatVolume(stock.volume) +
            (volAnalysis.ratio ? '，为近期均量的 ' + volAnalysis.ratio.toFixed(1) + ' 倍' : '') +
            '，<strong class="' + volClass + '">' + volLabel + '</strong>。' +
            (volAnalysis.ratio > 1.3 ? '成交量显著放大，表明市场参与度高，价格变动可信度较强。' :
             volAnalysis.ratio < 0.7 ? '成交量萎缩，市场参与度低，价格变动可能缺乏持续性。' :
             '成交量处于正常水平，市场情绪平稳。') +
          '</div>' +
        '</div>' +
        // KDJ analysis
        '<div class="analysis-section kdj">' +
          '<div class="analysis-title">🔮 KDJ 指标分析</div>' +
          '<div class="analysis-body">' + kdjAnalysis + '</div>' +
        '</div>' +
        // MA5 analysis
        '<div class="analysis-section ma5">' +
          '<div class="analysis-title">📈 5日均线 (MA5) 分析</div>' +
          '<div class="analysis-body">' + ma5Analysis + '</div>' +
        '</div>' +
        // MA20 analysis
        '<div class="analysis-section ma20">' +
          '<div class="analysis-title">📉 20日均线 (MA20) 分析</div>' +
          '<div class="analysis-body">' + ma20Analysis + '</div>' +
        '</div>' +
        // Summary
        '<div class="analysis-section summary">' +
          '<div class="analysis-title">📝 综合总结</div>' +
          '<div class="analysis-body">' + summary + '</div>' +
        '</div>' +
      '</div>';

    wrapEl.classList.add('open');
    // Scroll into view smoothly
    var el = wrapEl;
    setTimeout(function() {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }
};

/** Scroll to a stock's row and expand its detail card */
App.scrollToStock = function(symbol) {
  var row = document.querySelector('.stock-row[data-symbol="' + symbol + '"]');
  if (!row) return;
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  this.toggleDetail(symbol, row);
};

// ============================================================
// PART 5: Search, Add, Remove, Refresh, Modal, Toast
// ============================================================

// === Search ===
App.onSearchInput = function(e) {
  var query = e.target.value.trim().toUpperCase();
  if (!query) {
    this.filteredSymbols = null;
    this.render();
    return;
  }
  // Filter watchlist symbols matching query (by symbol or name)
  var self = this;
  var matches = this.watchlist.filter(function(sym) {
    var stock = null;
    for (var i = 0; i < self.allStocks.length; i++) {
      if (self.allStocks[i].symbol === sym) {
        stock = self.allStocks[i];
        break;
      }
    }
    return sym.indexOf(query) !== -1 || (stock && stock.name && stock.name.indexOf(query) !== -1);
  });
  this.filteredSymbols = matches.length ? matches : ['__NONE__'];
  this.render();
};

// === Add Stock ===
App.showAddForm = function() {
  var form = this.$('#add-form');
  form.classList.remove('hidden');
  this.$('#add-symbol').focus();
};

App.hideAddForm = function() {
  this.$('#add-form').classList.add('hidden');
  this.$('#add-symbol').value = '';
  this.$('#add-industry').value = '';
};

App.confirmAdd = function() {
  var symbol = this.$('#add-symbol').value.trim().toUpperCase();
  var industry = this.$('#add-industry').value.trim();
  if (!symbol) {
    this.toast('请输入美股代码', 'info');
    return;
  }
  if (this.watchlist.indexOf(symbol) !== -1) {
    this.toast(symbol + ' 已经在自选列表中', 'info');
    return;
  }
  // Check if symbol exists in our data
  var exists = false;
  for (var i = 0; i < this.allStocks.length; i++) {
    if (this.allStocks[i].symbol === symbol) {
      exists = true;
      break;
    }
  }
  if (!exists) {
    this.toast(symbol + ' 不在数据源中，但已添加到监控列表', 'info');
  }
  this.watchlist.unshift(symbol);
  // Save industry if provided
  if (industry) {
    this.setIndustry(symbol, industry);
  }
  this.saveWatchlist();
  this.hideAddForm();
  this.render();
  this.renderSidebar();
  this.toast(symbol + (industry ? ' (' + industry + ')' : '') + ' 已添加到自选', 'success');
};

// === Remove Stock ===
App.removeStock = function(symbol) {
  this.watchlist = this.watchlist.filter(function(s) {
    return s !== symbol;
  });
  this.saveWatchlist();
  this.render();
  this.renderSidebar();
  this.toast(symbol + ' 已从自选移除', 'info');
};

// === Manual Refresh ===
App.onRefresh = async function() {
  if (this.refreshCount <= 0) {
    this.toast('今日刷新次数已用完，请明天再试', 'error');
    return;
  }
  this.toast('正在刷新数据...', 'info');
  await this.fetchData(true);
  if (this.lastFetchOk) {
    this.refreshCount--;
    this.saveRefreshCount();
    this.render();
    this.toast('数据已刷新', 'success');
  } else {
    this.toast('数据刷新失败，请检查网络', 'error');
  }
};

// === Manage Modal ===
App.showManageModal = function() {
  // Remove existing modal if any
  var existing = document.querySelector('.modal-overlay');
  if (existing) existing.remove();

  var tmpl = this.$('#tmpl-manage-modal');
  var clone = tmpl.content.cloneNode(true);
  document.body.appendChild(clone);

  var overlay = document.querySelector('.modal-overlay');
  var list = overlay.querySelector('.manage-list');
  var filterInput = overlay.querySelector('.manage-filter');
  var batchInput = overlay.querySelector('.batch-input');
  var self = this;

  // Render watchlist items in modal
  var renderManageList = function(filter) {
    filter = filter || '';
    list.innerHTML = '';
    var q = filter.toUpperCase();
    var filtered = self.watchlist.filter(function(sym) {
      return !q || sym.indexOf(q) !== -1;
    });
    if (filtered.length === 0) {
      overlay.querySelector('.manage-empty').classList.remove('hidden');
    } else {
      overlay.querySelector('.manage-empty').classList.add('hidden');
    }
    filtered.forEach(function(sym) {
      var stock = null;
      for (var i = 0; i < self.allStocks.length; i++) {
        if (self.allStocks[i].symbol === sym) {
          stock = self.allStocks[i];
          break;
        }
      }
      var industry = self.getIndustry(sym);
      var item = document.createElement('div');
      item.className = 'manage-item';
      item.innerHTML =
        '<div class="manage-item-name">' +
          '<span class="manage-item-symbol">' + sym + '</span>' +
          '<span class="manage-item-desc">' + (stock ? stock.name : '未知') + '</span>' +
        '</div>' +
        '<input type="text" class="manage-item-industry" value="' + industry + '" data-symbol="' + sym + '" placeholder="行业" title="点击编辑行业">' +
        '<button class="btn-delete" data-symbol="' + sym + '">&#10005;</button>';

      // Industry inline edit
      var industryInput = item.querySelector('.manage-item-industry');
      industryInput.addEventListener('change', function() {
        self.setIndustry(sym, this.value);
        self.render();
        self.renderSidebar();
        self.toast(sym + ' 行业已更新为 ' + (this.value || '默认'), 'success');
      });

      item.querySelector('.btn-delete').addEventListener('click', function() {
        self.removeStock(sym);
        renderManageList(filterInput.value);
        self.renderSidebar();
      });
      list.appendChild(item);
    });
  };

  renderManageList();

  // Filter input in modal
  filterInput.addEventListener('input', function(e) {
    renderManageList(e.target.value);
  });

  // Batch add
  overlay.querySelector('.btn-batch-add').addEventListener('click', function() {
    var raw = batchInput.value.trim();
    if (!raw) return;
    var lines = raw.split(/[\n]+/);
    var added = 0;
    lines.forEach(function(line) {
      line = line.trim();
      if (!line) return;
      // Support "SYMBOL,INDUSTRY" format
      var parts = line.split(/[,，]/);
      var sym = parts[0].trim().toUpperCase();
      var ind = parts[1] ? parts[1].trim() : '';
      if (!sym) return;
      if (self.watchlist.indexOf(sym) === -1) {
        self.watchlist.unshift(sym);
        added++;
      }
      if (ind) {
        self.setIndustry(sym, ind);
      }
    });
    if (added > 0) {
      self.saveWatchlist();
      self.render();
      self.renderSidebar();
      renderManageList(filterInput.value);
      batchInput.value = '';
      self.toast('已添加 ' + added + ' 只股票', 'success');
    } else {
      self.toast('所有代码已在自选列表中', 'info');
    }
  });

  // Close modal
  overlay.querySelector('.btn-close-modal').addEventListener('click', function() {
    overlay.remove();
  });
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.remove();
  });
};

// === Toast ===
App.toast = function(msg, type) {
  type = type || 'info';
  var container = this.$('#toast-container');
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(function() {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(function() {
      toast.remove();
    }, 300);
  }, 2000);
};

// ============================================================
// PART 6: Event Binding & Bootstrap
// ============================================================

/** Bind all DOM events */
App.bindEvents = function() {
  var self = this;

  // Search input
  this.$('#search-input').addEventListener('input', function(e) {
    self.onSearchInput(e);
  });

  // Add button and form actions
  this.$('#btn-add').addEventListener('click', function() {
    self.showAddForm();
  });
  this.$('#btn-confirm-add').addEventListener('click', function() {
    self.confirmAdd();
  });
  this.$('#btn-cancel-add').addEventListener('click', function() {
    self.hideAddForm();
  });

  // Enter / Escape keys in add form
  this.$('#add-symbol').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      // Move to industry input
      var industryInput = self.$('#add-industry');
      if (document.activeElement === this) {
        e.preventDefault();
        industryInput.focus();
      }
    }
    if (e.key === 'Escape') self.hideAddForm();
  });
  this.$('#add-industry').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') self.confirmAdd();
    if (e.key === 'Escape') self.hideAddForm();
  });

  // Refresh button
  this.$('#btn-refresh').addEventListener('click', function() {
    self.onRefresh();
  });

  // Manage modal button
  this.$('#btn-manage').addEventListener('click', function() {
    self.showManageModal();
  });

  // Global Escape key: close add form and any open modal
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      self.hideAddForm();
      var modal = document.querySelector('.modal-overlay');
      if (modal) modal.remove();
    }
  });
};

// === Bootstrap ===
// Use 'complete' or 'interactive' readyState check to avoid
// missing the DOMContentLoaded event when the script loads late.
(function() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      App.init();
    });
  } else {
    // DOM already parsed, init directly
    App.init();
  }
})();
```

---

### Task 5: Update Python script with fallback note

**Files:**
- Modify: `scripts/fetch_and_calc.py`

- [ ] **Step 1: Add comment above SECTORS dict**

At line 43 in `scripts/fetch_and_calc.py`, add a comment above the SECTORS dictionary:

```python
# NOTE: SECTORS is a fallback only. The frontend allows users to define custom
# industries per stock, stored in localStorage. Any industry values set here
# will be overridden by user-defined industries in the UI.
SECTORS = {
```

---

### Task 6: Verify changes work

**Files:**
- Verify: `docs/index.html`, `docs/css/app.css`, `docs/js/indicators.js`, `docs/js/app.js`

- [ ] **Step 1: Check JavaScript syntax**

Run: `node --check docs/js/indicators.js && node --check docs/js/app.js`

- [ ] **Step 2: Open the page in browser**

Run: Start a local server and navigate to the page:
```bash
cd "C:\us stocks\docs" && npx serve . --no-clipboard
```

Expected: Page loads with left sidebar showing industry list, enhanced cards with indicator rows, and clicking a stock row expands to show five analysis sections.

- [ ] **Step 3: Test add stock with industry**

1. Click "+ 添加"
2. Enter a symbol and an industry
3. Confirm
Expected: Stock appears under correct industry in sidebar and main content

- [ ] **Step 4: Test sidebar filtering**

1. Click an industry in the sidebar
Expected: Main content shows only stocks from that industry; sidebar item is highlighted

- [ ] **Step 5: Test detail expansion**

1. Click a stock row
Expected: Detail card expands with five analysis sections (volume, KDJ, MA5, MA20, summary)

- [ ] **Step 6: Commit**

```bash
git add docs/index.html docs/css/app.css docs/js/indicators.js docs/js/app.js scripts/fetch_and_calc.py docs/superpowers/
git commit -m "feat: add sidebar nav, enhanced cards, custom industries, detail analysis"
```
