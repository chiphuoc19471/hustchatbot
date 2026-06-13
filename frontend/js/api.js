// js/api.js
async function request(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(`${CONFIG.BASE_URL}${endpoint}`, options);
    const data = await response.json();
    if (!response.ok) {
        const err = new Error(data.detail || 'Lỗi kết nối');
        err.status = response.status;
        err.data = data;
        throw err;
    }
    return data;
}

async function sendMessage(question, conversationId = null) {
    const body = { question };
    if (conversationId) body.conversation_id = conversationId;
    return request('/chat', 'POST', body);
}

async function* sendMessageStream(question, conversationId = null) {
    const body = { question };
    if (conversationId) body.conversation_id = conversationId;

    const response = await fetch(`${CONFIG.BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error('Lỗi kết nối server');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try { yield JSON.parse(line.slice(6)); } catch (_) {}
            }
        }
    }
}

async function getHistoryList() {
    return request('/history', 'GET');
}

async function getConversationDetail(convId) {
    return request(`/history/${convId}`, 'GET');
}

async function deleteConversation(convId) {
    return request(`/history/${convId}`, 'DELETE');
}
