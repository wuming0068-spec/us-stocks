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
    this.syncWatchlist();
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
      var baseUrl = this.getDataUrl();
      const url = forceRefresh
        ? baseUrl + '?t=' + ts
        : baseUrl;
      var resp = await fetch(url);
      // Fallback: if remote fetch fails on localhost, try local file
      if (!resp.ok && baseUrl !== 'data/stocks.json') {
        console.warn('Remote data fetch failed, falling back to local');
        resp = await fetch('data/stocks.json?t=' + ts);
      }
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

  /** Load watchlist from localStorage. Seed from stocks.json data on first visit. */
  loadWatchlist() {
    try {
      var raw = localStorage.getItem('us_watchlist');
      this.watchlist = raw ? JSON.parse(raw) : [];
    } catch(e) {
      this.watchlist = [];
    }
  },

  /** Sync watchlist with stocks.json data symbols.
   *  On first visit (empty watchlist): populate all symbols from data.
   *  On subsequent visits: auto-add any new symbols found in data file. */
  syncWatchlist() {
    var self = this;
    if (!this.allStocks || this.allStocks.length === 0) return;
    // First visit: populate from data file
    if (this.watchlist.length === 0) {
      this.watchlist = this.allStocks.map(function(s) { return s.symbol; });
      this.saveWatchlist();
      return;
    }
    // Auto-add any new stocks that appear in the data file (e.g. added on GitHub)
    var changed = false;
    this.allStocks.forEach(function(s) {
      if (self.watchlist.indexOf(s.symbol) === -1) {
        self.watchlist.push(s.symbol);
        changed = true;
      }
    });
    if (changed) this.saveWatchlist();
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
    // Sort stocks within each sector: signal priority (buy > sell > watch > none), then market cap desc
    var signalRank = { buy: 0, sell: 1, watch: 2 };
    Object.keys(groups).forEach(function(key) {
      groups[key].sort(function(a, b) {
        var rankA = signalRank[a._signal] != null ? signalRank[a._signal] : 3;
        var rankB = signalRank[b._signal] != null ? signalRank[b._signal] : 3;
        if (rankA !== rankB) return rankA - rankB;
        return (b.market_cap || 0) - (a.market_cap || 0);
      });
    });
    return groups;
  },

  /** Resolve data URL: use GitHub raw when on localhost to keep data synced */
  getDataUrl() {
    var host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1' || host === '[::1]' || host.startsWith('192.168.') || host.startsWith('10.')) {
      return 'https://raw.githubusercontent.com/wuming0068-spec/us-stocks/master/docs/data/stocks.json';
    }
    return 'data/stocks.json';
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

  var html = '';

  // MA5 indicator
  html += '<span class="stock-ind ' + ma5Class + '">MA5:' + ma5Arrow + ma5Pct + '%</span>';
  // MA20 indicator
  html += '<span class="stock-ind ' + ma20Class + '">MA20:' + ma20Arrow + ma20Pct + '%</span>';
  // KDJ signal interpretation (replaces raw K/D/J values)
  var kdjSig = Indicators.getKDJSignalText(k, d, stock.j);
  html += '<span class="stock-ind kdj-sig ' + kdjSig.cssClass + '">' + kdjSig.text + '</span>';

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
  // Show data source indicator on localhost
  var sourceEl = this.$('#data-source');
  if (sourceEl) {
    var host = window.location.hostname;
    var isLocal = host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
    sourceEl.textContent = isLocal ? ' 🌐 同步自GitHub' : '';
  }
  this.$('#refresh-count').textContent = '剩' + this.refreshCount + '次';
};

/** Render signal cards for buy/sell/watch stocks */
App.renderSignals = function() {
  var stocks = this.getFilteredStocks();

  // Collect all stocks that have signals
  var buyStocks = [];
  var sellStocks = [];
  var watchStocks = [];

  stocks.forEach(function(s) {
    if (s._signal === 'buy') buyStocks.push(s);
    else if (s._signal === 'sell') sellStocks.push(s);
    else if (s._signal === 'watch') watchStocks.push(s);
  });

  // Sort each group by market cap descending
  var byMarketCap = function(a, b) {
    return (b.market_cap || 0) - (a.market_cap || 0);
  };
  buyStocks.sort(byMarketCap);
  sellStocks.sort(byMarketCap);
  watchStocks.sort(byMarketCap);

  // Buy first, then sell, then watch
  var allSignals = buyStocks.concat(sellStocks).concat(watchStocks);

  var list = this.$('#signals-list');
  var empty = this.$('#signals-empty');
  list.innerHTML = '';

  if (allSignals.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  var self = this;
  allSignals.forEach(function(stock) {
    var card = document.createElement('div');
    card.className = 'signal-card ' + (stock._signal || '');
    var phase = Indicators.getMarketPhase(stock);
    card.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:space-between;">' +
        '<div class="signal-info">' +
          '<span class="signal-symbol">' + stock.symbol + '</span>' +
          '<span class="signal-name">' + (stock.name || '') + '</span>' +
          '<span class="signal-change ' + Indicators.changeClass(stock.change_pct) + '">' +
            Indicators.formatChange(stock.change_pct) +
          '</span>' +
        '</div>' +
        '<div class="signal-badges">' +
          '<span class="stock-row-phase ' + phase.cssClass + '">' + phase.label + '</span>' +
          '<span class="signal-badge ' + (stock._signal || '') + '">' + Indicators.signalText(stock._signal) + '</span>' +
        '</div>' +
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
  var phase = Indicators.getMarketPhase(stock);
  var phaseBadge = '<span class="stock-row-phase ' + phase.cssClass + '">' + phase.label + '</span>';
  var indRow = this.indicatorRowHTML(stock);
  return (
    '<div class="stock-row" data-symbol="' + stock.symbol + '">' +
      '<div class="stock-row-main">' +
        '<div class="stock-row-left">' +
          '<span class="stock-row-symbol">' + stock.symbol + '</span>' +
          '<span class="stock-row-name">' + (stock.name || '') + '</span>' +
          '<span class="stock-row-price">$' + Indicators.formatPrice(stock.close) + '</span>' +
          '<span class="stock-row-change ' + chgClass + '">' + Indicators.formatChange(stock.change_pct) + '</span>' +
        '</div>' +
        '<div class="stock-row-right">' +
          phaseBadge +
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

    var kdjSig = Indicators.getKDJSignalText(stock.k, stock.d, stock.j);
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
    var maAnalysis = Indicators.analyzeMA20(stock.close, stock.ma20, stock.ma5);
    var summary = Indicators.generateSummary(stock);

    // Right-side analysis
    var rightSide = Indicators.analyzeRightSide(stock);

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
      // MA row (compact stats)
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
      // KDJ row (signal interpretation, no raw values)
      '<div class="detail-kdj-row">' +
        '<span class="kdj-label">KDJ</span>' +
        '<span class="kdj-item k-val' + kOverClass + '">K: ' + stock.k.toFixed(1) + '</span>' +
        '<span class="kdj-item d-val">D: ' + stock.d.toFixed(1) + '</span>' +
        '<span class="kdj-item j-val' + jOverClass + '">J: ' + stock.j.toFixed(1) + '</span>' +
        '<span class="kdj-signal-text ' + kdjSig.cssClass + '">' + kdjSig.text + '</span>' +
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
            (volAnalysis.ratio && volAnalysis.ratio > 1.3 ? '成交量显著放大，表明市场参与度高，价格变动可信度较强。' :
             volAnalysis.ratio && volAnalysis.ratio < 0.7 ? '成交量萎缩，市场参与度低，价格变动可能缺乏持续性。' :
             '成交量处于正常水平，市场情绪平稳。') +
          '</div>' +
        '</div>' +
        // KDJ analysis
        '<div class="analysis-section kdj">' +
          '<div class="analysis-title">🔮 KDJ 指标分析</div>' +
          '<div class="analysis-body">' + kdjAnalysis + '</div>' +
        '</div>' +
        // Merged MA5 + MA20 analysis
        '<div class="analysis-section ma-combined">' +
          '<div class="analysis-title">📈 均线分析 (MA5 & MA20)</div>' +
          '<div class="analysis-body">' +
            '<p><strong>均线排列：</strong>' + ma.alignment + '（MA5: $' + Indicators.formatPrice(stock.ma5) + '，MA20: $' + Indicators.formatPrice(stock.ma20) + '）</p>' +
            '<p><strong>MA5偏离：</strong>股价在MA5' + (ma.priceAboveMA5 ? '上方 ' : '下方 ') +
              Math.abs(parseFloat(((stock.close - stock.ma5) / stock.ma5 * 100).toFixed(2))) + '%</p>' +
            '<p><strong>MA20偏离：</strong>股价在MA20' + (ma.priceAboveMA20 ? '上方 ' : '下方 ') +
              Math.abs(parseFloat(((stock.close - stock.ma20) / stock.ma20 * 100).toFixed(2))) + '%</p>' +
            '<p>' + maAnalysis + '</p>' +
          '</div>' +
        '</div>' +
        // Right-side indicator analysis
        (rightSide ? (
        '<div class="analysis-section right-side">' +
          '<div class="analysis-title">🎯 右侧指标分析</div>' +
          '<div class="analysis-body">' +
            '<div class="right-side-summary">' +
              '<span class="rs-trend ' + (rightSide.isApplicable ? 'rs-bull' : 'rs-bear') + '">MA20趋势：' + rightSide.trendDirection + '（斜率 ' + (rightSide.ma20Slope >= 0 ? '+' : '') + rightSide.ma20Slope.toFixed(2) + '%/日）</span>' +
              '<span class="rs-deviation">当前偏离MA20：' + (rightSide.deviation >= 0 ? '+' : '') + rightSide.deviationPct + '%</span>' +
            '</div>' +
            '<div class="right-side-zone">' +
              '<div class="rs-zone-title">📐 买入区间（经验参数 L=' + rightSide.L + '% U=' + (rightSide.U >= 0 ? '+' : '') + rightSide.U + '%）</div>' +
              '<div class="rs-prices">' +
                '<div class="rs-price-item b1"><span>B1 试探买点</span><strong>$' + Indicators.formatPrice(rightSide.lowerPrice) + '</strong><small>20%仓位</small></div>' +
                '<div class="rs-price-item b2"><span>B2 标准买点</span><strong>$' + Indicators.formatPrice(rightSide.midPrice) + '</strong><small>30%仓位</small></div>' +
                '<div class="rs-price-item b3"><span>B3 确认买点</span><strong>$' + Indicators.formatPrice(rightSide.upperPrice) + '</strong><small>50%仓位</small></div>' +
              '</div>' +
            '</div>' +
            '<div class="right-side-info">' +
              '<span class="rs-stop-loss">🛑 止损价：$' + Indicators.formatPrice(rightSide.stopLoss) + '（下限×0.98）</span>' +
              '<span class="rs-current">📍 当前位置：' + rightSide.currentPriceRelative + '</span>' +
            '</div>' +
            (rightSide.isApplicable ? '' : '<div class="rs-warning">⚠ MA20未处于上升趋势，右侧交易条件不满足，建议观望或切换左侧策略</div>') +
            '<div class="rs-note">📌 基于经验默认参数计算。历史回调数据充足后将自动切换为个性化统计参数。</div>' +
          '</div>' +
        '</div>'
        ) : '') +
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
