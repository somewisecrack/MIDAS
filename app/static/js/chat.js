/**
 * chat.js — Multi-modal chat interface with Gemma using SSE streaming.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatPanel      = document.getElementById('chat-panel');
  const chatMessages   = document.getElementById('chat-messages');
  const chatInput      = document.getElementById('chat-input');
  const sendBtn        = document.getElementById('chat-send-btn');
  const attachBtn      = document.getElementById('chat-attach-btn');
  const imageInput     = document.getElementById('chat-image-input');
  const imageStrip     = document.getElementById('chat-image-strip');
  const imageThumb     = document.getElementById('chat-image-thumb');
  const imageRemove    = document.getElementById('chat-image-remove');
  const offlineMsg     = document.getElementById('chat-offline-msg');
  const contextPill    = document.getElementById('chat-context-pill');
  const contextLabel   = document.getElementById('chat-context-label');
  const contextClear   = document.getElementById('chat-context-clear');
  const modelSelect    = document.getElementById('model-select');
  const quickPrompts   = document.querySelectorAll('.quick-prompt');

  let messageHistory = [];
  let currentImageB64 = null;
  let isStreaming = false;
  let useContext = true;

  // ── Load Models ───────────────────────────────────────────────────────────
  async function loadModels() {
    try {
      const res = await MIDAS.api('GET', '/gemma/models');
      if (res.available && res.models.length > 0) {
        modelSelect.innerHTML = res.models.map(m => `<option value="${m}">${m}</option>`).join('');
      } else {
        modelSelect.innerHTML = `<option value="">No models found</option>`;
      }
    } catch (e) {
      modelSelect.innerHTML = `<option value="">Offline</option>`;
    }
  }

  // ── Auto-resize textarea ──────────────────────────────────────────────────
  chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    sendBtn.disabled = !this.value.trim() && !currentImageB64;
  });

  // ── Handle Tab / Context updates ──────────────────────────────────────────
  document.querySelector('[data-panel="chat"]').addEventListener('click', () => {
    const offline = !MIDAS.state.ollamaOnline;
    offlineMsg.classList.toggle('hidden', !offline);
    chatInput.disabled = offline;
    sendBtn.disabled = offline || (!chatInput.value.trim() && !currentImageB64);

    if (MIDAS.state.ticker && useContext) {
      contextPill.classList.remove('hidden');
      contextLabel.textContent = `${MIDAS.state.ticker} (${MIDAS.state.dateFrom} to ${MIDAS.state.dateTo})`;
    } else {
      contextPill.classList.add('hidden');
    }

    if (modelSelect.options.length <= 1 && MIDAS.state.ollamaOnline) {
      loadModels();
    }
  });

  contextClear.addEventListener('click', () => {
    useContext = false;
    contextPill.classList.add('hidden');
  });

  // ── Image Attachment ──────────────────────────────────────────────────────
  attachBtn.addEventListener('click', () => imageInput.click());

  imageInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      MIDAS.toast('Image too large (max 10MB)', 'warn');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      // Extract base64 part (remove data:image/png;base64, prefix)
      const dataUrl = event.target.result;
      const base64 = dataUrl.split(',')[1];
      currentImageB64 = base64;
      imageThumb.src = dataUrl;
      imageStrip.classList.remove('hidden');
      sendBtn.disabled = false;
      setTimeout(() => chatInput.focus(), 50);
    };
    reader.readAsDataURL(file);
    imageInput.value = '';
  });

  imageRemove.addEventListener('click', () => {
    currentImageB64 = null;
    imageThumb.src = '';
    imageStrip.classList.add('hidden');
    sendBtn.disabled = !chatInput.value.trim();
  });

  // ── Quick Prompts ─────────────────────────────────────────────────────────
  quickPrompts.forEach(btn => {
    btn.addEventListener('click', () => {
      chatInput.value = btn.dataset.prompt;
      chatInput.style.height = 'auto';
      chatInput.style.height = chatInput.scrollHeight + 'px';
      sendBtn.disabled = false;
      chatInput.focus();
    });
  });

  // ── Markdown Parser (Basic) ───────────────────────────────────────────────
  function parseMD(text) {
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') // escape HTML
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');

    // Code blocks
    html = html.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');

    // Paragraphs
    html = html.split('\\n\\n').map(p => `<p>${p.replace(/\\n/g, '<br>')}</p>`).join('');
    return html;
  }

  // ── Render Message ────────────────────────────────────────────────────────
  function addMessage(role, content, imageB64 = null) {
    const msgEl = document.createElement('div');
    msgEl.className = `chat-msg ${role}`;

    let imgHtml = '';
    if (imageB64) {
      imgHtml = `<img src="data:image/png;base64,${imageB64}" class="msg-img-preview" alt="User attachment">`;
    }

    const contentHtml = parseMD(content);

    msgEl.innerHTML = `
      ${imgHtml}
      <div class="content">${contentHtml}</div>
    `;

    chatMessages.appendChild(msgEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgEl;
  }

  // ── Send Message (SSE) ────────────────────────────────────────────────────
  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text && !currentImageB64) return;
    if (isStreaming) return;

    // 1. Add user message
    messageHistory.push({
      role: 'user',
      content: text,
      image_b64: currentImageB64
    });

    addMessage('user', text, currentImageB64);

    // 2. Prepare payload
    // If context enabled, we invisibly inject it into the latest user prompt
    const payloadMessages = [...messageHistory];
    if (useContext && MIDAS.state.ticker && MIDAS.state.ohlcvData.length) {
      const last = payloadMessages[payloadMessages.length - 1];
      const data = MIDAS.state.ohlcvData.slice(-100); // Send last 100 days max
      const dataStr = data.map(r => `${r.date},${r.open},${r.high},${r.low},${r.close},${r.volume}`).join('\\n');
      const systemContext = `\\n\\n[System Context: The user is currently looking at ${MIDAS.state.ticker} from ${MIDAS.state.dateFrom} to ${MIDAS.state.dateTo}. Here are the last 100 daily bars for context:\\ndate,open,high,low,close,volume\\n${dataStr}]`;
      last.content += systemContext;
    }

    // 3. Reset input
    chatInput.value = '';
    chatInput.style.height = '34px';
    sendBtn.disabled = true;
    imageRemove.click(); // clear attachments
    isStreaming = true;

    // 4. Create empty assistant message with cursor
    const assistantMsgEl = document.createElement('div');
    assistantMsgEl.className = 'chat-msg assistant';
    assistantMsgEl.innerHTML = `<div class="content"><span class="streaming-cursor"></span></div>`;
    chatMessages.appendChild(assistantMsgEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const contentNode = assistantMsgEl.querySelector('.content');

    // 5. Connect to SSE
    try {
      const response = await fetch('/api/gemma/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: payloadMessages,
          model: modelSelect.value || null,
          stream: true
        })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\\n\\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') {
              isStreaming = false;
              break;
            }

            try {
              const data = JSON.parse(dataStr);
              if (data.error) throw new Error(data.error);

              fullResponse += data.token;
              contentNode.innerHTML = parseMD(fullResponse) + '<span class="streaming-cursor"></span>';
              chatMessages.scrollTop = chatMessages.scrollHeight;
            } catch (e) {
              console.warn('SSE parse error:', e);
            }
          }
        }
      }

      // 6. Finalize
      contentNode.innerHTML = parseMD(fullResponse);
      messageHistory.push({ role: 'assistant', content: fullResponse });

    } catch (err) {
      contentNode.innerHTML = `<span style="color:var(--short)">Error: ${err.message}</span>`;
    } finally {
      isStreaming = false;
      sendBtn.disabled = !chatInput.value.trim();
      chatInput.focus();
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  loadModels();
});
