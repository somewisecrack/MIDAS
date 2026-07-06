/**
 * data_loader.js — Ticker search, date range, data fetch, and CSV upload.
 */

document.addEventListener('DOMContentLoaded', () => {
  const tickerInput   = document.getElementById('ticker-input');
  const csvUploadBtn  = document.getElementById('csv-upload-btn');
  const csvFileInput  = document.getElementById('csv-file-input');
  const placeholder   = document.getElementById('chart-placeholder');

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
      MIDAS.setSingleTickerScope?.(uploadedTicker, { clearData: false });
      MIDAS.resetResultsUi?.();

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
    MIDAS.resetResultsUi?.();
    MIDAS.state.lastBacktestResult = null;
    MIDAS.state.lastRunId = null;
  }

  // ── Helper: enable/disable Run Backtest button ────────────────────────────
  function updateRunBtn() {
    const runBtn = document.getElementById('run-backtest-btn');
    if (!runBtn) return;
    
    // Always enable the run button so that click handlers can
    // provide toast warnings to the user if they miss a step.
    runBtn.disabled = false;
  }

  // Expose so backtest.js can call it on selection change
  window.updateRunBtn = updateRunBtn;
});
