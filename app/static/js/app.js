/**
 * app.js — Global state, utilities, and router for MIDAS SPA.
 * Loaded first. All other modules attach to window.MIDAS.
 */

window.MIDAS = (() => {
  const DEFAULT_BACKTEST_EMPTY = 'Select strategies and load data,<br>then click Run Backtest';
  const DEFAULT_RUNNING_MSG = 'Running backtest…';
  const DEFAULT_INTERPRET_LABEL = '<span>🔮</span> Ask Gemma to interpret results';

  // ── Global state ──────────────────────────────────────────────────────────
  const state = {
    ticker: '',
    dateFrom: null,
    dateTo: null,
    batchTickers: [],
    sp500Mode: false,
    preset: '3Y',
    ohlcvData: [],
    strategies: [],
    selectedStrategies: new Set(),
    lastBacktestResult: null,
    lastRunId: null,
    lastScanResult: null,
    ollamaOnline: false,
    activePanel: 'backtest',
    indicators: {
      sma10: false,
      sma20: true,
      sma50: false,
      volume: true,
    },
  };

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const batchBtn = document.getElementById('batch-mode-btn');
  const sp500ModeBtn = document.getElementById('sp500-mode-btn');
  const batchModal = document.getElementById('batch-modal');
  const batchInput = document.getElementById('batch-ticker-input');
  const tickerInput = document.getElementById('ticker-input');
  const activeScopeSection = document.getElementById('active-scope-section');
  const activeScopeTray = document.getElementById('active-scope-tray');
  const backtestEmpty = document.getElementById('backtest-empty');
  const backtestResults = document.getElementById('backtest-results');
  const backtestRunning = document.getElementById('backtest-running');
  const interpretationBox = document.getElementById('interpretation-box');
  const interpretBtn = document.getElementById('interpret-btn');
  const backtestRunningMsg = document.getElementById('backtest-running-msg');
  const chartWrap = document.getElementById('chart-wrap');
  const scanTableWrap = document.getElementById('scan-table-wrap');
  const runModeSwitch = document.getElementById('run-mode-switch');
  const resetBtn = document.getElementById('reset-btn');

  // ── Toast ─────────────────────────────────────────────────────────────────
  function toast(message, type = 'info', duration = 4000) {
    const icons = { success: '✓', error: '✕', warn: '⚠', info: 'ℹ' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ'}</span><span>${message}</span>`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  // ── API helper ────────────────────────────────────────────────────────────
  async function api(method, path, body, isFormData = false) {
    const opts = { method };
    if (body && !isFormData) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(body);
    } else if (body && isFormData) {
      opts.body = body;
    }
    const res = await fetch(`/api${path}`, opts);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        detail = err.detail || JSON.stringify(err);
        if (typeof detail === 'object') detail = detail.error || JSON.stringify(detail);
      } catch (_) {}
      throw new Error(detail);
    }
    return res.json();
  }

  function clearAnalysisState() {
    state.lastBacktestResult = null;
    state.lastRunId = null;
    state.lastScanResult = null;
  }

  function getScopeInfo() {
    if (state.sp500Mode) {
      return {
        kind: 'sp500',
        label: 'S&P 500',
        meta: 'Universe',
        title: 'S&P 500 universe selected',
        runLabel: 'S&P 500',
      };
    }

    if (state.batchTickers.length > 0) {
      return {
        kind: 'batch',
        label: 'Batch',
        meta: `${state.batchTickers.length} tickers`,
        title: state.batchTickers.join(', '),
        runLabel: `batch (${state.batchTickers.length} tickers)`,
      };
    }

    if (state.ticker) {
      return {
        kind: 'ticker',
        label: state.ticker,
        meta: 'Single ticker',
        title: state.ticker,
        runLabel: state.ticker,
      };
    }

    return {
      kind: 'none',
      label: '',
      meta: '',
      title: '',
      runLabel: '',
    };
  }

  function syncScopeUi() {
    const scope = getScopeInfo();

    if (scope.kind === 'sp500') {
      if (tickerInput) {
        tickerInput.value = 'S&P 500';
        tickerInput.disabled = true;
      }
      batchBtn?.classList.remove('active');
      sp500ModeBtn?.classList.add('active');
    } else if (scope.kind === 'batch') {
      if (tickerInput) {
        tickerInput.value = `BATCH (${state.batchTickers.length})`;
        tickerInput.disabled = true;
      }
      batchBtn?.classList.add('active');
      sp500ModeBtn?.classList.remove('active');
    } else {
      if (tickerInput) {
        tickerInput.disabled = false;
        tickerInput.value = state.ticker || '';
      }
      batchBtn?.classList.remove('active');
      sp500ModeBtn?.classList.remove('active');
    }

    if (!activeScopeSection || !activeScopeTray) return;

    if (scope.kind === 'none') {
      activeScopeSection.classList.add('hidden');
      activeScopeTray.innerHTML = '';
      return;
    }

    activeScopeSection.classList.remove('hidden');
    activeScopeTray.innerHTML = `
      <div class="active-scope-tile" title="${scope.title}">
        <div class="active-scope-body">
          <span class="active-scope-label">${scope.label}</span>
          <span class="active-scope-meta">${scope.meta}</span>
        </div>
        <button class="active-scope-close" data-scope="${scope.kind}" title="Clear selection">×</button>
      </div>
    `;
  }

  function setScope(kind, payload = {}) {
    if (kind === 'sp500') {
      state.sp500Mode = true;
      state.batchTickers = [];
      state.ticker = 'S&P 500';
      state.ohlcvData = [];
    } else if (kind === 'batch') {
      state.sp500Mode = false;
      state.batchTickers = [...(payload.tickers || [])];
      state.ticker = state.batchTickers.length ? 'BATCH' : '';
      state.ohlcvData = [];
    } else if (kind === 'ticker') {
      state.sp500Mode = false;
      state.batchTickers = [];
      state.ticker = (payload.ticker || '').trim().toUpperCase();
      if (payload.clearData !== false) {
        state.ohlcvData = [];
      }
    } else {
      state.sp500Mode = false;
      state.batchTickers = [];
      state.ticker = '';
      state.ohlcvData = [];
    }

    syncScopeUi();
    if (window.updateRunBtn) window.updateRunBtn();
    window.dispatchEvent(new CustomEvent('midas:scopechange', { detail: getScopeInfo() }));
  }

  function setSingleTickerScope(ticker, options = {}) {
    setScope('ticker', { ticker, clearData: options.clearData });
  }

  function setBatchScope(tickers) {
    setScope('batch', { tickers });
  }

  function setSp500Scope() {
    setScope('sp500');
  }

  function showChartView() {
    chartWrap?.classList.remove('hidden');
    scanTableWrap?.classList.add('hidden');
  }

  function showScanView() {
    chartWrap?.classList.add('hidden');
    scanTableWrap?.classList.remove('hidden');
  }

  function resetResultsUi() {
    backtestEmpty?.classList.remove('hidden');
    backtestResults?.classList.add('hidden');
    backtestRunning?.classList.add('hidden');
    interpretationBox?.classList.remove('visible');
    if (backtestEmpty?.querySelector('.empty-text')) {
      backtestEmpty.querySelector('.empty-text').innerHTML = DEFAULT_BACKTEST_EMPTY;
    }
    if (backtestRunningMsg) {
      backtestRunningMsg.textContent = DEFAULT_RUNNING_MSG;
    }
    if (interpretBtn) {
      interpretBtn.dataset.mode = 'backtest';
      delete interpretBtn.dataset.scope;
      interpretBtn.disabled = false;
      interpretBtn.innerHTML = DEFAULT_INTERPRET_LABEL;
    }
    showChartView();
  }

  function clearScope(kind = 'active', options = {}) {
    if (kind === 'sp500' && !state.sp500Mode) return;
    if (kind === 'batch' && state.batchTickers.length === 0) return;
    setScope('none');
    clearAnalysisState();
    resetResultsUi();
    if (runModeSwitch) runModeSwitch.checked = false;
    if (window.MIDASChart && options.resetChart !== false) {
      MIDASChart.reset();
    }
  }

  function resetApp() {
    clearScope('active');
    const dates = presetToDates('3Y');
    state.preset = '3Y';
    state.dateFrom = dates.from;
    state.dateTo = dates.to;
    document.getElementById('date-from').value = dates.from;
    document.getElementById('date-to').value = dates.to;
    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.preset === '3Y');
    });
    state.selectedStrategies.clear();
    window.dispatchEvent(new CustomEvent('midas:reset'));
  }

  function handleScopeAction(kind, message) {
    clearAnalysisState();
    resetResultsUi();
    setScope(kind.type, kind.payload || {});
    if (window.MIDASChart) {
      MIDASChart.reset();
    }
    toast(message, 'success');
  }

  activeScopeTray?.addEventListener('click', e => {
    const closeBtn = e.target.closest('.active-scope-close');
    if (!closeBtn) return;
    clearScope(closeBtn.dataset.scope || 'active');
    toast('Selection cleared', 'info');
  });

  sp500ModeBtn?.addEventListener('click', () => {
    handleScopeAction({ type: 'sp500' }, 'S&P 500 mode active. Click RUN!');
  });

  batchBtn?.addEventListener('click', () => {
    batchInput.value = state.batchTickers.join(', ');
    batchModal.classList.remove('hidden');
  });

  document.getElementById('batch-cancel-btn')?.addEventListener('click', () => {
    batchModal.classList.add('hidden');
  });

  document.getElementById('batch-apply-btn')?.addEventListener('click', () => {
    const tickers = batchInput.value
      .split(/[\n,]+/)
      .map(t => t.trim().toUpperCase())
      .filter(Boolean);

    if (tickers.length === 0) {
      clearScope('active');
      toast('No tickers provided. Batch mode disabled.', 'warn');
      batchModal.classList.add('hidden');
      return;
    }

    if (tickers.length > 100) {
      toast(`Truncating ${tickers.length} tickers to 100 maximum.`, 'warn');
      tickers.splice(100);
    }

    handleScopeAction({ type: 'batch', payload: { tickers } }, `Batch mode enabled: ${tickers.length} tickers`);
    batchModal.classList.add('hidden');
  });

  // ── Auto Load Data ────────────────────────────────────────────────────────
  async function autoLoadData() {
    if (state.batchTickers.length > 0 || state.sp500Mode) {
      return;
    }

    const ticker = tickerInput ? tickerInput.value.trim().toUpperCase() : '';
    if (!ticker) {
      clearScope('active');
      return;
    }

    setSingleTickerScope(ticker);
    clearAnalysisState();
    resetResultsUi();

    try {
      await api('POST', '/data/fetch', {
        ticker: state.ticker,
        date_from: state.dateFrom,
        date_to: state.dateTo,
        preset: state.preset,
      });

      const rowsRes = await api('GET', `/data/${state.ticker}?date_from=${state.dateFrom || ''}&date_to=${state.dateTo || ''}&preset=${state.preset || ''}`);
      state.ohlcvData = rowsRes.data || [];
      if (window.MIDASChart && state.ohlcvData.length > 0) {
        MIDASChart.loadCandles(state.ohlcvData);
      }
    } catch (e) {
      toast(`Error loading data: ${e.message}`, 'error');
    } finally {
      if (window.updateRunBtn) window.updateRunBtn();
    }
  }

  if (tickerInput) {
    tickerInput.addEventListener('blur', autoLoadData);
    tickerInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        tickerInput.blur();
      }
    });
  }

  // ── Date utilities ────────────────────────────────────────────────────────
  function formatLocalDate(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function today() {
    return formatLocalDate(new Date());
  }

  function presetToDates(preset) {
    const now = new Date();
    const presets = {
      '1Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 1); return d; },
      '3Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 3); return d; },
      '5Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 5); return d; },
      '10Y': () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 10); return d; },
      'MAX': () => new Date('1990-01-01'),
    };
    const fn = presets[preset];
    if (!fn) return { from: formatLocalDate(presets['1Y']()), to: formatLocalDate(now) };
    return { from: formatLocalDate(fn()), to: formatLocalDate(now) };
  }

  function switchPanel(panelName) {
    state.activePanel = panelName;
    document.querySelectorAll('.panel-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.panel === panelName);
    });
    document.getElementById('backtest-panel').classList.toggle('hidden', panelName !== 'backtest');
    document.getElementById('gemma-panel').classList.toggle('hidden', panelName !== 'gemma');
    document.getElementById('chat-panel')?.classList.toggle('hidden', panelName !== 'chat');
    document.getElementById('history-panel').classList.toggle('hidden', panelName !== 'history');
  }

  // ── Status check on load ──────────────────────────────────────────────────
  async function checkHealth() {
    try {
      const h = await api('GET', '/health');
      const dot = document.getElementById('ollama-dot');
      const label = document.getElementById('ollama-label');
      state.ollamaOnline = h.ollama?.available ?? false;
      if (state.ollamaOnline) {
        dot.className = 'status-dot online';
        const models = h.ollama.models || [];
        label.textContent = 'Gemma ✓';
        label.title = `Models: ${models.join(', ')}`;
      } else {
        dot.className = 'status-dot offline';
        label.textContent = 'Gemma offline';
        label.title = 'Run: ollama serve';
      }
      const cacheLabel = document.getElementById('cache-label');
      cacheLabel.textContent = `${h.cached_tickers || 0} tickers cached`;
    } catch (e) {
      console.warn('Health check failed:', e);
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    const dates = presetToDates(state.preset);
    state.dateFrom = dates.from;
    state.dateTo = dates.to;
    document.getElementById('date-from').value = dates.from;
    document.getElementById('date-to').value = dates.to;

    syncScopeUi();
    resetResultsUi();

    document.querySelectorAll('.panel-tab').forEach(tab => {
      tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
    });

    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.preset = btn.dataset.preset;
        const d = presetToDates(btn.dataset.preset);
        state.dateFrom = d.from;
        state.dateTo = d.to;
        document.getElementById('date-from').value = d.from;
        document.getElementById('date-to').value = d.to;
        autoLoadData();
      });
    });

    document.getElementById('date-from').addEventListener('change', e => {
      state.dateFrom = e.target.value;
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      state.preset = null;
      autoLoadData();
    });

    document.getElementById('date-to').addEventListener('change', e => {
      state.dateTo = e.target.value;
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      state.preset = null;
      autoLoadData();
    });

    resetBtn?.addEventListener('click', () => {
      resetApp();
      toast('MIDAS reset', 'info');
    });

    checkHealth();
    setInterval(checkHealth, 30000);
  }

  return {
    state,
    toast,
    api,
    presetToDates,
    today,
    switchPanel,
    init,
    getScopeInfo,
    setSingleTickerScope,
    setBatchScope,
    setSp500Scope,
    clearScope,
    resetApp,
    resetResultsUi,
    showChartView,
    showScanView,
    syncScopeUi,
  };
})();

document.addEventListener('DOMContentLoaded', () => MIDAS.init());
