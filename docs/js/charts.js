// charts.js — Stock price chart with MAs, Volume, and KDJ indicator
// ============================================================

const ChartManager = {
  // Cache: { symbol: { raw: [...], mas: {...}, kdj: [...] } }
  _cache: {},

  // Color palette
  COLORS: {
    price:     '#1976d2',  // blue - close price
    ma5:       '#ff9800',  // orange
    ma20:      '#4caf50',  // green
    ma30:      '#9c27b0',  // purple
    ma60:      '#f44336',  // red
    ma120:     '#795548',  // brown
    ma150:     '#607d8b',  // blue-grey
    volumeUp:  'rgba(46, 125, 50, 0.45)',
    volumeDown:'rgba(198, 40, 40, 0.45)',
    kLine:     '#1976d2',
    dLine:     '#7b1fa2',
    jLine:     '#e65100',
    grid:      '#e0e0e0',
    gridMinor: '#f0f0f0',
    text:      '#666',
    bg:        '#fafbfc',
    crosshair: 'rgba(0,0,0,0.3)',
    tooltipBg: 'rgba(30,30,30,0.88)',
    tooltipText:'#fff',
    ref20:     'rgba(67,160,71,0.25)',
    ref50:     'rgba(158,158,158,0.2)',
    ref80:     'rgba(229,57,53,0.25)'
  },

  // MA periods to compute
  MA_PERIODS: [5, 20, 30, 60, 120, 150],

  // Pixel ratio for sharp rendering
  _dpr: Math.max(window.devicePixelRatio || 1, 1),

  // Currently rendered symbol
  _activeSymbol: null,
  _activeContainer: null,

  /** Fetch history JSON for a symbol. Returns parsed array of OHLCV objects. */
  async fetchHistory(symbol) {
    if (this._cache[symbol]) return this._cache[symbol];
    try {
      const ts = Date.now();
      const resp = await fetch('data/history/' + symbol + '.json?t=' + ts);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const raw = await resp.json();
      // Compute derived data
      const closes  = raw.map(function(d) { return d.close; });
      const highs   = raw.map(function(d) { return d.high; });
      const lows    = raw.map(function(d) { return d.low; });
      const volumes = raw.map(function(d) { return d.volume; });

      const mas = {};
      var self = this;
      this.MA_PERIODS.forEach(function(p) {
        mas['ma' + p] = self.computeSMA(closes, p);
      });

      const kdj = this.computeKDJ(highs, lows, closes, 9);

      const entry = { raw: raw, mas: mas, kdj: kdj };
      this._cache[symbol] = entry;
      return entry;
    } catch (err) {
      console.error('Failed to load history for ' + symbol + ':', err);
      return null;
    }
  },

  /** Simple Moving Average. Returns array same length as data, with null for first p-1 entries. */
  computeSMA(data, period) {
    const result = new Array(data.length).fill(null);
    if (data.length < period) return result;
    var sum = 0;
    for (var i = 0; i < period; i++) sum += data[i];
    result[period - 1] = sum / period;
    for (var i = period; i < data.length; i++) {
      sum += data[i] - data[i - period];
      result[i] = sum / period;
    }
    return result;
  },

  /** Compute KDJ values for all days.
   *  RSV(n) = (C - Ln) / (Hn - Ln) * 100
   *  K = 2/3 * prevK + 1/3 * RSV
   *  D = 2/3 * prevD + 1/3 * K
   *  J = 3*K - 2*D
   *  Returns [{k, d, j}] parallel to input arrays. First n-1 entries are null for all. */
  computeKDJ(highs, lows, closes, n) {
    const len = closes.length;
    const result = new Array(len);
    var k = 50, d = 50, j = 50;
    for (var i = 0; i < len; i++) {
      if (i < n - 1) {
        // Not enough data yet — use initial values
        result[i] = { k: k, d: d, j: j };
        continue;
      }
      // Find highest high and lowest low over past n days
      var hh = -Infinity, ll = Infinity;
      for (var t = i - n + 1; t <= i; t++) {
        if (highs[t] > hh) hh = highs[t];
        if (lows[t] < ll) ll = lows[t];
      }
      var rsv = (hh - ll === 0) ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
      k = (2/3) * k + (1/3) * rsv;
      d = (2/3) * d + (1/3) * k;
      j = 3 * k - 2 * d;
      result[i] = { k: k, d: d, j: j };
    }
    return result;
  },

  /** ======= MAIN RENDER ======= */
  async render(container, symbol) {
    const data = await this.fetchHistory(symbol);
    if (!data) {
      container.innerHTML = '<div style="padding:20px;text-align:center;color:#999;">无法加载历史数据</div>';
      return;
    }

    this._activeSymbol = symbol;
    this._activeContainer = container;

    // Build DOM
    container.innerHTML =
      '<div class="chart-wrap">' +
        '<div class="chart-panel chart-panel--price">' +
          '<canvas class="chart-canvas" id="canvas-price-' + symbol + '"></canvas>' +
        '</div>' +
        '<div class="chart-panel chart-panel--kdj">' +
          '<canvas class="chart-canvas" id="canvas-kdj-' + symbol + '"></canvas>' +
        '</div>' +
      '</div>';

    // Wait for DOM update then draw
    var self = this;
    setTimeout(function() {
      self._drawPrice(symbol, data);
      self._drawKDJ(symbol, data);
    }, 50);

    // Attach resize observer
    this._observeResize(symbol, data, container);
  },

  /** ======= PRICE CHART ======= */
  _drawPrice(symbol, data) {
    var canvas = document.getElementById('canvas-price-' + symbol);
    if (!canvas) return;
    var wrap = canvas.parentElement;
    var w = wrap.clientWidth;
    var h = 300;
    var dpr = this._dpr;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.scale(dpr, dpr);

    var raw = data.raw;
    var mas = data.mas;
    var len = raw.length;
    if (len < 2) return;

    // --- Layout ---
    var pad = { top: 20, right: 70, bottom: 20, left: 65 };
    var chartW = w - pad.left - pad.right;
    var chartH = h - pad.top - pad.bottom;
    var volTop = chartH * 0.70;  // volume area starts at 70% down
    var priceH = chartH * 0.70;  // price area height
    var volH   = chartH * 0.30;  // volume area height

    // --- Data ranges ---
    var allPriceVals = [];
    for (var i = 0; i < len; i++) {
      allPriceVals.push(raw[i].high);
      allPriceVals.push(raw[i].low);
      // Include MA values
      for (var k in mas) {
        var v = mas[k][i];
        if (v != null) allPriceVals.push(v);
      }
    }
    var priceMin = Math.min.apply(null, allPriceVals);
    var priceMax = Math.max.apply(null, allPriceVals);
    var priceRange = priceMax - priceMin || 1;
    priceMin -= priceRange * 0.05;
    priceMax += priceRange * 0.05;
    priceRange = priceMax - priceMin;

    var volMax = 0;
    for (var j = 0; j < len; j++) {
      if (raw[j].volume > volMax) volMax = raw[j].volume;
    }
    volMax = volMax || 1;

    // --- Helpers ---
    var xFor = function(i) { return pad.left + (i / Math.max(len - 1, 1)) * chartW; };
    var yForPrice = function(p) { return pad.top + priceH - ((p - priceMin) / priceRange) * priceH; };
    var yForVol = function(v) { return pad.top + chartH - ((v / volMax) * volH); };

    // --- Draw grid ---
    ctx.strokeStyle = this.COLORS.grid;
    ctx.lineWidth = 0.5;
    var ySteps = 5;
    for (var yi = 0; yi <= ySteps; yi++) {
      var y = pad.top + (priceH / ySteps) * yi;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + chartW, y);
      ctx.stroke();

      // Price labels
      var priceVal = priceMax - (priceRange / ySteps) * yi;
      ctx.fillStyle = this.COLORS.text;
      ctx.font = '10px -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText('$' + priceVal.toFixed(2), pad.left - 6, y + 3);
    }

    // --- Volume bars ---
    for (var vi = 0; vi < len; vi++) {
      var x = xFor(vi);
      var barW = Math.max(1, chartW / len * 0.7);
      var volY = yForVol(raw[vi].volume);
      var volBottom = pad.top + chartH;
      var isUp = vi > 0 ? raw[vi].close >= raw[vi - 1].close : true;
      ctx.fillStyle = isUp ? this.COLORS.volumeUp : this.COLORS.volumeDown;
      ctx.fillRect(x - barW / 2, volY, barW, volBottom - volY);
    }

    // --- MA lines ---
    var maColors = {
      ma5: this.COLORS.ma5, ma20: this.COLORS.ma20, ma30: this.COLORS.ma30,
      ma60: this.COLORS.ma60, ma120: this.COLORS.ma120, ma150: this.COLORS.ma150
    };
    var lineWidths = { ma5: 1, ma20: 1.5, ma30: 1, ma60: 1.5, ma120: 1, ma150: 1.5 };
    var maDefs = this.MA_PERIODS.map(function(p) { return { key: 'ma' + p, period: p }; });

    maDefs.forEach(function(def) {
      var arr = mas[def.key];
      if (!arr) return;
      ctx.strokeStyle = maColors[def.key];
      ctx.lineWidth = lineWidths[def.key] || 1;
      ctx.setLineDash(def.period >= 60 ? [4, 2] : []);
      ctx.beginPath();
      var started = false;
      for (var i = 0; i < len; i++) {
        if (arr[i] == null) continue;
        var px = xFor(i);
        var py = yForPrice(arr[i]);
        if (!started) { ctx.moveTo(px, py); started = true; }
        else { ctx.lineTo(px, py); }
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // --- Price line (thick, on top) ---
    ctx.strokeStyle = this.COLORS.price;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (var pi = 0; pi < len; pi++) {
      var ppx = xFor(pi);
      var ppy = yForPrice(raw[pi].close);
      if (pi === 0) ctx.moveTo(ppx, ppy);
      else ctx.lineTo(ppx, ppy);
    }
    ctx.stroke();

    // --- X-axis date labels ---
    ctx.fillStyle = this.COLORS.text;
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    var xLabelInterval = Math.max(1, Math.floor(len / 6));
    for (var xi = 0; xi < len; xi += xLabelInterval) {
      var d = raw[xi].date;
      // Format: MM-DD
      var parts = d.split('-');
      var label = parts[1] + '/' + parts[2];
      ctx.fillText(label, xFor(xi), pad.top + chartH + 14);
    }

    // --- Legend ---
    var legendX = pad.left + 8;
    var legendY = pad.top + 4;
    ctx.font = 'bold 11px -apple-system, sans-serif';
    ctx.fillStyle = this.COLORS.price;
    ctx.textAlign = 'left';
    ctx.fillText('── 价格', legendX, legendY);

    var legendItems = [
      { label: 'MA5', color: this.COLORS.ma5, dash: false },
      { label: 'MA20', color: this.COLORS.ma20, dash: false },
      { label: 'MA30', color: this.COLORS.ma30, dash: false },
      { label: 'MA60', color: this.COLORS.ma60, dash: true },
      { label: 'MA120', color: this.COLORS.ma120, dash: true },
      { label: 'MA150', color: this.COLORS.ma150, dash: true }
    ];
    var curX = legendX + 58;
    legendItems.forEach(function(item) {
      var lw = ctx.measureText(item.label).width + 12;
      if (curX + lw > pad.left + chartW - 10) { curX = legendX; legendY += 14; }
      ctx.font = '10px -apple-system, sans-serif';
      ctx.fillStyle = item.color;
      ctx.setLineDash(item.dash ? [3, 2] : []);
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(curX, legendY - 3);
      ctx.lineTo(curX + 16, legendY - 3);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillText(item.label, curX + 19, legendY);
      curX += lw;
    });

    // --- Crosshair interaction ---
    this._attachCrosshair(canvas, symbol, data, 'price', xFor, yForPrice, yForVol,
      pad, chartW, chartH, priceH, priceMin, priceMax, priceRange, volMax);
  },

  /** ======= KDJ CHART ======= */
  _drawKDJ(symbol, data) {
    var canvas = document.getElementById('canvas-kdj-' + symbol);
    if (!canvas) return;
    var wrap = canvas.parentElement;
    var w = wrap.clientWidth;
    var h = 180;
    var dpr = this._dpr;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.scale(dpr, dpr);

    var kdj = data.kdj;
    var raw = data.raw;
    var len = kdj.length;
    if (len < 2) return;

    var pad = { top: 15, right: 70, bottom: 20, left: 45 };
    var chartW = w - pad.left - pad.right;
    var chartH = h - pad.top - pad.bottom;

    // KDJ range: 0-100 nominal, but J can overshoot
    var jMin = Infinity, jMax = -Infinity;
    for (var i = 0; i < len; i++) {
      var jv = kdj[i].j;
      if (jv < jMin) jMin = jv;
      if (jv > jMax) jMax = jv;
    }
    var yMin = Math.min(0, Math.floor(jMin / 5) * 5 - 5);
    var yMax = Math.max(100, Math.ceil(jMax / 5) * 5 + 5);
    var yRange = yMax - yMin;

    var xFor = function(i) { return pad.left + (i / Math.max(len - 1, 1)) * chartW; };
    var yFor = function(v) { return pad.top + chartH - ((v - yMin) / yRange) * chartH; };

    // --- Reference bands ---
    // 20-80 band
    ctx.fillStyle = this.COLORS.ref20;
    ctx.fillRect(pad.left, yFor(80), chartW, yFor(20) - yFor(80));
    // 50 line
    ctx.strokeStyle = this.COLORS.ref50;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, yFor(50));
    ctx.lineTo(pad.left + chartW, yFor(50));
    ctx.stroke();
    ctx.setLineDash([]);

    // --- Grid ---
    ctx.strokeStyle = this.COLORS.grid;
    ctx.lineWidth = 0.5;
    var yTicks = [0, 20, 50, 80, 100];
    yTicks.forEach(function(tick) {
      if (tick < yMin || tick > yMax) return;
      var y = yFor(tick);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + chartW, y);
      ctx.stroke();
      ctx.fillStyle = ChartManager.COLORS.text;
      ctx.font = '10px -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(String(tick), pad.left - 6, y + 3);
    });

    // --- KDJ Lines ---
    var lines = [
      { arr: kdj.map(function(d) { return d.k; }), color: ChartManager.COLORS.kLine, label: 'K', width: 1.5, dash: false },
      { arr: kdj.map(function(d) { return d.d; }), color: ChartManager.COLORS.dLine, label: 'D', width: 1.5, dash: false },
      { arr: kdj.map(function(d) { return d.j; }), color: ChartManager.COLORS.jLine, label: 'J', width: 1.5, dash: false }
    ];

    lines.forEach(function(line) {
      ctx.strokeStyle = line.color;
      ctx.lineWidth = line.width;
      if (line.dash) ctx.setLineDash(line.dash);
      else ctx.setLineDash([]);
      ctx.beginPath();
      var started = false;
      for (var i = 0; i < len; i++) {
        if (line.arr[i] == null) continue;
        var px = xFor(i);
        var py = yFor(line.arr[i]);
        // Clamp to visible area
        if (py < pad.top) py = pad.top;
        if (py > pad.top + chartH) py = pad.top + chartH;
        if (!started) { ctx.moveTo(px, py); started = true; }
        else { ctx.lineTo(px, py); }
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // --- X-axis date labels ---
    ctx.fillStyle = this.COLORS.text;
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    var xLabelInterval = Math.max(1, Math.floor(len / 6));
    for (var xi = 0; xi < len; xi += xLabelInterval) {
      var parts = raw[xi].date.split('-');
      ctx.fillText(parts[1] + '/' + parts[2], xFor(xi), pad.top + chartH + 14);
    }

    // --- Legend ---
    var lx = pad.left + 8;
    var ly = pad.top + 2;
    var items = [
      { label: 'K', color: ChartManager.COLORS.kLine, dash: false },
      { label: 'D', color: ChartManager.COLORS.dLine, dash: false },
      { label: 'J', color: ChartManager.COLORS.jLine, dash: false }
    ];
    items.forEach(function(item) {
      ctx.font = 'bold 10px -apple-system, sans-serif';
      ctx.fillStyle = item.color;
      ctx.textAlign = 'left';
      ctx.setLineDash(item.dash ? [3, 2] : []);
      ctx.strokeStyle = item.color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(lx, ly - 2);
      ctx.lineTo(lx + 14, ly - 2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillText(item.label, lx + 17, ly + 1);
      lx += ctx.measureText(item.label).width + 26;
    });

    // --- Crosshair ---
    this._attachCrosshair(canvas, symbol, data, 'kdj', xFor, yFor, null,
      pad, chartW, chartH, 0, yMin, yMax, yRange, 0);
  },

  /** ======= CROSSHAIR + TOOLTIP ======= */
  _attachCrosshair(canvas, symbol, data, mode, xFor, yForPrice, yForVol,
                   pad, chartW, chartH, priceH, yPriceMin, yPriceMax, priceRange, volMax) {

    var tooltip = null;
    var savedImage = null;
    var self = this;
    var ctx = canvas.getContext('2d', { willReadFrequently: true });

    function saveImage() {
      savedImage = ctx.getImageData(0, 0, canvas.width, canvas.height);
    }

    function restoreImage() {
      if (savedImage) ctx.putImageData(savedImage, 0, 0);
    }

    function ensureTooltip() {
      if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.className = 'chart-tooltip';
        canvas.parentElement.appendChild(tooltip);
      }
      return tooltip;
    }

    function hideTooltip() {
      restoreImage();
      if (tooltip) { tooltip.style.display = 'none'; }
    }

    function showTooltip(e) {
      var rect = canvas.getBoundingClientRect();
      var mx = e.clientX - rect.left;
      var my = e.clientY - rect.top;

      var len = data.raw.length;
      var idx = Math.round(((mx - pad.left) / chartW) * (len - 1));
      if (idx < 0) idx = 0;
      if (idx >= len) idx = len - 1;

      restoreImage();

      var tt = ensureTooltip();
      var raw = data.raw[idx];
      var dateParts = raw.date.split('-');
      var dateStr = dateParts[0] + '-' + dateParts[1] + '-' + dateParts[2];

      var dpr = self._dpr;
      ctx.save();
      ctx.scale(dpr, dpr);
      var cx = xFor(idx);
      ctx.strokeStyle = self.COLORS.crosshair;
      ctx.lineWidth = 0.8;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(cx, pad.top);
      ctx.lineTo(cx, pad.top + chartH);
      ctx.stroke();
      ctx.setLineDash([]);

      if (mode === 'price') {
        // Build tooltip
        var lines = [];
        lines.push('<div class="tt-date">' + dateStr + '</div>');
        lines.push('<div>O: <b>$' + raw.open.toFixed(2) + '</b> H: <b>$' + raw.high.toFixed(2) + '</b> L: <b>$' + raw.low.toFixed(2) + '</b></div>');
        lines.push('<div style="color:' + self.COLORS.price + '">Close: <b>$' + raw.close.toFixed(2) + '</b></div>');

        var maKeys = ['ma5','ma20','ma30','ma60','ma120','ma150'];
        var maColors = { ma5: self.COLORS.ma5, ma20: self.COLORS.ma20, ma30: self.COLORS.ma30,
                         ma60: self.COLORS.ma60, ma120: self.COLORS.ma120, ma150: self.COLORS.ma150 };
        maKeys.forEach(function(k) {
          var v = data.mas[k][idx];
          if (v != null) {
            var period = k.replace('ma', '');
            lines.push('<div style="color:' + maColors[k] + '">MA' + period + ': <b>$' + v.toFixed(2) + '</b></div>');
          }
        });
        lines.push('<div>Vol: <b>' + Indicators.formatVolume(raw.volume) + '</b></div>');

        tt.innerHTML = lines.join('');
      } else {
        // KDJ mode
        var kdj = data.kdj[idx];
        var lines2 = [];
        lines2.push('<div class="tt-date">' + dateStr + '</div>');
        lines2.push('<div style="color:' + self.COLORS.kLine + '">K: <b>' + kdj.k.toFixed(1) + '</b></div>');
        lines2.push('<div style="color:' + self.COLORS.dLine + '">D: <b>' + kdj.d.toFixed(1) + '</b></div>');
        lines2.push('<div style="color:' + self.COLORS.jLine + '">J: <b>' + kdj.j.toFixed(1) + '</b></div>');

        tt.innerHTML = lines2.join('');
      }

      tt.style.display = 'block';

      var ttW = tt.offsetWidth || 200;
      var ttH = tt.offsetHeight || 120;
      var tx = cx + 12;
      var ty = pad.top + 4;
      if (tx + ttW > pad.left + chartW + 8) tx = cx - ttW - 12;
      if (tx < 0) tx = 4;
      if (ty + ttH > pad.top + chartH + 8) ty = pad.top + chartH - ttH - 4;
      if (ty < 0) ty = 4;
      tt.style.left = tx + 'px';
      tt.style.top = ty + 'px';

      ctx.restore();
    }

    // Remove old listeners if any (stored on the canvas DOM element)
    if (canvas._chartListeners) {
      canvas.removeEventListener('mousemove', canvas._chartListeners.mousemove);
      canvas.removeEventListener('mouseleave', canvas._chartListeners.mouseleave);
      canvas.removeEventListener('touchmove', canvas._chartListeners.touchmove);
      canvas.removeEventListener('touchend', canvas._chartListeners.touchend);
    }

    var touchHandler = function(e) {
      e.preventDefault();
      showTooltip(e.touches[0]);
    };

    canvas.addEventListener('mousemove', showTooltip);
    canvas.addEventListener('mouseleave', hideTooltip);
    canvas.addEventListener('touchmove', touchHandler);
    canvas.addEventListener('touchend', hideTooltip);

    // Store references for cleanup on next redraw
    canvas._chartListeners = {
      mousemove: showTooltip,
      mouseleave: hideTooltip,
      touchmove: touchHandler,
      touchend: hideTooltip
    };

    // Save image after draw completes
    setTimeout(function() { saveImage(); }, 100);
  },

  /** ======= RESIZE HANDLING ======= */
  _observeResize(symbol, data, container) {
    var self = this;
    var ro = new ResizeObserver(function() {
      if (self._activeSymbol === symbol && self._activeContainer === container) {
        // Remove old tooltips
        var oldTT = container.querySelectorAll('.chart-tooltip');
        oldTT.forEach(function(el) { el.remove(); });
        self._drawPrice(symbol, data);
        self._drawKDJ(symbol, data);
      }
    });
    ro.observe(container.querySelector('.chart-panel--price'));
  },

  /** Clear the active chart */
  destroy() {
    this._activeSymbol = null;
    this._activeContainer = null;
  }
};
