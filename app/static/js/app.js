/**
 * app.js — Global state, utilities, and router for MIDAS SPA.
 * Loaded first. All other modules attach to window.MIDAS.
 */

window.MIDAS = (() => {
  // ── Global state ──────────────────────────────────────────────────────────
  const state = {
    ticker: '',
    dateFrom: null,
    dateTo: null,
    batchTickers: [],
    preset: '3Y',
    ohlcvData: [],           // array of { date, open, high, low, close, volume }
    strategies: [],          // full list from /api/strategies
    selectedStrategies: new Set(),
    lastBacktestResult: null,
    lastRunId: null,
    ollamaOnline: false,
    activePanel: 'backtest', // 'backtest' | 'gemma' | 'history'
    indicators: {
      sma10: false,
      sma20: true,
      sma50: false,
      volume: true,
    },
  };

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
      opts.body = body; // FormData — browser sets content-type automatically
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

  // ── Batch Modal ───────────────────────────────────────────────────────────
  const batchBtn = document.getElementById('batch-mode-btn');
  const batchModal = document.getElementById('batch-modal');
  const batchInput = document.getElementById('batch-ticker-input');
  
  batchBtn?.addEventListener('click', () => {
    batchInput.value = state.batchTickers.join(', ');
    batchModal.classList.remove('hidden');
  });
  
  document.getElementById('batch-cancel-btn')?.addEventListener('click', () => {
    batchModal.classList.add('hidden');
  });
  
  document.getElementById('batch-apply-btn')?.addEventListener('click', () => {
    const text = batchInput.value;
    const tickers = text.split(/[\n,]+/).map(t => t.trim().toUpperCase()).filter(t => t);
    
    if (tickers.length === 0) {
      toast('No tickers provided. Batch mode disabled.', 'warn');
      state.batchTickers = [];
      document.getElementById('ticker-input').disabled = false;
      batchBtn.classList.remove('active');
    } else {
      if (tickers.length > 100) {
        toast(`Truncating ${tickers.length} tickers to 100 maximum.`, 'warn');
        tickers.splice(100);
      }
      state.batchTickers = tickers;
      state.ticker = 'BATCH'; // Visual indicator
      document.getElementById('ticker-input').value = `BATCH (${tickers.length})`;
      document.getElementById('ticker-input').disabled = true;
      batchBtn.classList.add('active');
      toast(`Batch mode enabled: ${tickers.length} tickers`, 'success');
    }
    batchModal.classList.add('hidden');
    if (window.updateRunBtn) window.updateRunBtn();
  });

  // ── Load Data Button ──────────────────────────────────────────────────────
  document.getElementById('load-btn').addEventListener('click', async () => {
    if (state.batchTickers.length > 0) {
      toast(`Batch mode active. Click "Run Backtest" directly to begin.`, 'info');
      // For batch mode, we don't load chart data until a ticker is selected from results
      return;
    }
    
    let t = document.getElementById('ticker-input').value.trim().toUpperCase();
    if (!t) {
      toast('Enter a ticker symbol', 'warn');
      return;
    }
    state.ticker = t;

    try {
      const btn = document.getElementById('load-btn');
      btn.disabled = true;
      btn.textContent = 'Loading...';

      const res = await api('POST', '/data/fetch', {
        ticker: state.ticker,
        date_from: state.dateFrom,
        date_to: state.dateTo,
        preset: state.preset,
      });

      // Load data to chart
      const rowsRes = await api('GET', `/data/${state.ticker}?date_from=${state.dateFrom || ''}&date_to=${state.dateTo || ''}&preset=${state.preset || ''}`);
      state.ohlcvData = rowsRes.data || [];
      MIDASChart.loadCandles(state.ohlcvData);
      toast(`Loaded ${rowsRes.rows || state.ohlcvData.length} bars for ${state.ticker}`, 'success');
      
      // Clear old results
      document.getElementById('backtest-empty')?.classList.remove('hidden');
      document.getElementById('backtest-results')?.classList.add('hidden');
      
    } catch (e) {
      toast(`Error loading data: ${e.message}`, 'error');
    } finally {
      const btn = document.getElementById('load-btn');
      btn.disabled = false;
      btn.textContent = 'Load Data';
      if (window.updateRunBtn) window.updateRunBtn();
    }
  });

  // ── Date utilities ────────────────────────────────────────────────────────
  function today() {
    return new Date().toISOString().slice(0, 10);
  }

  function presetToDates(preset) {
    const now = new Date();
    const toStr = d => d.toISOString().slice(0, 10);
    const presets = {
      '1Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 1); return d; },
      '3Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 3); return d; },
      '5Y':  () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 5); return d; },
      '10Y': () => { const d = new Date(now); d.setFullYear(d.getFullYear() - 10); return d; },
      'MAX': () => new Date('1990-01-01'),
    };
    const fn = presets[preset];
    if (!fn) return { from: toStr(presets['1Y']()), to: toStr(now) };
    return { from: toStr(fn()), to: toStr(now) };
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
      // Ollama status
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
      // Cache info
      const cacheLabel = document.getElementById('cache-label');
      cacheLabel.textContent = `${h.cached_tickers || 0} tickers cached`;
    } catch (e) {
      console.warn('Health check failed:', e);
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    // Set default dates from preset
    const dates = presetToDates(state.preset);
    state.dateFrom = dates.from;
    state.dateTo = dates.to;
    document.getElementById('date-from').value = dates.from;
    document.getElementById('date-to').value = dates.to;

    // Panel tab clicks
    document.querySelectorAll('.panel-tab').forEach(tab => {
      tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
    });

    // Preset buttons
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
      });
    });

    // Custom date inputs
    document.getElementById('date-from').addEventListener('change', e => {
      state.dateFrom = e.target.value;
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      state.preset = null;
    });
    document.getElementById('date-to').addEventListener('change', e => {
      state.dateTo = e.target.value;
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      state.preset = null;
    });

    document.getElementById('reset-btn')?.addEventListener('click', () => {
      window.location.reload();
    });

    checkHealth();
    // Re-check health every 30 seconds
    setInterval(checkHealth, 30000);
  }

  return { state, toast, api, presetToDates, today, switchPanel, init };
})();

// Boot
document.addEventListener('DOMContentLoaded', () => MIDAS.init());
