/**
 * chart.js — Lightweight Charts v4 wrapper for MIDAS.
 * Handles: candlestick rendering, volume sub-panel, SMA overlays,
 * trade markers (entry/exit), equity curve, and pattern window highlights.
 */

window.MIDASChart = (() => {
  let chart = null;
  let candleSeries = null;
  let volumeSeries = null;
  let sma10Series = null;
  let sma20Series = null;
  let sma50Series = null;
  let equitySeries = null;
  let highlightBands = [];  // DOM elements for pattern window overlays

  const container = document.getElementById('chart-container');
  const placeholder = document.getElementById('chart-placeholder');

  // ── Chart colours ─────────────────────────────────────────────────────────
  const COLORS = {
    up:       '#26a641',
    down:     '#f85149',
    wick_up:  '#26a641',
    wick_dn:  '#f85149',
    sma10:    '#ec4899',
    sma20:    '#60a5fa',
    sma50:    '#f59e0b',
    volume:   'rgba(96, 165, 250, 0.25)',
    equity:   '#a78bfa',
    bg:       '#0d1117',
    grid:     '#21262d',
    border:   '#30363d',
    text:     '#7d8590',
    crosshair:'#30363d',
  };

  // ── SMA computation ───────────────────────────────────────────────────────
  function computeSMA(data, period) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) continue;
      const slice = data.slice(i - period + 1, i + 1);
      const avg = slice.reduce((s, d) => s + d.close, 0) / period;
      result.push({ time: data[i].time, value: parseFloat(avg.toFixed(4)) });
    }
    return result;
  }

  // ── Init chart ────────────────────────────────────────────────────────────
  function initChart() {
    if (chart) {
      chart.remove();
      chart = null;
    }

    chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { color: COLORS.bg },
        textColor: COLORS.text,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: COLORS.crosshair, labelBackgroundColor: '#161b22' },
        horzLine: { color: COLORS.crosshair, labelBackgroundColor: '#161b22' },
      },
      rightPriceScale: {
        borderColor: COLORS.border,
        textColor: COLORS.text,
      },
      timeScale: {
        borderColor: COLORS.border,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Candlestick series
    candleSeries = chart.addCandlestickSeries({
      upColor:          COLORS.up,
      downColor:        COLORS.down,
      borderUpColor:    COLORS.wick_up,
      borderDownColor:  COLORS.wick_dn,
      wickUpColor:      COLORS.wick_up,
      wickDownColor:    COLORS.wick_dn,
    });

    // Volume series on separate scale
    volumeSeries = chart.addHistogramSeries({
      color: COLORS.volume,
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.80, bottom: 0 },
    });

    // SMA series (hidden by default until toggled)
    sma10Series = chart.addLineSeries({
      color: COLORS.sma10,
      lineWidth: 1,
      visible: MIDAS.state.indicators.sma10,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    sma20Series = chart.addLineSeries({
      color: COLORS.sma20,
      lineWidth: 1,
      visible: MIDAS.state.indicators.sma20,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    sma50Series = chart.addLineSeries({
      color: COLORS.sma50,
      lineWidth: 1,
      visible: MIDAS.state.indicators.sma50,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (chart) {
        chart.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    });
    ro.observe(container);

    // Crosshair → update topbar price display
    chart.subscribeCrosshairMove(param => {
      if (!param || !param.time || !candleSeries) return;
      const ohlcv = param.seriesData.get(candleSeries);
      if (!ohlcv) return;
      updatePriceDisplay(ohlcv.close, ohlcv.close - ohlcv.open);
    });
  }

  // ── Load candles ──────────────────────────────────────────────────────────
  function loadCandles(rows) {
    if (!rows || rows.length === 0) return;

    placeholder.style.display = 'none';

    if (!chart) initChart();

    // Convert to Lightweight Charts format (time = Unix or 'YYYY-MM-DD')
    const candles = rows.map(r => ({
      time: r.date,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    }));
    const volumes = rows.map(r => ({
      time: r.date,
      value: r.volume,
      color: r.close >= r.open ? 'rgba(38,166,65,0.25)' : 'rgba(248,81,73,0.25)',
    }));

    candleSeries.setData(candles);
    volumeSeries.setData(volumes);

    // SMAs
    const sma10Data = computeSMA(candles, 10);
    const sma20Data = computeSMA(candles, 20);
    const sma50Data = computeSMA(candles, 50);
    sma10Series.setData(sma10Data);
    sma20Series.setData(sma20Data);
    sma50Series.setData(sma50Data);

    // Update volume visibility
    volumeSeries.applyOptions({ visible: MIDAS.state.indicators.volume });

    // Fit
    chart.timeScale().fitContent();

    // Update topbar price
    const last = rows[rows.length - 1];
    const prev = rows[rows.length - 2];
    if (last) updatePriceDisplay(last.close, prev ? last.close - prev.close : 0);

    // Update data info
    document.getElementById('chart-data-info').textContent =
      `${rows.length} bars  ${rows[0].date} → ${rows[rows.length-1].date}`;
    document.getElementById('chart-ticker').textContent = MIDAS.state.ticker || '—';
  }

  // ── Indicator toggles ─────────────────────────────────────────────────────
  function toggleIndicator(name, visible) {
    MIDAS.state.indicators[name] = visible;
    if (name === 'sma10' && sma10Series) sma10Series.applyOptions({ visible });
    if (name === 'sma20' && sma20Series) sma20Series.applyOptions({ visible });
    if (name === 'sma50' && sma50Series) sma50Series.applyOptions({ visible });
    if (name === 'volume' && volumeSeries) volumeSeries.applyOptions({ visible });
  }

  // ── Trade markers ─────────────────────────────────────────────────────────
  function addTradeMarkers(trades) {
    if (!candleSeries || !trades || trades.length === 0) return;

    const markers = [];
    for (const t of trades) {
      markers.push({
        time: t.entry_date,
        position: 'belowBar',
        color: t.direction === 'LONG' ? '#26a641' : '#f85149',
        shape: 'arrowUp',
        text: t.direction === 'LONG' ? '▲' : '▼',
        size: 1,
      });
      markers.push({
        time: t.exit_date,
        position: 'aboveBar',
        color: t.return_pct >= 0 ? '#26a641' : '#f85149',
        shape: 'arrowDown',
        text: `${t.return_pct >= 0 ? '+' : ''}${t.return_pct?.toFixed(1)}%`,
        size: 1,
      });
    }
    // Sort markers by time (required by Lightweight Charts)
    markers.sort((a, b) => a.time < b.time ? -1 : 1);
    candleSeries.setMarkers(markers);
  }

  function clearMarkers() {
    if (candleSeries) candleSeries.setMarkers([]);
    if (equitySeries) {
      chart.removeSeries(equitySeries);
      equitySeries = null;
    }
  }

  // ── Equity curve ──────────────────────────────────────────────────────────
  function showEquityCurve(equityData) {
    if (!chart || !equityData || equityData.length === 0) return;

    if (equitySeries) {
      chart.removeSeries(equitySeries);
    }

    equitySeries = chart.addLineSeries({
      color: '#a78bfa',
      lineWidth: 2,
      priceScaleId: 'equity',
      priceLineVisible: false,
      lastValueVisible: true,
    });
    chart.priceScale('equity').applyOptions({
      scaleMargins: { top: 0, bottom: 0.55 },
    });

    const data = equityData.map(p => ({
      time: p.date,
      value: parseFloat(p.equity),
    }));
    equitySeries.setData(data);
  }

  // ── Pattern window highlights ─────────────────────────────────────────────
  function clearHighlights() {
    highlightBands.forEach(el => el.remove());
    highlightBands = [];
  }

  function highlightWindow(dateFrom, dateTo) {
    if (!chart) return;

    // Convert dates to x-pixel positions using the time scale
    const ts = chart.timeScale();
    const x1 = ts.timeToCoordinate(dateFrom);
    const x2 = ts.timeToCoordinate(dateTo);

    if (x1 === null || x2 === null) return;

    const band = document.createElement('div');
    band.className = 'chart-highlight';
    band.style.left = `${Math.min(x1, x2)}px`;
    band.style.width = `${Math.abs(x2 - x1)}px`;
    container.style.position = 'relative';
    container.appendChild(band);
    highlightBands.push(band);
  }

  function jumpToWindow(dateFrom, dateTo) {
    if (!chart) return;
    clearHighlights();
    chart.timeScale().setVisibleRange({ from: dateFrom, to: dateTo });
    // Add highlight after a short delay (wait for scroll)
    setTimeout(() => highlightWindow(dateFrom, dateTo), 100);
  }

  // ── Price display ─────────────────────────────────────────────────────────
  function updatePriceDisplay(price, change) {
    const priceEl = document.getElementById('chart-price');
    const changeEl = document.getElementById('chart-change');
    priceEl.textContent = `$${parseFloat(price).toFixed(2)}`;
    const changePct = (change / (price - change)) * 100;
    const sign = change >= 0 ? '+' : '';
    changeEl.textContent = `${sign}${change.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
    changeEl.className = `chart-change-label ${change >= 0 ? 'up' : 'down'}`;
  }

  function reset() {
    if (candleSeries) candleSeries.setData([]);
    if (volumeSeries) volumeSeries.setData([]);
    if (sma10Series) sma10Series.setData([]);
    if (sma20Series) sma20Series.setData([]);
    if (sma50Series) sma50Series.setData([]);
    clearMarkers();
    clearHighlights();
    document.getElementById('chart-ticker').textContent = '—';
    document.getElementById('chart-price').textContent = '';
    document.getElementById('chart-change').textContent = '';
    document.getElementById('chart-data-info').textContent = '';
    placeholder.style.display = 'flex';
  }

  // ── Indicator toggle buttons ──────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.chart-indicator-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const ind = btn.dataset.ind;
        const isActive = btn.classList.toggle('active');
        toggleIndicator(ind, isActive);
      });
    });

    // Navigation Controls
    document.getElementById('nav-zoom-in')?.addEventListener('click', () => zoomChart(0.8));
    document.getElementById('nav-zoom-out')?.addEventListener('click', () => zoomChart(1.2));
    document.getElementById('nav-pan-left')?.addEventListener('click', () => panChart(-0.2));
    document.getElementById('nav-pan-right')?.addEventListener('click', () => panChart(0.2));
    document.getElementById('nav-reset')?.addEventListener('click', () => {
      if (chart) chart.timeScale().fitContent();
    });
  });

  function zoomChart(factor) {
    if (!chart) return;
    const ts = chart.timeScale();
    const range = ts.getVisibleLogicalRange();
    if (!range) return;
    const len = range.to - range.from;
    const center = range.from + len / 2;
    const newLen = len * factor;
    ts.setVisibleLogicalRange({ from: center - newLen / 2, to: center + newLen / 2 });
  }

  function panChart(factor) {
    if (!chart) return;
    const ts = chart.timeScale();
    const range = ts.getVisibleLogicalRange();
    if (!range) return;
    const len = range.to - range.from;
    const shift = len * factor;
    ts.setVisibleLogicalRange({ from: range.from + shift, to: range.to + shift });
  }

  return {
    loadCandles,
    addTradeMarkers,
    clearMarkers,
    showEquityCurve,
    highlightWindow,
    jumpToWindow,
    clearHighlights,
    reset,
    toggleIndicator,
  };
})();
