/**
 * gemma.js — Pattern search panel (text + image) using Qwen via Ollama.
 * Handles: mode switching, text input, image drag-drop/upload, search,
 * results rendering, and jumping chart to matched windows.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const offlineMsg    = document.getElementById('gemma-offline-msg');
  const modeTextBtn   = document.getElementById('mode-text-btn');
  const modeImageBtn  = document.getElementById('mode-image-btn');
  const textMode      = document.getElementById('gemma-text-mode');
  const imageMode     = document.getElementById('gemma-image-mode');
  const textInput     = document.getElementById('gemma-text-input');
  const dropzone      = document.getElementById('gemma-dropzone');
  const imagePreview  = document.getElementById('gemma-image-preview');
  const previewImg    = document.getElementById('gemma-preview-img');
  const imageClearBtn = document.getElementById('gemma-image-clear');
  const imageInput    = document.getElementById('gemma-image-input');
  const searchBtn     = document.getElementById('gemma-search-btn');
  const thinkingEl    = document.getElementById('gemma-thinking');
  const resultsEl     = document.getElementById('pattern-results');

  let currentMode  = 'text';   // 'text' | 'image'
  let uploadedFile = null;     // File object for image upload

  // ── Mode toggle ───────────────────────────────────────────────────────────
  modeTextBtn.addEventListener('click', () => setMode('text'));
  modeImageBtn.addEventListener('click', () => setMode('image'));

  function setMode(mode) {
    currentMode = mode;
    modeTextBtn.classList.toggle('active', mode === 'text');
    modeImageBtn.classList.toggle('active', mode === 'image');
    textMode.classList.toggle('hidden', mode !== 'text');
    imageMode.classList.toggle('hidden', mode !== 'image');
    updateSearchBtn();
  }

  // ── Offline check (updated when panel tab opened) ─────────────────────────
  function checkOffline() {
    const offline = !MIDAS.state.ollamaOnline;
    offlineMsg.classList.toggle('visible', offline);
    searchBtn.disabled = offline || !MIDAS.state.ohlcvData.length;
  }

  // Check whenever panel becomes visible
  document.querySelector('[data-panel="gemma"]').addEventListener('click', checkOffline);

  // ── Search button state ───────────────────────────────────────────────────
  function updateSearchBtn() {
    const hasData     = MIDAS.state.ohlcvData.length > 0;
    const hasOnline   = MIDAS.state.ollamaOnline;
    const hasContent  = currentMode === 'text'
      ? textInput.value.trim().length > 10
      : uploadedFile !== null;

    searchBtn.disabled = !(hasData && hasOnline && hasContent);
  }

  textInput.addEventListener('input', updateSearchBtn);

  // ── Image drag-drop ───────────────────────────────────────────────────────
  dropzone.addEventListener('click', () => imageInput.click());

  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) loadImageFile(file);
  });

  imageInput.addEventListener('change', e => {
    if (e.target.files[0]) loadImageFile(e.target.files[0]);
  });

  function loadImageFile(file) {
    if (file.size > 10 * 1024 * 1024) {
      MIDAS.toast('Image too large (max 10 MB)', 'warn');
      return;
    }
    uploadedFile = file;
    const url = URL.createObjectURL(file);
    previewImg.src = url;
    dropzone.classList.add('hidden');
    imagePreview.style.display = 'block';
    updateSearchBtn();
  }

  imageClearBtn.addEventListener('click', () => {
    uploadedFile = null;
    previewImg.src = '';
    imagePreview.style.display = 'none';
    dropzone.classList.remove('hidden');
    imageInput.value = '';
    updateSearchBtn();
  });

  // ── Search ────────────────────────────────────────────────────────────────
  searchBtn.addEventListener('click', async () => {
    if (!MIDAS.state.ohlcvData.length) {
      MIDAS.toast('Load ticker data first', 'warn');
      return;
    }
    if (!MIDAS.state.ollamaOnline) {
      MIDAS.toast('Qwen is offline — start Ollama first', 'warn');
      return;
    }

    const query = textInput.value.trim();
    if (currentMode === 'text' && query.length < 10) {
      MIDAS.toast('Describe the pattern in more detail (at least 10 characters)', 'warn');
      return;
    }
    if (currentMode === 'image' && !uploadedFile) {
      MIDAS.toast('Upload a chart image first', 'warn');
      return;
    }

    // Show thinking
    searchBtn.disabled = true;
    thinkingEl.classList.add('visible');
    resultsEl.innerHTML = '';
    MIDASChart.clearHighlights();

    try {
      let res;

      if (currentMode === 'text') {
        res = await MIDAS.api('POST', '/gemma/pattern/text', {
          ticker:    MIDAS.state.ticker,
          query:     query,
          date_from: MIDAS.state.dateFrom,
          date_to:   MIDAS.state.dateTo,
        });
      } else {
        // Image upload via FormData
        const fd = new FormData();
        fd.append('ticker', MIDAS.state.ticker);
        fd.append('date_from', MIDAS.state.dateFrom);
        fd.append('date_to', MIDAS.state.dateTo);
        fd.append('file', uploadedFile);
        res = await MIDAS.api('POST', '/gemma/pattern/image', fd, true);
      }

      renderResults(res.windows || []);

    } catch (err) {
      MIDAS.toast(`Pattern search failed: ${err.message}`, 'error');
      resultsEl.innerHTML = `<div class="empty-state"><div class="empty-text">Search failed: ${err.message}</div></div>`;
    } finally {
      thinkingEl.classList.remove('visible');
      updateSearchBtn();
    }
  });

  // ── Render pattern results ────────────────────────────────────────────────
  function renderResults(windows) {
    if (!windows || windows.length === 0) {
      resultsEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔍</div>
          <div class="empty-text">No matching patterns found</div>
          <div class="empty-sub">Try rephrasing your description or a different time range</div>
        </div>`;
      return;
    }

    resultsEl.innerHTML = windows.map((w, i) => `
      <div class="pattern-window-card" data-start="${w.start}" data-end="${w.end}">
        <div class="window-dates">📅 ${w.start} → ${w.end}</div>
        <span class="window-confidence">Match ${w.confidence ?? '?'}%</span>
        <div class="window-explanation">${w.explanation || '—'}</div>
      </div>
    `).join('');

    // Click → jump chart
    resultsEl.querySelectorAll('.pattern-window-card').forEach(card => {
      card.addEventListener('click', () => {
        const start = card.dataset.start;
        const end   = card.dataset.end;
        MIDASChart.jumpToWindow(start, end);
        MIDAS.toast(`Jumping to pattern: ${start} → ${end}`, 'info', 2500);
      });
    });

    MIDAS.toast(`Qwen found ${windows.length} matching window${windows.length > 1 ? 's' : ''}`, 'success');
  }

  // Expose for external refresh
  window.MIDASGemma = { checkOffline, updateSearchBtn };
});
