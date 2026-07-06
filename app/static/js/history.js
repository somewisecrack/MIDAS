/**
 * history.js — Saved backtest runs panel.
 * Load, rename, delete, and re-activate past runs.
 */

document.addEventListener('DOMContentLoaded', () => {
  const historyList = document.getElementById('history-list');

  // ── Load runs ─────────────────────────────────────────────────────────────
  async function loadHistory() {
    try {
      const res = await MIDAS.api('GET', '/backtest/runs');
      renderRuns(res.runs || []);
    } catch (e) {
      historyList.innerHTML = `<div class="empty-state"><div class="empty-text">Failed to load history</div></div>`;
    }
  }

  // ── Render run cards ──────────────────────────────────────────────────────
  function renderRuns(runs) {
    if (runs.length === 0) {
      historyList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🕐</div>
          <div class="empty-text">No saved runs yet</div>
          <div class="empty-sub">Backtest results are auto-saved here</div>
        </div>`;
      return;
    }

    historyList.innerHTML = runs.map(r => {
      const s = r.stats || {};
      const strategies = (r.strategy_names || []).slice(0, 3).join(', ');
      const moreCount = (r.strategy_names || []).length - 3;
      const stratDisplay = moreCount > 0 ? `${strategies} +${moreCount} more` : strategies;

      const retVal = s.total_return;
      const retStr = retVal !== undefined
        ? `${retVal >= 0 ? '+' : ''}${retVal.toFixed(2)}%`
        : '—';
      const retClass = retVal !== undefined ? (retVal >= 0 ? 'pos' : 'neg') : '';

      const createdDate = r.created_at?.slice(0, 10) || '—';
      const label = r.label ? `<div style="font-size:10px;color:var(--gold);margin-bottom:2px">✏️ ${r.label}</div>` : '';
      const isActive = r.id === MIDAS.state.lastRunId;

      return `
        <div class="run-card${isActive ? ' active' : ''}" data-id="${r.id}">
          ${label}
          <div class="run-card-header">
            <span class="run-ticker">${r.ticker}</span>
            <span class="run-date">${createdDate}</span>
          </div>
          <div class="run-strategies" title="${r.strategy_names?.join(', ')}">${stratDisplay}</div>
          <div style="font-size:10px;color:var(--text-faint);font-family:var(--font-mono)">${r.date_from} → ${r.date_to}</div>
          <div class="run-stats-row">
            <div class="run-stat">Trades <span>${s.total_trades ?? '—'}</span></div>
            <div class="run-stat">Win <span>${s.win_rate !== undefined ? s.win_rate.toFixed(2) : '—'}%</span></div>
            <div class="run-stat">Return <span class="${retClass}">${retStr}</span></div>
            <div class="run-stat">PF <span>${s.profit_factor ?? '—'}</span></div>
          </div>
          <div class="run-actions">
            <button class="run-action-btn btn-rename" data-id="${r.id}">Rename</button>
            <button class="run-action-btn btn-reload" data-id="${r.id}">Reload</button>
            <button class="run-action-btn danger btn-delete" data-id="${r.id}">Delete</button>
          </div>
        </div>
      `;
    }).join('');

    // ── Button handlers ───────────────────────────────────────────────────────

    historyList.querySelectorAll('.btn-rename').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const newLabel = prompt('Enter a label for this run:');
        if (newLabel === null) return;
        try {
          await MIDAS.api('PATCH', `/backtest/runs/${id}`, { label: newLabel });
          loadHistory();
        } catch (err) {
          MIDAS.toast(`Rename failed: ${err.message}`, 'error');
        }
      });
    });

    historyList.querySelectorAll('.btn-delete').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (!confirm('Delete this run?')) return;
        try {
          await MIDAS.api('DELETE', `/backtest/runs/${id}`);
          if (MIDAS.state.lastRunId === id) MIDAS.state.lastRunId = null;
          loadHistory();
          MIDAS.toast('Run deleted', 'info');
        } catch (err) {
          MIDAS.toast(`Delete failed: ${err.message}`, 'error');
        }
      });
    });

    historyList.querySelectorAll('.btn-reload').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const id = btn.dataset.id;
        await reloadRun(id);
      });
    });

    // Click card body = reload
    historyList.querySelectorAll('.run-card').forEach(card => {
      card.addEventListener('click', async e => {
        if (e.target.classList.contains('run-action-btn')) return;
        await reloadRun(card.dataset.id);
      });
    });
  }

  // ── Reload a past run ─────────────────────────────────────────────────────
  async function reloadRun(runId) {
    try {
      const run = await MIDAS.api('GET', `/backtest/runs/${runId}`);
      MIDAS.state.lastRunId = runId;
      MIDAS.state.lastBacktestResult = run;

      MIDAS.state.dateFrom = run.date_from;
      MIDAS.state.dateTo = run.date_to;
      MIDAS.state.preset = null;
      document.getElementById('date-from').value = run.date_from;
      document.getElementById('date-to').value = run.date_to;
      document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));

      // If ticker data not loaded for this run, auto-fetch
      const needFetch = MIDAS.state.ticker !== run.ticker ||
        !MIDAS.state.ohlcvData.length;

      if (needFetch) {
        MIDAS.toast(`Loading ${run.ticker} data…`, 'info');
        await MIDAS.api('POST', '/data/fetch', {
          ticker:    run.ticker,
          date_from: run.date_from,
          date_to:   run.date_to,
        });
        const dataRes = await MIDAS.api('GET', `/data/${run.ticker}?date_from=${run.date_from}&date_to=${run.date_to}`);
        MIDAS.setSingleTickerScope?.(run.ticker, { clearData: false });
        MIDAS.state.ohlcvData = dataRes.data || [];
        document.getElementById('ticker-input').value = run.ticker;
        MIDASChart.loadCandles(MIDAS.state.ohlcvData);
      }

      MIDAS.setSingleTickerScope?.(run.ticker, { clearData: false });

      // Show backtest results
      MIDAS.switchPanel('backtest');

      // Trigger result render — reuse backtest.js rendering via a custom event
      window.dispatchEvent(new CustomEvent('midas:loadrun', { detail: run }));

      MIDAS.toast(`Loaded run: ${run.ticker} (${run.trades?.length || 0} trades)`, 'success');
      renderRuns(await (await fetch('/api/backtest/runs')).json().then(r => r.runs));

    } catch (err) {
      MIDAS.toast(`Failed to reload run: ${err.message}`, 'error');
    }
  }

  // ── Listen for run loaded from backtest.js ────────────────────────────────
  window.addEventListener('midas:loadrun', e => {
    const run = e.detail;
    if (!run || !run.trades) return;
    // Show markers on chart
    MIDASChart.clearMarkers();
    MIDASChart.addTradeMarkers(run.trades);
    if (run.equity_curve?.length > 1) MIDASChart.showEquityCurve(run.equity_curve);
  });

  // ── Boot ──────────────────────────────────────────────────────────────────
  loadHistory();

  // Tab click → refresh
  document.querySelector('[data-panel="history"]').addEventListener('click', loadHistory);

  // Expose so backtest.js can trigger a refresh after saving
  window.MIDASHistory = { reload: loadHistory };
});
