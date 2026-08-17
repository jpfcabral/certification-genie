/**
 * Certification Genie — Telegram Simulator Frontend
 * 
 * Pure thin client. No local state, no questions stored.
 * Every interaction is sent to the backend API via /webhook.
 * The backend is the single source of truth.
 */

const API_BASE = '/api';
const WEBHOOK_SECRET = 'local-dev-secret';
const TELEGRAM_USER_ID = 12345;

let updateCounter = 1;

// ─── API Communication ───────────────────────────────────────────────

async function checkHealth() {
    const statusEl = document.getElementById('api-status');
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            statusEl.textContent = '● Online';
            statusEl.classList.remove('offline');
            return true;
        }
    } catch (e) {}
    statusEl.textContent = '● Offline';
    statusEl.classList.add('offline');
    return false;
}

async function sendToWebhook(payload) {
    try {
        const res = await fetch(`${API_BASE}/webhook`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Bot-Api-Secret-Token': WEBHOOK_SECRET,
            },
            body: JSON.stringify(payload),
        });
        return await res.json();
    } catch (e) {
        return { ok: false, error: e.message };
    }
}

function buildMessagePayload(text) {
    return {
        update_id: updateCounter++,
        message: {
            message_id: updateCounter,
            from: { id: TELEGRAM_USER_ID, is_bot: false, first_name: 'Local User' },
            chat: { id: TELEGRAM_USER_ID, type: 'private' },
            date: Math.floor(Date.now() / 1000),
            text: text,
        },
    };
}

function buildCallbackPayload(callbackData) {
    return {
        update_id: updateCounter++,
        callback_query: {
            id: String(updateCounter),
            from: { id: TELEGRAM_USER_ID, is_bot: false, first_name: 'Local User' },
            message: {
                message_id: updateCounter - 1,
                chat: { id: TELEGRAM_USER_ID, type: 'private' },
            },
            data: callbackData,
        },
    };
}

function buildPollAnswerPayload(pollId, optionIndex) {
    return {
        update_id: updateCounter++,
        poll_answer: {
            poll_id: pollId,
            user: { id: TELEGRAM_USER_ID, is_bot: false, first_name: 'Local User' },
            option_ids: [optionIndex],
        },
    };
}

// ─── Message Display ─────────────────────────────────────────────────

function addMessage(text, type = 'bot') {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerHTML = formatText(text);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function formatText(text) {
    // Basic markdown-like formatting
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>');
}

function addBotResponse(result) {
    if (!result.ok && result.error) {
        addMessage(`⚠️ Erro: ${result.error}`, 'error');
        return;
    }

    if (result.blocked) {
        addMessage(result.response || 'Mensagem bloqueada.', 'bot');
        return;
    }

    // Show the response from the API
    if (result.response) {
        addMessage(result.response, 'bot');
    } else if (result.message) {
        addMessage(result.message, 'bot');
    }

    // If API returned a poll/question
    if (result.poll) {
        addPoll(result.poll);
    }

    // If API returned inline keyboard buttons
    if (result.keyboard) {
        addKeyboard(result.keyboard);
    }

    // If nothing meaningful came back, show a raw status
    if (!result.response && !result.message && !result.poll && !result.keyboard && !result.blocked) {
        addMessage(`<em>[API: ok=${result.ok}, blocked=${result.blocked || false}]</em>`, 'system');
    }
}

function addPoll(poll) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'quiz-poll';

    const optionsHtml = poll.options.map((opt, i) => {
        const letter = String.fromCharCode(65 + i);
        return `<div class="option" data-index="${i}" onclick="answerPoll(this, '${poll.id}', ${i}, ${poll.correct_option_id})">
            <span class="letter">${letter}</span>
            <span>${opt}</span>
        </div>`;
    }).join('');

    div.innerHTML = `
        <div class="question-text">${poll.question}</div>
        <div class="options">${optionsHtml}</div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addKeyboard(keyboard) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot keyboard';

    const buttonsHtml = keyboard.map(row => {
        return row.map(btn => {
            return `<button class="kb-btn" onclick="pressButton('${btn.callback_data}')">${btn.text}</button>`;
        }).join('');
    }).join('<br>');

    div.innerHTML = buttonsHtml;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ─── User Actions ────────────────────────────────────────────────────

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    addMessage(text, 'user');
    showTyping();

    const payload = buildMessagePayload(text);
    const result = await sendToWebhook(payload);

    hideTyping();
    addBotResponse(result);
}

async function sendCommand(command) {
    document.getElementById('user-input').value = '';
    addMessage(command, 'user');
    showTyping();

    const payload = buildMessagePayload(command);
    const result = await sendToWebhook(payload);

    hideTyping();
    addBotResponse(result);
}

async function answerPoll(element, pollId, selectedIndex, correctIndex) {
    const poll = element.closest('.quiz-poll');
    const options = poll.querySelectorAll('.option');

    // Disable all options visually
    options.forEach(opt => {
        opt.classList.add('disabled');
        opt.onclick = null;
    });

    // Mark correct/incorrect locally for immediate feedback
    options[correctIndex].classList.add('correct');
    if (selectedIndex !== correctIndex) {
        options[selectedIndex].classList.add('incorrect');
    }

    // Send poll answer to backend
    const payload = buildPollAnswerPayload(pollId, selectedIndex);
    const result = await sendToWebhook(payload);
    addBotResponse(result);
}

async function pressButton(callbackData) {
    addMessage(`[button: ${callbackData}]`, 'user');
    showTyping();

    const payload = buildCallbackPayload(callbackData);
    const result = await sendToWebhook(payload);

    hideTyping();
    addBotResponse(result);
}

// ─── UI Helpers ──────────────────────────────────────────────────────

function showTyping() {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot typing';
    div.id = 'typing-indicator';
    div.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

function clearChat() {
    document.getElementById('messages').innerHTML = '';
    addMessage('💬 Chat limpo. Envie uma mensagem ou comando.', 'system');
}

// ─── Initialization ──────────────────────────────────────────────────

async function init() {
    const online = await checkHealth();
    setInterval(checkHealth, 10000);

    if (online) {
        addMessage('🧞‍♂️ Conectado à API. Este frontend simula o Telegram — tudo é processado pelo backend.', 'system');
        addMessage('Envie /start para começar ou qualquer mensagem para testar o Guardrail Agent.', 'system');
    } else {
        addMessage('⚠️ API offline. Verifique se o docker compose está rodando.', 'error');
    }
}

init();
