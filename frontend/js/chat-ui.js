// js/chat-ui.js
let currentConversationId = null;
let currentMessages = [];

document.addEventListener('DOMContentLoaded', async () => {
    await loadHistory();
    setupEventListeners();
});

// ===== HISTORY =====

async function loadHistory() {
    try {
        const history = await getHistoryList();
        renderHistory(history);
        if (history.length > 0) {
            await loadConversation(history[0].id);
        } else {
            currentConversationId = null;
            currentMessages = [];
            renderMessages();
        }
    } catch (err) {
        console.error(err);
    }
}

function renderHistory(history) {
    const container = document.getElementById('historyList');
    if (!container) return;
    container.innerHTML = '';
    if (history.length === 0) {
        container.innerHTML = '<div style="color:var(--sidebar-muted);font-size:0.82rem;padding:12px 8px;text-align:center;">Chưa có cuộc trò chuyện nào</div>';
        return;
    }
    history.forEach(conv => {
        const div = document.createElement('div');
        div.className = 'history-item';
        if (currentConversationId === conv.id) div.classList.add('active');

        const body = document.createElement('div');
        body.className = 'history-item-body';
        body.innerHTML = `
            <div class="history-item-title">${escapeHtml(conv.title)}</div>
            <div class="history-item-meta">${formatDate(conv.created_at)} · ${conv.message_count} tin nhắn</div>
        `;

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-history';
        delBtn.setAttribute('data-id', conv.id);
        delBtn.title = 'Xóa cuộc trò chuyện';
        delBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>`;

        div.appendChild(body);
        div.appendChild(delBtn);

        div.addEventListener('click', (e) => {
            if (e.target.closest('.delete-history')) return;
            loadConversation(conv.id);
        });
        delBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm('Xóa cuộc trò chuyện này?')) {
                await deleteConversation(conv.id);
                await loadHistory();
                if (currentConversationId === conv.id) {
                    currentConversationId = null;
                    currentMessages = [];
                    renderMessages();
                }
            }
        });
        container.appendChild(div);
    });
}

async function loadConversation(convId) {
    try {
        const detail = await getConversationDetail(convId);
        currentConversationId = detail.id;
        currentMessages = detail.messages || [];
        renderMessages();
        document.querySelectorAll('.history-item').forEach(el => {
            const btn = el.querySelector('.delete-history');
            const id = btn ? btn.getAttribute('data-id') : null;
            if (id == convId) el.classList.add('active');
            else el.classList.remove('active');
        });
    } catch (err) {
        console.error(err);
    }
}

// ===== RENDER MESSAGES =====

function renderMessages() {
    const container = document.getElementById('messagesContainer');
    if (!container) return;

    const emptyEl = document.getElementById('emptyChat');

    if (currentMessages.length === 0) {
        container.innerHTML = '';
        if (emptyEl) { container.appendChild(emptyEl); emptyEl.style.display = 'flex'; }
        else {
            container.innerHTML = `
                <div class="empty-chat" id="emptyChat">
                    <div class="empty-chat-icon">🎓</div>
                    <div class="empty-chat-title">Tư vấn Quy chế HUST</div>
                    <div class="empty-chat-sub">Hãy đặt câu hỏi về quy chế đào tạo, chuẩn đầu ra, điều kiện tốt nghiệp, học phí, học bổng...</div>
                </div>`;
        }
        return;
    }

    if (emptyEl) emptyEl.style.display = 'none';
    container.innerHTML = '';

    currentMessages.forEach(msg => {
        container.appendChild(createMessageRow(msg));
    });
    container.scrollTop = container.scrollHeight;
}

function createMessageRow(msg) {
    const row = document.createElement('div');
    row.className = `message-row ${msg.role}`;
    if (msg._isTyping) row.id = 'typingRow';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = msg.role === 'user' ? '👤' : '🎓';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const content = document.createElement('div');
    content.className = 'message-content';

    if (msg._isTyping) {
        content.innerHTML = `<div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>`;
    } else {
        if (msg.role === 'user') {
            content.innerHTML = escapeHtml(msg.content).replace(/\n/g, '<br>');
        } else {
            content.innerHTML = renderMarkdown(msg.content);
        }
    }

    bubble.appendChild(content);

    if (msg.sources && msg.sources.length > 0 && !msg._isTyping) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        msg.sources.forEach(s => {
            const tag = document.createElement('span');
            tag.className = 'source-tag';
            tag.innerHTML = `📚 ${escapeHtml(s.van_ban || '')} · ${escapeHtml(s.dieu || '')}`;
            sourcesDiv.appendChild(tag);
        });
        bubble.appendChild(sourcesDiv);
    }

    if (msg.created_at && !msg._isTyping) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = formatTime(msg.created_at);
        bubble.appendChild(timeDiv);
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    return row;
}

// ===== MARKDOWN RENDERER =====

function renderMarkdown(text) {
    if (!text) return '';
    let html = text;

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_full, _lang, code) => {
        return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
    });
    html = html.replace(/`([^`\n]+)`/g, (_, code) => `<code>${escapeHtml(code)}</code>`);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_\n]+)_/g, '<em>$1</em>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`);
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    const parts = html.split(/\n\n+/);
    html = parts.map(part => {
        if (part.match(/^<(h[123]|ul|ol|pre|blockquote)/)) return part;
        const inner = part.replace(/\n/g, '<br>');
        return `<p>${inner}</p>`;
    }).join('');

    return html;
}

// ===== EVENT LISTENERS =====

function setupEventListeners() {
    const sendBtn = document.getElementById('sendBtn');
    const input = document.getElementById('messageInput');
    const newChatBtn = document.getElementById('newChatBtn');
    const toggleSidebar = document.getElementById('toggleSidebar');

    sendBtn.addEventListener('click', sendMessageHandler);

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessageHandler();
        }
    });

    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 180) + 'px';
    });

    newChatBtn.addEventListener('click', () => {
        currentConversationId = null;
        currentMessages = [];
        renderMessages();
        document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
        input.focus();
    });

    toggleSidebar.addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('collapsed');
    });
}

// ===== SEND MESSAGE (Streaming) =====

async function sendMessageHandler() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const question = input.value.trim();
    if (!question) return;

    input.disabled = true;
    sendBtn.disabled = true;
    input.value = '';
    input.style.height = 'auto';

    const emptyEl = document.getElementById('emptyChat');
    if (emptyEl) emptyEl.style.display = 'none';

    const container = document.getElementById('messagesContainer');

    const userMsg = {
        id: 'tmp-' + Date.now(),
        role: 'user',
        content: question,
        sources: null,
        created_at: new Date().toISOString()
    };
    currentMessages.push(userMsg);
    container.appendChild(createMessageRow(userMsg));
    container.scrollTop = container.scrollHeight;

    const typingRow = createMessageRow({ role: 'assistant', content: '', _isTyping: true });
    typingRow.id = 'typingRow';
    container.appendChild(typingRow);
    container.scrollTop = container.scrollHeight;

    try {
        let fullAnswer = '';
        let sources = [];
        let msgId = null;
        let contentEl = null;

        const stream = sendMessageStream(question, currentConversationId);

        for await (const chunk of stream) {
            if (chunk.status === 'generating') {
                const typingEl = document.getElementById('typingRow');
                if (typingEl) {
                    typingEl.innerHTML = '';
                    const avatar = document.createElement('div');
                    avatar.className = 'message-avatar';
                    avatar.textContent = '🎓';
                    const bubble = document.createElement('div');
                    bubble.className = 'message-bubble';
                    contentEl = document.createElement('div');
                    contentEl.className = 'message-content';
                    bubble.appendChild(contentEl);
                    typingEl.appendChild(avatar);
                    typingEl.appendChild(bubble);
                }
            } else if (chunk.token) {
                fullAnswer += chunk.token;
                if (contentEl) {
                    contentEl.innerHTML = renderMarkdown(fullAnswer);
                    container.scrollTop = container.scrollHeight;
                }
            } else if (chunk.done) {
                sources = chunk.sources || [];
                if (!currentConversationId) currentConversationId = chunk.conversation_id;
                msgId = chunk.message_id;
            }
        }

        document.getElementById('typingRow')?.remove();

        const assistantMsg = {
            id: msgId,
            role: 'assistant',
            content: fullAnswer,
            sources: sources,
            created_at: new Date().toISOString()
        };
        currentMessages.push(assistantMsg);
        container.appendChild(createMessageRow(assistantMsg));
        container.scrollTop = container.scrollHeight;

        await loadHistory();

    } catch (err) {
        document.getElementById('typingRow')?.remove();
        const errMsg = {
            id: Date.now(),
            role: 'assistant',
            content: `Lỗi: ${err.message || 'Không thể gửi tin nhắn. Vui lòng thử lại.'}`,
            sources: null,
            created_at: new Date().toISOString()
        };
        currentMessages.push(errMsg);
        container.appendChild(createMessageRow(errMsg));
        container.scrollTop = container.scrollHeight;
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

// ===== UTILS =====

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}
