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
    if (status.kOverbought) parts.push('K值处于超买区(>80)，短期有回调风险');
    else if (status.kOversold) parts.push('K值处于超卖区(<20)，短期有反弹机会');
    else parts.push('K值处于正常区间');
    if (status.goldenCross) parts.push('K线上穿D线形成金叉，短期看多信号');
    else if (status.deathCross) parts.push('K线下穿D线形成死叉，短期看空信号');
    else parts.push('K线与D线未形成交叉');
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
    if (kdj.kOverbought) points.push('注意KDJ超买风险，追高需谨慎');
    if (kdj.kOversold) points.push('KDJ超卖，可能存在超跌反弹机会');
    if (change_pct > 2) points.push('当日涨幅较大，短期获利盘可能回吐');
    if (change_pct < -2) points.push('当日跌幅较大，恐慌情绪可能过度');
    return points.join('；') + '。';
  },

  /**
   * Check if golden cross is currently active (K > D).
   */
  hasGoldenCross(k, d) {
    return k > d;
  },

  /**
   * Get KDJ signal interpretation text for card display.
   * Returns { text, cssClass, hasGoldenCross, hasDeathCross }
   */
  getKDJSignalText(k, d, j) {
    const parts = [];
    let cssClass = 'kdj-normal';

    // Overbought / Oversold detection (primary signal)
    const isOversold = d < 20 && j < 0;
    const isOverbought = d > 80 && j > 100;
    const isGoldenCross = k > d;
    const isDeathCross = k < d;

    if (isOversold) {
      parts.push('🔴 超卖（潜在买点）');
      cssClass = 'kdj-oversold';
    } else if (isOverbought) {
      parts.push('🟢 超买（潜在卖点）');
      cssClass = 'kdj-overbought';
    } else {
      // Normal range
      if (k < 30) { parts.push('KDJ 偏低'); cssClass = 'kdj-low'; }
      else if (k > 70) { parts.push('KDJ 偏高'); cssClass = 'kdj-high'; }
      else { parts.push('KDJ 正常'); }
    }

    // Cross signals (can coexist with overbought/oversold)
    if (isGoldenCross) {
      parts.push('✨ 金叉');
      if (cssClass === 'kdj-normal' || cssClass === 'kdj-low') cssClass = 'kdj-golden';
    } else if (isDeathCross) {
      parts.push('💀 死叉');
      if (cssClass === 'kdj-normal' || cssClass === 'kdj-high') cssClass = 'kdj-death';
    }

    return {
      text: parts.join(' · '),
      cssClass: cssClass,
      isOversold: isOversold,
      isOverbought: isOverbought,
      hasGoldenCross: isGoldenCross,
      hasDeathCross: isDeathCross
    };
  },

  /**
   * Determine market phase: 右侧 (uptrend), 左侧 (downtrend), or 震荡 (ranging).
   * Returns { phase, cssClass, label }
   */
  getMarketPhase(stock) {
    const { close, ma5, ma20, k } = stock;
    const aboveMA20 = close > ma20;
    const ma5AboveMA20 = ma5 > ma20;
    const kAbove50 = k > 50;

    if (aboveMA20 && ma5AboveMA20 && kAbove50) {
      return { phase: 'right', cssClass: 'phase-right', label: '右侧' };
    } else if (!aboveMA20 && !ma5AboveMA20 && !kAbove50) {
      return { phase: 'left', cssClass: 'phase-left', label: '左侧' };
    } else {
      return { phase: 'ranging', cssClass: 'phase-ranging', label: '震荡' };
    }
  },

  /**
   * Simplified right-side indicator analysis based on available snapshot data.
   * Uses fixed experience parameters (L=-3%, U=+1%) when historical data is unavailable.
   * Returns a structured analysis object.
   */
  analyzeRightSide(stock) {
    const { close, ma20, ma5, change_pct } = stock;
    if (!ma20) return null;

    // MA20 trend assessment (approximation from available data)
    const ma20Slope = ma5 && ma20 ? ((ma5 - ma20) / ma20 * 100) : 0;
    let trendDirection, trendStrength;
    if (ma20Slope > 0.5) { trendDirection = '上升'; trendStrength = '强'; }
    else if (ma20Slope > 0.1) { trendDirection = '温和上升'; trendStrength = '中'; }
    else if (ma20Slope > -0.1) { trendDirection = '走平'; trendStrength = '弱'; }
    else if (ma20Slope > -0.5) { trendDirection = '温和下降'; trendStrength = '中'; }
    else { trendDirection = '下降'; trendStrength = '强'; }

    // Current deviation from MA20
    const deviation = ((close - ma20) / ma20 * 100);

    // Experience-based parameters (L=-3%, U=+1%)
    const L = -3;  // historical deepest callback
    const U = 1;   // historical shallowest callback

    // Buy zone calculation
    const lowerPrice = ma20 * (1 + L / 100);   // B1
    const midPrice = ma20;                       // B2 = MA20 line
    const upperPrice = ma20 * (1 + U / 100);    // B3

    // Stop loss price
    const stopLoss = lowerPrice * 0.98;

    // Applicability check
    const isApplicable = ma20Slope > 0; // MA20 must be trending up for right-side trading

    return {
      trendDirection: trendDirection,
      trendStrength: trendStrength,
      ma20Slope: ma20Slope,
      deviation: deviation,
      deviationPct: deviation.toFixed(2),
      L: L,
      U: U,
      lowerPrice: lowerPrice,
      midPrice: midPrice,
      upperPrice: upperPrice,
      stopLoss: stopLoss,
      isApplicable: isApplicable,
      // Buy point status
      buyPoints: [
        { name: 'B1 试探买点', price: lowerPrice, ratio: '20%', desc: '股价触及历史回调下限' },
        { name: 'B2 标准买点', price: midPrice, ratio: '30%', desc: '股价回调至20日均线' },
        { name: 'B3 确认买点', price: upperPrice, ratio: '50%', desc: '股价触及回调上限+企稳信号' }
      ],
      currentPriceRelative: deviation > U ? '高于买入区间上限' :
                           deviation < L ? '低于买入区间下限（不建议买入）' :
                           deviation > 0 ? '在B2-B3区间' :
                           deviation > -1 ? '在B1-B2区间' : '接近B1买点'
    };
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
