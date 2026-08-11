// intraday.js — Intraday Volatility Analysis for Options Trading
// ============================================================

const Intraday = {
  data: null,
  activePeriod: '300',
  loaded: false,
  active: false,

  async load() {
    try {
      const ts = Date.now();
      let resp = await fetch('data/intraday_stats.json?t=' + ts);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      this.data = await resp.json();
      this.loaded = true;
    } catch (err) {
      console.warn('Failed to load intraday_stats.json:', err);
      this.loaded = false;
    }
  },

  getStocks() {
    if (!this.data || !this.data.stocks) return [];
    const watchSet = new Set(App.watchlist);
    const result = [];
    for (const [sym, info] of Object.entries(this.data.stocks)) {
      if (watchSet.has(sym) && info.periods && info.periods[this.activePeriod]) {
        result.push({ symbol: sym, ...info });
      }
    }
    result.sort((a, b) => {
      const aS = a.periods[this.activePeriod]?.swing?.mean || 0;
      const bS = b.periods[this.activePeriod]?.swing?.mean || 0;
      return bS - aS;
    });
    return result;
  },

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

  buildHead() {
    return `<tr>
      <th rowspan="2" class="th-fixed th-stock-col">股票</th>
      <th rowspan="2" class="th-price-col">当前价</th>
      <th colspan="5" class="th-grp th-grp-up">📈 最高涨幅</th>
      <th colspan="5" class="th-grp th-grp-down">📉 最低跌幅</th>
      <th colspan="4" class="th-grp th-grp-swing">📐 震荡幅度</th>
    </tr>
    <tr>
      <th class="th-s">均值</th><th class="th-s">σ</th>
      <th class="th-s">1σ(超%)</th><th class="th-s">2σ(超%)</th><th class="th-s">3σ(超%)</th>
      <th class="th-s">均值</th><th class="th-s">σ</th>
      <th class="th-s">1σ(超%)</th><th class="th-s">2σ(超%)</th><th class="th-s">3σ(超%)</th>
      <th class="th-s">均值</th><th class="th-s">σ</th>
      <th class="th-s">1σ(超%)</th><th class="th-s">2σ(超%)</th>
    </tr>`;
  },

  sigmaCells(stats, isDown) {
    if (!stats || !stats.sigma_1) return '<td colspan="5" class="td-na">-</td>';
    let html = `<td class="td-mean">${this.fmtPct(stats.mean)}</td>`;
    html += `<td class="td-std">${this.fmtPct(stats.std)}</td>`;
    for (const s of [1, 2, 3]) {
      const sig = stats[`sigma_${s}`];
      if (sig) {
        html += `<td class="td-sig"><span class="sig-price">$${this.fmtPrice(sig.price)}</span><span class="sig-exceed ${this.colorClass(sig.exceed_pct, 30)}">${sig.exceed_pct}%</span></td>`;
      } else {
        html += '<td class="td-na">-</td>';
      }
    }
    return html;
  },

  swingSigmaCells(stats) {
    if (!stats || !stats.sigma_1) return '<td colspan="4" class="td-na">-</td>';
    let html = `<td class="td-mean">${this.fmtPct(stats.mean)}</td>`;
    html += `<td class="td-std">${this.fmtPct(stats.std)}</td>`;
    for (const s of [1, 2]) {
      const sig = stats[`sigma_${s}`];
      if (sig) {
        html += `<td class="td-sig"><span class="sig-range">±${this.fmtPct(sig.pct)}</span><span class="sig-exceed ${this.colorClass(sig.exceed_pct, 30)}">${sig.exceed_pct}%</span></td>`;
      } else {
        html += '<td class="td-na">-</td>';
      }
    }
    return html;
  },

  render() {
    const thead = document.getElementById('intraday-thead');
    const tbody = document.getElementById('intraday-tbody');
    const empty = document.getElementById('intraday-empty');
    const table = document.getElementById('intraday-table');

    if (!this.loaded || !this.data) {
      empty.classList.remove('hidden');
      if (table) table.style.display = 'none';
      return;
    }

    const stocks = this.getStocks();
    if (stocks.length === 0) {
      empty.classList.remove('hidden');
      if (table) table.style.display = 'none';
      return;
    }

    empty.classList.add('hidden');
    if (table) table.style.display = '';
    thead.innerHTML = this.buildHead();

    let rows = '';
    for (const s of stocks) {
      const p = s.periods[this.activePeriod];
      if (!p) continue;
      rows += `<tr>
        <td class="td-fixed td-stock-col">
          <span class="s-sym">${s.symbol}</span>
          <span class="s-name">${s.name}</span>
        </td>
        <td class="td-price-col">$${this.fmtPrice(s.close)}</td>
        ${this.sigmaCells(p.up, false)}
        ${this.sigmaCells(p.down, true)}
        ${this.swingSigmaCells(p.swing)}
      </tr>`;
    }
    tbody.innerHTML = rows;

    const updateEl = document.getElementById('intraday-update-time');
    if (updateEl && this.data) {
      updateEl.textContent = this.data.updated_at || '未知';
    }
  },

  show() {
    this.active = true;
    document.getElementById('signals-section').classList.add('hidden');
    document.getElementById('industries-section').classList.add('hidden');
    document.getElementById('intraday-section').classList.remove('hidden');
    this.render();
  },

  hide() {
    this.active = false;
    document.getElementById('intraday-section').classList.add('hidden');
  },

  switchPeriod(period) {
    this.activePeriod = period;
    document.querySelectorAll('.period-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.period === period);
    });
    this.render();
  },

  init() {
    const self = this;

    // Period tabs
    document.getElementById('intraday-period-tabs').addEventListener('click', function(e) {
      const tab = e.target.closest('.period-tab');
      if (tab) self.switchPeriod(tab.dataset.period);
    });

    // Sidebar nav: intraday
    const intraNav = document.querySelector('.sidebar-item[data-nav="intraday"]');
    if (intraNav) {
      intraNav.addEventListener('click', async function() {
        document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
        document.querySelectorAll('.sidebar-industry-item').forEach(i => i.classList.remove('active'));
        intraNav.classList.add('active');
        App.activeIndustry = null;
        App.showStarredOnly = false;
        if (!self.loaded) await self.load();
        self.show();
      });
    }

    // Patch existing nav clicks to hide intraday when switching away
    function hideIntradayOnNav(sel) {
      const el = document.querySelector(sel);
      if (!el) return;
      el.addEventListener('click', function() {
        self.hide();
      });
    }
    hideIntradayOnNav('.sidebar-item[data-nav="signals"]');
    hideIntradayOnNav('.sidebar-item[data-nav="starred"]');

    // Also hide intraday when clicking industry items (use event delegation)
    const industriesEl = document.getElementById('sidebar-industries');
    if (industriesEl) {
      industriesEl.addEventListener('click', function(e) {
        if (e.target.closest('.sidebar-industry-item')) {
          self.hide();
        }
      });
    }
  }
};

// Auto-init on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() { Intraday.init(); });
} else {
  Intraday.init();
}
