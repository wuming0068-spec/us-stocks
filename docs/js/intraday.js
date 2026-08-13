// intraday.js — Intraday Volatility Analysis for Options Trading
// ============================================================

const Intraday = {
  data: null,
  activePeriod: '300',
  loaded: false,
  active: false,
  watchlist: [],  // symbols the user manually added (persisted in localStorage)

  // ---- Persistence ----
  loadWatchlist() {
    try {
      var raw = localStorage.getItem('us_intraday_watchlist');
      this.watchlist = raw ? JSON.parse(raw) : [];
    } catch(e) { this.watchlist = []; }
  },

  saveWatchlist() {
    try { localStorage.setItem('us_intraday_watchlist', JSON.stringify(this.watchlist)); }
    catch(e) {}
  },

  // ---- Data ----
  async load() {
    try {
      var ts = Date.now();
      var resp = await fetch('data/intraday_stats.json?t=' + ts);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      this.data = await resp.json();
      this.loaded = true;
    } catch (err) {
      console.warn('Failed to load intraday_stats.json:', err);
      this.loaded = false;
    }
  },

  // Returns stocks that have intraday data, sorted by swing mean
  getAvailableStocks() {
    if (!this.data || !this.data.stocks) return [];
    var result = [];
    for (var sym in this.data.stocks) {
      var info = this.data.stocks[sym];
      if (info.periods && info.periods[this.activePeriod]) {
        result.push({ symbol: sym, name: info.name || sym, close: info.close, sector: info.sector || '' });
      }
    }
    result.sort(function(a, b) {
      var aS = a.symbol;
      var bS = b.symbol;
      // Prefer larger market cap stocks at top (approximated by close price)
      return (b.close || 0) - (a.close || 0);
    });
    return result;
  },

  // Returns ONLY user-added stocks with their period data
  getStocks() {
    if (!this.data || !this.data.stocks) return [];
    var self = this;
    var result = [];
    this.watchlist.forEach(function(sym) {
      var info = self.data.stocks[sym];
      if (info && info.periods && info.periods[self.activePeriod]) {
        result.push({ symbol: sym, name: info.name || sym, close: info.close, sector: info.sector || '', periods: info.periods });
      }
    });
    return result;
  },

  // Add a symbol to intraday watchlist
  addStock(symbol) {
    var sym = symbol.toUpperCase();
    if (this.watchlist.indexOf(sym) !== -1) return false; // already added
    if (!this.data || !this.data.stocks[sym]) return false; // no intraday data
    this.watchlist.push(sym);
    this.saveWatchlist();
    this.render();
    return true;
  },

  // Remove a symbol from intraday watchlist
  removeStock(symbol) {
    var idx = this.watchlist.indexOf(symbol);
    if (idx === -1) return;
    this.watchlist.splice(idx, 1);
    this.saveWatchlist();
    this.render();
  },

  // ---- Search autocomplete ----
  onSearchInput(e) {
    var query = e.target.value.trim().toUpperCase();
    var dropdown = document.getElementById('intraday-suggestions');
    if (!dropdown) return;
    if (!query || query.length < 1) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    // Find matching stocks NOT already in watchlist
    var available = this.getAvailableStocks();
    var matches = [];
    for (var i = 0; i < available.length; i++) {
      var s = available[i];
      var sym = s.symbol.toUpperCase();
      var name = (s.name || '').toUpperCase();
      if (sym.indexOf(query) !== -1 || name.indexOf(query) !== -1) {
        if (this.watchlist.indexOf(s.symbol) === -1) {
          matches.push(s);
        }
      }
    }
    if (matches.length === 0) {
      dropdown.classList.add('hidden');
      dropdown.innerHTML = '';
      return;
    }

    // Prefer prefix matches
    var prefix = matches.filter(function(s) { return s.symbol.toUpperCase().startsWith(query); });
    var rest = matches.filter(function(s) { return !s.symbol.toUpperCase().startsWith(query); });
    var results = prefix.concat(rest).slice(0, 8);

    var self = this;
    var html = '';
    results.forEach(function(s) {
      html += '<div class="suggestion-item" data-symbol="' + s.symbol + '">' +
        '<span class="sugg-symbol">' + s.symbol + '</span>' +
        '<span class="sugg-name">' + (s.name || '') + '</span>' +
        '<span class="sugg-sector">' + (s.sector || '') + '</span>' +
      '</div>';
    });
    dropdown.innerHTML = html;
    dropdown.classList.remove('hidden');

    var items = dropdown.querySelectorAll('.suggestion-item');
    items.forEach(function(item) {
      item.addEventListener('mousedown', function(ev) {
        ev.preventDefault();
        var sym = item.getAttribute('data-symbol');
        self.addStock(sym);
        document.getElementById('intraday-search').value = '';
        self.hideSuggestions();
      });
      item.addEventListener('keydown', function(ev) {
        if (ev.key === 'Enter') {
          ev.preventDefault();
          var sym = item.getAttribute('data-symbol');
          self.addStock(sym);
          document.getElementById('intraday-search').value = '';
          self.hideSuggestions();
        }
        if (ev.key === 'ArrowDown') { ev.preventDefault(); var n = item.nextElementSibling; if (n) n.focus(); }
        if (ev.key === 'ArrowUp') { ev.preventDefault(); var p = item.previousElementSibling; if (p) p.focus(); else document.getElementById('intraday-search').focus(); }
      });
    });
  },

  hideSuggestions() {
    var dropdown = document.getElementById('intraday-suggestions');
    if (dropdown) { dropdown.classList.add('hidden'); dropdown.innerHTML = ''; }
  },

  // ---- Formatting ----
  fmtPrice(p) {
    if (p == null || isNaN(p)) return '-';
    return p.toFixed(2);
  },

  fmtPct(v) {
    if (v == null || isNaN(v)) return '-';
    return (v > 0 ? '+' : '') + v.toFixed(1) + '%';
  },

  colorClass(val, threshold) {
    if (val == null || isNaN(val)) return '';
    if (val > threshold) return 'cell-hot';
    if (val > threshold * 0.5) return 'cell-warm';
    return '';
  },

  // ---- Table rendering ----
  buildHead() {
    return '<tr>' +
      '<th rowspan="2" class="th-fixed th-stock-col">股票</th>' +
      '<th rowspan="2" class="th-price-col">当前价</th>' +
      '<th rowspan="2"></th>' +
      '<th colspan="4" class="th-grp th-grp-up">📈 最高涨幅</th>' +
      '<th colspan="4" class="th-grp th-grp-down">📉 最低跌幅</th>' +
      '<th colspan="4" class="th-grp th-grp-swing">📐 震荡幅度</th>' +
    '</tr>' +
    '<tr>' +
      '<th class="th-s">均值</th><th class="th-s">P25</th><th class="th-s">P50</th><th class="th-s">P75</th>' +
      '<th class="th-s">均值</th><th class="th-s">P25</th><th class="th-s">P50</th><th class="th-s">P75</th>' +
      '<th class="th-s">均值</th><th class="th-s">P25</th><th class="th-s">P50</th><th class="th-s">P75</th>' +
    '</tr>';
  },

  percentileCells(stats) {
    if (!stats || stats.p50 == null) return '<td colspan="4" class="td-na">-</td>';
    var html = '<td class="td-mean">' + this.fmtPct(stats.mean) + '</td>';
    for (var p = 25; p <= 75; p += 25) {
      var val = stats['p' + p];
      var price = stats['p' + p + '_price'];
      if (val != null) {
        html += '<td class="td-sig"><span class="sig-price">$' + this.fmtPrice(price) + '</span><span class="sig-exceed">' + this.fmtPct(val) + '</span></td>';
      } else {
        html += '<td class="td-na">-</td>';
      }
    }
    return html;
  },

  render() {
    var thead = document.getElementById('intraday-thead');
    var tbody = document.getElementById('intraday-tbody');
    var empty = document.getElementById('intraday-empty');
    var table = document.getElementById('intraday-table');

    if (!this.loaded || !this.data) {
      if (empty) empty.classList.remove('hidden');
      if (table) table.style.display = 'none';
      return;
    }

    var stocks = this.getStocks();
    if (stocks.length === 0) {
      if (empty) { empty.classList.remove('hidden'); empty.style.display = ''; }
      if (table) table.style.display = 'none';
      return;
    }

    if (empty) { empty.classList.add('hidden'); empty.style.display = 'none'; }
    if (table) table.style.display = '';
    thead.innerHTML = this.buildHead();

    var rows = '';
    var self = this;
    for (var i = 0; i < stocks.length; i++) {
      var s = stocks[i];
      var p = s.periods[this.activePeriod];
      if (!p) continue;
      rows += '<tr>' +
        '<td class="td-fixed td-stock-col">' +
          '<span class="s-sym">' + s.symbol + '</span>' +
          '<span class="s-name">' + s.name + '</span>' +
        '</td>' +
        '<td class="td-price-col">$' + this.fmtPrice(s.close) + '</td>' +
        '<td class="td-del"><button class="btn-intraday-del" data-symbol="' + s.symbol + '" title="移除">✕</button></td>' +
        this.percentileCells(p.up) +
        this.percentileCells(p.down) +
        this.percentileCells(p.swing) +
      '</tr>';
    }
    tbody.innerHTML = rows;

    // Bind delete buttons
    var delBtns = tbody.querySelectorAll('.btn-intraday-del');
    delBtns.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        self.removeStock(btn.getAttribute('data-symbol'));
      });
    });

    // Update time
    var updateEl = document.getElementById('intraday-update-time');
    if (updateEl && this.data) {
      updateEl.textContent = this.data.updated_at || '未知';
    }
  },

  show() {
    this.active = true;
    document.getElementById('signals-section').classList.add('hidden');
    document.getElementById('industries-section').classList.add('hidden');
    document.getElementById('intraday-section').classList.remove('hidden');
    this.loadWatchlist();
    this.render();
  },

  hide() {
    this.active = false;
    document.getElementById('intraday-section').classList.add('hidden');
  },

  switchPeriod(period) {
    this.activePeriod = period;
    document.querySelectorAll('#intraday-period-tabs .period-tab').forEach(function(t) {
      t.classList.toggle('active', t.dataset.period === period);
    });
    this.render();
  },

  init() {
    var self = this;
    this.loadWatchlist();

    // Period tabs
    document.getElementById('intraday-period-tabs').addEventListener('click', function(e) {
      var tab = e.target.closest('.period-tab');
      if (tab) self.switchPeriod(tab.dataset.period);
    });

    // Search input for adding stocks
    var searchInput = document.getElementById('intraday-search');
    if (searchInput) {
      searchInput.addEventListener('input', function(e) { self.onSearchInput(e); });
      searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          var first = document.querySelector('#intraday-suggestions .suggestion-item');
          if (first) first.focus();
        }
        if (e.key === 'Escape') { self.hideSuggestions(); }
      });
      searchInput.addEventListener('blur', function() {
        setTimeout(function() { self.hideSuggestions(); }, 150);
      });
    }

    // Sidebar nav: intraday
    var intraNav = document.querySelector('.sidebar-item[data-nav="intraday"]');
    if (intraNav) {
      intraNav.addEventListener('click', async function() {
        document.querySelectorAll('.sidebar-item').forEach(function(i) { i.classList.remove('active'); });
        document.querySelectorAll('.sidebar-industry-item').forEach(function(i) { i.classList.remove('active'); });
        intraNav.classList.add('active');
        if (!self.loaded) await self.load();
        self.show();
      });
    }

    // Hide intraday when switching away
    function hideIntradayOnNav(sel) {
      var el = document.querySelector(sel);
      if (!el) return;
      el.addEventListener('click', function() { self.hide(); });
    }
    hideIntradayOnNav('.sidebar-item[data-nav="signals"]');
    hideIntradayOnNav('.sidebar-item[data-nav="starred"]');

    // Industry item clicks also hide intraday
    var industriesEl = document.getElementById('sidebar-industries');
    if (industriesEl) {
      industriesEl.addEventListener('click', function(e) {
        if (e.target.closest('.sidebar-industry-item')) { self.hide(); }
      });
    }
  }
};

// Auto-init
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() { Intraday.init(); });
} else {
  Intraday.init();
}
