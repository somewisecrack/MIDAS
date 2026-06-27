/**
 * backtest.js — Strategy library sidebar + backtest panel.
 * Loads strategies from API, renders cards, runs backtests, shows results.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const strategyList   = document.getElementById('strategy-list');
  const runBtn         = document.getElementById('run-backtest-btn');
  const strategySearch = document.getElementById('strategy-search');
  const filterChips    = document.querySelectorAll('.filter-chip');

  const backtestEmpty   = document.getElementById('backtest-empty');
  const backtestRunning = document.getElementById('backtest-running');
  const backtestResults = document.getElementById('backtest-results');
  const backtestStats   = document.getElementById('backtest-stats');
  const tradeTbody      = document.getElementById('trade-tbody');
  const tradeCountBadge = document.getElementById('trade-count-badge');
  const interpretBtn    = document.getElementById('interpret-btn');
  const interpretBox    = document.getElementById('interpretation-box');
  const exportCsvBtn    = document.getElementById('export-csv-btn');

  let allStrategies = [];
  let activeFilter  = 'ALL';
  let sortKey       = 'entry_date';
  let sortAsc       = true;

  // ── Load strategies ───────────────────────────────────────────────────────
  async function loadStrategies() {
    try {
      const res = await MIDAS.api('GET', '/strategies');
      allStrategies = res.strategies || [];
      renderStrategyList();
    } catch (e) {
      strategyList.innerHTML = `<div class="empty-state"><div class="empty-text">Failed to load strategies</div></div>`;
    }
  }

  // ── Render strategy cards ─────────────────────────────────────────────────
  function renderStrategyList() {
    const query = strategySearch.value.toLowerCase().trim();

    const filtered = allStrategies.filter(s => {
      const matchSearch = !query || s.name.toLowerCase().includes(query);
      const matchFilter =
        activeFilter === 'ALL' ||
        s.priority === activeFilter ||
        s.direction_hint === activeFilter;
      return matchSearch && matchFilter;
    });

    if (filtered.length === 0) {
      strategyList.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-text">No strategies match</div></div>`;
      return;
    }

    strategyList.innerHTML = filtered.map(s => {
      const selected = MIDAS.state.selectedStrategies.has(s.id);
      const dirClass = s.direction_hint || 'BOTH';
      return `
        <div class="strategy-card${selected ? ' selected' : ''}" data-id="${s.id}">
          <div class="strategy-radio"></div>
          <div class="strategy-info">
            <div class="strategy-name" title="${s.name}">${s.name}</div>
            <div class="strategy-meta">
              <span class="priority-badge ${s.priority}">${s.priority}</span>
              <span class="strategy-dir ${dirClass}">${dirClass}</span>
            </div>
          </div>
          <div class="strategy-winrate">${s.win_rate || '—'}</div>
        </div>
      `;
    }).join('');

    // Attach click handlers
    strategyList.querySelectorAll('.strategy-card').forEach(card => {
      card.addEventListener('click', () => toggleStrategy(card.dataset.id));
    });

    updateSelectionCount();
  }

  // ── Toggle strategy selection ─────────────────────────────────────────────
  function toggleStrategy(id) {
    MIDAS.state.selectedStrategies.clear();
    MIDAS.state.selectedStrategies.add(id);
    renderStrategyList();
    if (window.updateRunBtn) window.updateRunBtn();
  }

  function updateSelectionCount() {
    const n = MIDAS.state.selectedStrategies.size;
    runBtn.disabled = !(n > 0 && MIDAS.state.ohlcvData.length > 0);
  }

  // ── Filters ───────────────────────────────────────────────────────────────
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeFilter = chip.dataset.filter;
      renderStrategyList();
    });
  });

  strategySearch.addEventListener('input', () => renderStrategyList());

  strategySearch.addEventListener('input', () => renderStrategyList());

  // ── Run Backtest ──────────────────────────────────────────────────────────
  runBtn.addEventListener('click', async () => {
    if (MIDAS.state.selectedStrategies.size === 0) {
      MIDAS.toast('Select at least one strategy', 'warn');
      return;
    }
    if (!MIDAS.state.batchTickers.length && !MIDAS.state.ohlcvData.length) {
      MIDAS.toast('Load ticker data first, or enable Batch Mode', 'warn');
      return;
    }

    // Show running state
    backtestEmpty.classList.add('hidden');
    backtestResults.classList.add('hidden');
    backtestRunning.classList.remove('hidden');
    MIDASChart.clearMarkers();
    MIDASChart.clearHighlights();
    interpretBox.classList.remove('visible');

    const strategyIds = [...MIDAS.state.selectedStrategies];
    
    if (MIDAS.state.batchTickers.length > 0) {
      document.getElementById('backtest-running-msg').textContent =
        `Running batch backtest on ${MIDAS.state.batchTickers.length} tickers... (This may take a moment to fetch data)`;
    } else {
      document.getElementById('backtest-running-msg').textContent =
        `Running ${strategyIds.length} strateg${strategyIds.length > 1 ? 'ies' : 'y'} on ${MIDAS.state.ticker}…`;
    }

    MIDAS.switchPanel('backtest');

    try {
      const payload = {
        strategy_ids: strategyIds,
        date_from:    MIDAS.state.dateFrom,
        date_to:      MIDAS.state.dateTo,
      };
      if (MIDAS.state.batchTickers.length > 0) {
        payload.tickers = MIDAS.state.batchTickers;
      } else {
        payload.ticker = MIDAS.state.ticker;
      }
      
      const res = await MIDAS.api('POST', '/backtest/run', payload);

      MIDAS.state.lastBacktestResult = res;
      MIDAS.state.lastRunId = res.run_id;

      backtestRunning.classList.add('hidden');

      if (!res.trades || res.trades.length === 0) {
        backtestEmpty.classList.remove('hidden');
        backtestEmpty.querySelector('.empty-text').textContent =
          'No signals fired for this strategy/ticker/range combination.';
        MIDAS.toast('No trades generated — try a wider date range or different strategies', 'warn');
        return;
      }

      renderResults(res);
      MIDASChart.addTradeMarkers(res.trades);
      if (res.equity_curve && res.equity_curve.length > 1) {
        MIDASChart.showEquityCurve(res.equity_curve);
      }

      // Auto-save notice
      MIDAS.toast(
        `Backtest complete — ${res.trades.length} trades | Win rate: ${res.stats.win_rate}%`,
        'success',
      );

      // Refresh history panel
      if (window.MIDASHistory) MIDASHistory.reload();

    } catch (err) {
      backtestRunning.classList.add('hidden');
      backtestEmpty.classList.remove('hidden');
      MIDAS.toast(`Backtest failed: ${err.message}`, 'error');
    }
  });

  // ── Render results ────────────────────────────────────────────────────────
  function renderResults(res) {
    const s = res.stats;

    // Stats cards
    const pfColor = s.profit_factor >= 1.5 ? 'gold' : s.profit_factor >= 1 ? '' : 'negative';
    const wrColor = s.win_rate >= 55 ? 'positive' : s.win_rate >= 45 ? '' : 'negative';
    const retColor = s.total_return >= 0 ? 'positive' : 'negative';

    backtestStats.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Trades</div>
        <div class="stat-value gold">${s.total_trades}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Win Rate</div>
        <div class="stat-value ${wrColor}">${s.win_rate}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Profit Factor</div>
        <div class="stat-value ${pfColor}">${s.profit_factor === 999 ? '∞' : s.profit_factor}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Return</div>
        <div class="stat-value ${retColor}">${s.total_return >= 0 ? '+' : ''}${s.total_return}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Return</div>
        <div class="stat-value ${s.avg_return >= 0 ? 'positive' : 'negative'}">${s.avg_return >= 0 ? '+' : ''}${s.avg_return}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Max Drawdown</div>
        <div class="stat-value negative">${s.max_drawdown}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Sharpe</div>
        <div class="stat-value">${s.sharpe}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Win / Loss</div>
        <div class="stat-value" style="font-size:12px">
          <span class="return-positive">+${s.avg_win}%</span>
          <span class="text-muted"> / </span>
          <span class="return-negative">${s.avg_loss}%</span>
        </div>
      </div>
    `;

    // Trade table
    tradeCountBadge.textContent = `(${res.trades.length})`;
    renderTradeTable(res.trades);

    // Batch Ticker List
    const batchSection = document.getElementById('batch-ticker-section');
    const batchList = document.getElementById('batch-ticker-list');
    
    if (res.ticker_results && res.ticker_results.length > 0) {
      batchSection.classList.remove('hidden');
      batchList.innerHTML = res.ticker_results.map((tr, idx) => `
        <label style="display:flex;align-items:center;padding:4px;gap:8px;cursor:pointer;border-bottom:1px solid var(--border)">
          <input type="radio" name="batch-ticker" value="${tr.ticker}" ${idx===0 ? 'checked' : ''}>
          <span style="font-weight:bold">${tr.ticker}</span>
          <span style="color:var(--text-muted);font-size:11px;margin-left:auto">${tr.trades.length} trades | Ret: <span class="${tr.stats.total_return >= 0 ? 'return-positive' : 'return-negative'}">${tr.stats.total_return}%</span></span>
        </label>
      `).join('');
      
      // Event listener for picking a ticker
      batchList.querySelectorAll('input[name="batch-ticker"]').forEach(radio => {
        radio.addEventListener('change', async (e) => {
          if (e.target.checked) {
            await loadIndividualTicker(e.target.value, res.ticker_results.find(t => t.ticker === e.target.value));
          }
        });
      });
      
      // Load the first one by default
      const firstRadio = batchList.querySelector('input[name="batch-ticker"]');
      if (firstRadio) {
        firstRadio.dispatchEvent(new Event('change'));
      }
      
    } else {
      batchSection.classList.add('hidden');
    }

    backtestResults.classList.remove('hidden');
    interpretBtn.disabled = false;
  }

  // ── Load Individual Ticker from Batch ─────────────────────────────────────
  async function loadIndividualTicker(ticker, tr) {
    try {
      MIDAS.toast(`Loading chart for ${ticker}...`, 'info');
      const rowsRes = await MIDAS.api('GET', `/data/${ticker}?date_from=${MIDAS.state.dateFrom || ''}&date_to=${MIDAS.state.dateTo || ''}`);
      MIDAS.state.ohlcvData = rowsRes.data || [];
      MIDAS.state.ticker = ticker;
      document.getElementById('ticker-input').value = ticker; // Show visual
      MIDASChart.loadCandles(MIDAS.state.ohlcvData);
      MIDASChart.addTradeMarkers(tr.trades);
      if (tr.equity_curve && tr.equity_curve.length > 1) {
        MIDASChart.showEquityCurve(tr.equity_curve);
      }
    } catch (e) {
      MIDAS.toast(`Failed to load chart for ${ticker}`, 'error');
    }
  }

  // ── Trade table ───────────────────────────────────────────────────────────
  function renderTradeTable(trades) {
    const sorted = [...trades].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });

    tradeTbody.innerHTML = sorted.map(t => {
      const retClass = t.return_pct >= 0 ? 'return-positive' : 'return-negative';
      const dirClass = t.direction === 'LONG' ? 'direction-long' : 'direction-short';
      const ret = `${t.return_pct >= 0 ? '+' : ''}${t.return_pct?.toFixed(2)}%`;
      const mfe = t.mfe ? `+${t.mfe.toFixed(1)}%` : '—';
      // Truncate strategy name
      const strat = t.strategy?.length > 18 ? t.strategy.slice(0, 17) + '…' : t.strategy;
      return `
        <tr data-entry="${t.entry_date}" data-exit="${t.exit_date}">
          <td style="font-weight:bold">${t.ticker || MIDAS.state.ticker}</td>
          <td>${t.entry_date}</td>
          <td>${t.exit_date}</td>
          <td title="${t.strategy}">${strat}</td>
          <td class="${dirClass}">${t.direction}</td>
          <td class="${retClass}">${ret}</td>
          <td>${t.holding_days}d</td>
          <td style="color:var(--long);font-size:10px">${mfe}</td>
        </tr>
      `;
    }).join('');

    // Click row → jump chart to that trade window
    tradeTbody.querySelectorAll('tr').forEach(row => {
      row.addEventListener('click', () => {
        const entry = row.dataset.entry;
        const exit  = row.dataset.exit;
        if (entry && exit) MIDASChart.jumpToWindow(entry, exit);
      });
      row.style.cursor = 'pointer';
    });
  }

  // Sort on header click
  document.querySelectorAll('#trade-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (sortKey === key) {
        sortAsc = !sortAsc;
      } else {
        sortKey = key;
        sortAsc = true;
      }
      if (MIDAS.state.lastBacktestResult?.trades) {
        renderTradeTable(MIDAS.state.lastBacktestResult.trades);
      }
    });
  });

  // ── Export CSV ────────────────────────────────────────────────────────────
  exportCsvBtn.addEventListener('click', () => {
    const trades = MIDAS.state.lastBacktestResult?.trades;
    if (!trades || trades.length === 0) return;

    const headers = ['strategy','direction','entry_date','entry_price','exit_date','exit_price','return_pct','holding_days','mfe','mae'];
    const rows = trades.map(t => headers.map(h => t[h] ?? '').join(','));
    const csv = [headers.join(','), ...rows].join('\n');

    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `midas_${MIDAS.state.ticker}_${MIDAS.state.lastRunId?.slice(0,8)}.csv`;
    a.click();
  });

  // ── Qwen interpret ────────────────────────────────────────────────────────
  interpretBtn.addEventListener('click', async () => {
    if (!MIDAS.state.ollamaOnline) {
      MIDAS.toast('Qwen is offline — start Ollama first', 'warn');
      return;
    }
    if (!MIDAS.state.lastRunId) return;

    interpretBtn.disabled = true;
    interpretBtn.innerHTML = '<div class="gemma-spinner" style="width:14px;height:14px;border-width:2px;border-color:var(--gemma-dim);border-top-color:var(--gemma)"></div> Analysing…';

    try {
      const res = await MIDAS.api('POST', '/gemma/interpret', { run_id: MIDAS.state.lastRunId });
      interpretBox.textContent = res.interpretation || 'No interpretation returned.';
      interpretBox.classList.add('visible');
    } catch (e) {
      MIDAS.toast(`Qwen error: ${e.message}`, 'error');
    } finally {
      interpretBtn.disabled = false;
      interpretBtn.innerHTML = '<span>🔮</span> Ask Qwen to interpret results';
    }
  });

  // ── Boot ──────────────────────────────────────────────────────────────────
  await loadStrategies();
});
