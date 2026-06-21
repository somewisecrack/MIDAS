/**
 * data_loader.js — Ticker search, date range, data fetch, and CSV upload.
 */

document.addEventListener('DOMContentLoaded', () => {
  const tickerInput   = document.getElementById('ticker-input');
  const loadBtn       = document.getElementById('load-btn');
  const csvUploadBtn  = document.getElementById('csv-upload-btn');
  const csvFileInput  = document.getElementById('csv-file-input');
  const placeholder   = document.getElementById('chart-placeholder');

  // ── Fetch and render data ─────────────────────────────────────────────────
  async function loadData(ticker, dateFrom, dateTo, preset) {
    if (!ticker) {
      MIDAS.toast('Enter a ticker symbol first', 'warn');
      return;
    }

    loadBtn.disabled = true;
    loadBtn.textContent = 'Loading…';
    placeholder.style.display = 'none';

    try {
      // 1. Fetch & cache
      const fetchRes = await MIDAS.api('POST', '/data/fetch', {
        ticker,
        date_from: dateFrom,
        date_to:   dateTo,
        preset:    preset || null,
        force:     false,
      });

      // 2. Load from cache
      const dataRes = await MIDAS.api('GET', `/data/${ticker}?date_from=${dateFrom}&date_to=${dateTo}`);

      if (!dataRes.data || dataRes.data.length === 0) {
        MIDAS.toast(`No data returned for ${ticker.toUpperCase()}`, 'error');
        placeholder.style.display = 'flex';
        return;
      }

      // 3. Update state
      MIDAS.state.ticker   = ticker.toUpperCase();
      MIDAS.state.dateFrom = dateFrom;
      MIDAS.state.dateTo   = dateTo;
      MIDAS.state.ohlcvData = dataRes.data;

      // 4. Render chart
      MIDASChart.clearMarkers();
      MIDASChart.clearHighlights();
      MIDASChart.loadCandles(dataRes.data);

      // 5. Update run button and UI
      updateRunBtn();
      resetBacktestPanel();

      const source = fetchRes.cached ? 'cache' : 'Yahoo Finance';
      MIDAS.toast(
        `${ticker.toUpperCase()} — ${dataRes.rows} bars loaded from ${source}`,
        'success',
      );

    } catch (err) {
      MIDAS.toast(err.message || 'Failed to load data', 'error');
      placeholder.style.display = 'flex';
      console.error('Load error:', err);
    } finally {
      loadBtn.disabled = false;
      loadBtn.textContent = 'Load Data';
    }
  }

  // ── Load button ───────────────────────────────────────────────────────────
  loadBtn.addEventListener('click', () => {
    if (MIDAS.state.batchTickers && MIDAS.state.batchTickers.length > 0) {
      return; // Handled by app.js listener which shows the info toast
    }
    const ticker = tickerInput.value.trim().toUpperCase();
    loadData(ticker, MIDAS.state.dateFrom, MIDAS.state.dateTo, MIDAS.state.preset);
  });

  // Enter key on ticker input
  tickerInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') loadBtn.click();
  });

  // Auto-uppercase ticker
  tickerInput.addEventListener('input', e => {
    e.target.value = e.target.value.toUpperCase();
  });

  // ── CSV Upload ────────────────────────────────────────────────────────────
  csvUploadBtn.addEventListener('click', () => csvFileInput.click());

  csvFileInput.addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;

    const ticker = tickerInput.value.trim().toUpperCase();
    const fd = new FormData();
    fd.append('file', file);
    if (ticker) fd.append('ticker', ticker);

    csvUploadBtn.textContent = 'Uploading…';
    csvUploadBtn.disabled = true;

    try {
      const res = await MIDAS.api('POST', '/data/upload', fd, true);
      const uploadedTicker = res.ticker;

      // Now load it into chart
      tickerInput.value = uploadedTicker;
      MIDAS.state.ticker = uploadedTicker;

      const dataRes = await MIDAS.api('GET', `/data/${uploadedTicker}?date_from=1990-01-01&date_to=${MIDAS.today()}`);
      if (dataRes.data && dataRes.data.length > 0) {
        MIDAS.state.ohlcvData = dataRes.data;
        MIDAS.state.dateFrom = dataRes.data[0].date;
        MIDAS.state.dateTo   = dataRes.data[dataRes.data.length - 1].date;
        document.getElementById('date-from').value = MIDAS.state.dateFrom;
        document.getElementById('date-to').value   = MIDAS.state.dateTo;
        MIDASChart.loadCandles(dataRes.data);
        resetBacktestPanel();
        updateRunBtn();
      }

      MIDAS.toast(`CSV uploaded: ${uploadedTicker} — ${res.rows_imported} rows`, 'success');
    } catch (err) {
      MIDAS.toast(`CSV upload failed: ${err.message}`, 'error');
    } finally {
      csvUploadBtn.textContent = '📁 CSV';
      csvUploadBtn.disabled = false;
      csvFileInput.value = '';
    }
  });

  // ── Helper: reset backtest panel to empty state ───────────────────────────
  function resetBacktestPanel() {
    document.getElementById('backtest-empty').classList.remove('hidden');
    document.getElementById('backtest-results').classList.add('hidden');
    document.getElementById('backtest-running').classList.add('hidden');
    document.getElementById('interpretation-box').classList.remove('visible');
    MIDAS.state.lastBacktestResult = null;
    MIDAS.state.lastRunId = null;
  }

  // ── Helper: enable/disable Run Backtest button ────────────────────────────
  function updateRunBtn() {
    const btn = document.getElementById('run-backtest-btn');
    const hasData = MIDAS.state.ohlcvData.length > 0;
    const hasBatch = MIDAS.state.batchTickers && MIDAS.state.batchTickers.length > 0;
    const hasStrategies = MIDAS.state.selectedStrategies.size > 0;
    btn.disabled = !((hasData || hasBatch) && hasStrategies);
  }

  // Expose so backtest.js can call it on selection change
  window.updateRunBtn = updateRunBtn;
});
