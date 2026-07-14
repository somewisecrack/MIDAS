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
  const tradeTableWrap  = document.getElementById('trade-table-wrap');
  const batchSection    = document.getElementById('batch-ticker-section');
  const tradeHeaderRow  = tradeCountBadge.parentElement.parentElement;

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
    // We keep the run button enabled so click handlers can display helpful toasts.
    runBtn.disabled = false;
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

  // ── Run Button Logic ────────────────────────────────────────────────────────
  runBtn.addEventListener('click', async () => {
    if (MIDAS.state.selectedStrategies.size === 0) {
      MIDAS.toast('Select at least one strategy', 'warn');
      return;
    }

    const isScanMode = document.getElementById('run-mode-switch').checked;

    if (isScanMode) {
      if (!MIDAS.state.sp500Mode && MIDAS.state.batchTickers.length === 0) {
        MIDAS.toast('Scan mode requires S&P 500 or Batch mode active', 'warn');
        return;
      }
      runScan();
    } else {
      if (!MIDAS.state.batchTickers.length && !MIDAS.state.ohlcvData.length && !MIDAS.state.sp500Mode) {
        MIDAS.toast('Load ticker data first, or enable Batch/SP500 Mode', 'warn');
        return;
      }
      runBacktest();
    }
  });

  async function runScan() {
    const strategyIds = [...MIDAS.state.selectedStrategies];
    backtestEmpty.classList.add('hidden');
    backtestResults.classList.add('hidden');
    backtestRunning.classList.remove('hidden');
    if (window.MIDASChart) {
      MIDASChart.clearMarkers();
      MIDASChart.clearHighlights();
    }
    interpretBox.classList.remove('visible');

    document.getElementById('backtest-running-msg').textContent =
      `Scanning ${MIDAS.getScopeInfo().runLabel || 'selected universe'}... (This may take 1-2 minutes)`;

    MIDAS.switchPanel('backtest');

    try {
      const payload = {
        strategy_ids: strategyIds,
        date_from:    MIDAS.state.dateFrom,
        date_to:      MIDAS.state.dateTo,
      };
      if (MIDAS.state.sp500Mode) {
        payload.sp500 = true;
      } else {
        payload.tickers = MIDAS.state.batchTickers;
      }

      const res = await MIDAS.api('POST', '/backtest/scan', payload);

      MIDAS.state.lastScanResult = res;
      MIDAS.state.lastRunId = null;

      backtestRunning.classList.add('hidden');
      MIDAS.showScanView?.();

      const tbody = document.getElementById('scan-tbody');
      if (!res.results || res.results.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center">No active setups found for next session.</td></tr>`;
        document.getElementById('scan-count-badge').textContent = '0 setups';
      } else {
        document.getElementById('scan-count-badge').textContent = `${res.results.length} setup${res.results.length>1?'s':''}`;
        tbody.innerHTML = res.results.map(r => `
          <tr>
            <td style="color:var(--gold); font-weight:600">${r.ticker}</td>
            <td>${r.strategy}</td>
            <td class="${r.direction === 'LONG' ? 'direction-long' : 'direction-short'}">${r.direction}</td>
            <td>${r.close_price.toFixed(2)}</td>
            <td>${r.entry_price.toFixed(2)}</td>
            <td>${r.stop_loss.toFixed(2)}</td>
          </tr>
        `).join('');
      }

      renderScanSummary(res);
      MIDAS.toast(`Scan complete — ${res.results?.length || 0} setup${(res.results?.length || 0) === 1 ? '' : 's'} found`, 'success');

    } catch (e) {
      backtestRunning.classList.add('hidden');
      MIDAS.toast(`Scan Error: ${e.message}`, 'error');
    }
  }

  async function requestGemmaInterpretation(mode, triggerBtn, outputBox) {
    if (!MIDAS.state.ollamaOnline) {
      MIDAS.toast('Gemma is offline — start Ollama first', 'warn');
      return;
    }

    if (mode === 'backtest' && !MIDAS.state.lastRunId) return;
    if (mode === 'scan' && !MIDAS.state.lastScanResult) return;

    triggerBtn.disabled = true;
    triggerBtn.innerHTML = '<div class="gemma-spinner" style="width:14px;height:14px;border-width:2px;border-color:var(--gemma-dim);border-top-color:var(--gemma)"></div> Analysing…';

    try {
      let res;
      if (mode === 'scan') {
        const scan = MIDAS.state.lastScanResult;
        res = await MIDAS.api('POST', '/gemma/interpret-scan', {
          scope: interpretBtn.dataset.scope || 'Scan',
          date_from: scan.date_from,
          date_to: scan.date_to,
          results: scan.results || [],
        });
      } else {
        res = await MIDAS.api('POST', '/gemma/interpret', { run_id: MIDAS.state.lastRunId });
      }
      outputBox.textContent = res.interpretation || 'No interpretation returned.';
      outputBox.classList.add('visible');
    } catch (e) {
      MIDAS.toast(`Gemma error: ${e.message}`, 'error');
    } finally {
      triggerBtn.disabled = false;
      triggerBtn.innerHTML = mode === 'scan'
        ? '<span>🔮</span> Interpret Scan with Gemma'
        : '<span>🔮</span> Ask Gemma to interpret results';
    }
  }

  function renderScanSummary(res) {
    const results = res.results || [];
    const longCount = results.filter(r => r.direction === 'LONG').length;
    const shortCount = results.filter(r => r.direction === 'SHORT').length;
    const strategyCount = new Set(results.map(r => r.strategy)).size;
    const tickerCount = new Set(results.map(r => r.ticker)).size;
    const scope = MIDAS.state.sp500Mode
      ? 'S&P 500 scan'
      : `Batch scan (${MIDAS.state.batchTickers.length} tickers)`;

    backtestStats.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Scope</div>
        <div class="stat-value gold" style="font-size:14px">${MIDAS.state.sp500Mode ? 'S&P 500' : 'Batch'}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Setups</div>
        <div class="stat-value gold">${results.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tickers</div>
        <div class="stat-value">${tickerCount}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Strategies</div>
        <div class="stat-value">${strategyCount}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Long</div>
        <div class="stat-value positive">${longCount}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Short</div>
        <div class="stat-value ${shortCount > 0 ? 'negative' : ''}">${shortCount}</div>
      </div>
    `;

    batchSection.classList.add('hidden');
    tradeHeaderRow.classList.add('hidden');
    tradeTableWrap.classList.add('hidden');
    interpretBtn.disabled = false;
    interpretBtn.dataset.mode = 'scan';
    interpretBtn.dataset.scope = scope;
    interpretBtn.innerHTML = '<span>🔮</span> Interpret scan with Gemma';
    backtestResults.classList.remove('hidden');
    MIDAS.switchPanel('backtest');
  }

  function resetBacktestPanelForBacktest() {
    tradeHeaderRow.classList.remove('hidden');
    tradeTableWrap.classList.remove('hidden');
    interpretBtn.dataset.mode = 'backtest';
    delete interpretBtn.dataset.scope;
    interpretBtn.innerHTML = '<span>🔮</span> Ask Gemma to interpret results';
  }

  async function runBacktest() {
    // Show running state
    backtestEmpty.classList.add('hidden');
    backtestResults.classList.add('hidden');
    backtestRunning.classList.remove('hidden');
    if (window.MIDASChart) {
      MIDASChart.clearMarkers();
      MIDASChart.clearHighlights();
    }
    interpretBox.classList.remove('visible');

    const strategyIds = [...MIDAS.state.selectedStrategies];
    
    if (MIDAS.state.sp500Mode) {
      document.getElementById('backtest-running-msg').textContent =
        `Running S&P 500 backtest... (This may take 15-30 seconds to fetch data)`;
    } else if (MIDAS.state.batchTickers.length > 0) {
      document.getElementById('backtest-running-msg').textContent =
        `Running batch backtest on ${MIDAS.state.batchTickers.length} tickers... (This may take a moment to fetch data)`;
    } else {
      document.getElementById('backtest-running-msg').textContent =
        `Running ${strategyIds.length} strateg${strategyIds.length > 1 ? 'ies' : 'y'} on ${MIDAS.getScopeInfo().runLabel || MIDAS.state.ticker}…`;
    }

    MIDAS.switchPanel('backtest');

    try {
      const payload = {
        strategy_ids: strategyIds,
        date_from:    MIDAS.state.dateFrom,
        date_to:      MIDAS.state.dateTo,
      };
      if (MIDAS.state.sp500Mode) {
        payload.sp500 = true;
      } else if (MIDAS.state.batchTickers.length > 0) {
        payload.tickers = MIDAS.state.batchTickers;
      } else {
        payload.ticker = MIDAS.state.ticker;
      }
      
      const res = await MIDAS.api('POST', '/backtest/run', payload);

      MIDAS.state.lastBacktestResult = res;
      MIDAS.state.lastScanResult = null;
      MIDAS.state.lastRunId = res.run_id;

      backtestRunning.classList.add('hidden');
      MIDAS.showChartView?.();

      if ((!res.trades || res.trades.length === 0) && !res.portfolio_strategy) {
        backtestEmpty.classList.remove('hidden');
        backtestEmpty.querySelector('.empty-text').textContent =
          'No signals fired for this strategy/ticker/range combination.';
        MIDAS.toast('No trades generated — try a wider date range or different strategies', 'warn');
        return;
      }

      renderResults(res);
      if (!res.portfolio_strategy) {
        MIDASChart.addTradeMarkers(res.trades);
      }
      if (res.equity_curve && res.equity_curve.length > 1) {
        MIDASChart.showEquityCurve(res.equity_curve);
      }

      // Auto-save notice
      const completeMsg = res.portfolio_strategy
        ? `Portfolio backtest complete — Return on capital: ${(res.stats.profit_on_contributions || res.stats.total_return || 0).toFixed(2)}%`
        : `Backtest complete — ${res.trades.length} trades | Win rate: ${(res.stats.win_rate || 0).toFixed(2)}%`;
      MIDAS.toast(completeMsg, 'success');

      // Refresh history panel
      if (window.MIDASHistory) MIDASHistory.reload();

    } catch (err) {
      backtestRunning.classList.add('hidden');
      backtestEmpty.classList.remove('hidden');
      MIDAS.toast(`Backtest failed: ${err.message}`, 'error');
    }
  }

  // ── Render results ────────────────────────────────────────────────────────
  function renderResults(res) {
    const s = res.stats;

    resetBacktestPanelForBacktest();

    if (res.portfolio_strategy) {
      const ret = s.profit_on_contributions ?? s.total_return ?? 0;
      const retColor = ret >= 0 ? 'positive' : 'negative';
      backtestStats.innerHTML = `
        <div class="stat-card">
          <div class="stat-label">Portfolio Periods</div>
          <div class="stat-value gold">${s.total_trades || 0}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Ending Value</div>
          <div class="stat-value gold">$${(s.ending_value || 0).toFixed(2)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Contributed</div>
          <div class="stat-value">$${(s.total_contributed || 0).toFixed(2)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Profit</div>
          <div class="stat-value ${s.profit >= 0 ? 'positive' : 'negative'}">${s.profit >= 0 ? '+' : ''}$${(s.profit || 0).toFixed(2)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Return on Capital</div>
          <div class="stat-value ${retColor}">${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Max Drawdown</div>
          <div class="stat-value negative">${(s.max_drawdown || 0).toFixed(2)}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Period Return</div>
          <div class="stat-value ${s.avg_return >= 0 ? 'positive' : 'negative'}">${s.avg_return >= 0 ? '+' : ''}${(s.avg_return || 0).toFixed(2)}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Sharpe</div>
          <div class="stat-value">${(s.sharpe || 0).toFixed(2)}</div>
        </div>
      `;
      tradeCountBadge.textContent = `(${res.trades?.length || 0} legs)`;
      renderTradeTable(res.trades || []);
      batchSection.classList.add('hidden');
      backtestResults.classList.remove('hidden');
      interpretBtn.disabled = false;
      return;
    }

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
        <div class="stat-value ${wrColor}">${(s.win_rate || 0).toFixed(2)}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Profit Factor</div>
        <div class="stat-value ${pfColor}">${s.profit_factor === 999 ? '∞' : (s.profit_factor || 0).toFixed(2)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Return</div>
        <div class="stat-value ${retColor}">${s.total_return >= 0 ? '+' : ''}${(s.total_return || 0).toFixed(2)}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Return</div>
        <div class="stat-value ${s.avg_return >= 0 ? 'positive' : 'negative'}">${s.avg_return >= 0 ? '+' : ''}${(s.avg_return || 0).toFixed(2)}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Max Drawdown</div>
        <div class="stat-value negative">${(s.max_drawdown || 0).toFixed(2)}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Sharpe</div>
        <div class="stat-value">${(s.sharpe || 0).toFixed(2)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Win / Loss</div>
        <div class="stat-value" style="font-size:12px">
          <span class="return-positive">+${(s.avg_win || 0).toFixed(2)}%</span>
          <span class="text-muted"> / </span>
          <span class="return-negative">${(s.avg_loss || 0).toFixed(2)}%</span>
        </div>
      </div>
    `;

    // Trade table
    tradeCountBadge.textContent = `(${res.trades.length})`;
    renderTradeTable(res.trades);

    // Batch Ticker List
    const batchList = document.getElementById('batch-ticker-list');
    
    if (res.ticker_results && res.ticker_results.length > 0) {
      batchSection.classList.remove('hidden');
      batchList.innerHTML = res.ticker_results.map((tr, idx) => `
        <label style="display:flex;align-items:center;padding:4px;gap:8px;cursor:pointer;border-bottom:1px solid var(--border)">
          <input type="radio" name="batch-ticker" value="${tr.ticker}" ${idx===0 ? 'checked' : ''}>
          <span style="font-weight:bold">${tr.ticker}</span>
          <span style="color:var(--text-muted);font-size:11px;margin-left:auto">${tr.trades.length} trades | Ret: <span class="${tr.stats.total_return >= 0 ? 'return-positive' : 'return-negative'}">${(tr.stats.total_return || 0).toFixed(2)}%</span></span>
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
      const mfe = t.mfe ? `+${t.mfe.toFixed(2)}%` : '—';
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

  // ── Gemma interpret ───────────────────────────────────────────────────────
  interpretBtn.addEventListener('click', async () => {
    const mode = interpretBtn.dataset.mode === 'scan' ? 'scan' : 'backtest';
    await requestGemmaInterpretation(mode, interpretBtn, interpretBox);
  });

  window.addEventListener('midas:reset', () => {
    strategySearch.value = '';
    activeFilter = 'ALL';
    filterChips.forEach(chip => {
      chip.classList.toggle('active', chip.dataset.filter === 'ALL');
    });
    tradeTbody.innerHTML = '';
    tradeCountBadge.textContent = '';
    backtestStats.innerHTML = '';
    document.getElementById('batch-ticker-list').innerHTML = '';
    batchSection.classList.add('hidden');
    resetBacktestPanelForBacktest();
    renderStrategyList();
  });

  // ── Boot ──────────────────────────────────────────────────────────────────
  await loadStrategies();
});
