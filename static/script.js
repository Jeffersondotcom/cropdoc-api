// Initialize Lucide Icons
lucide.createIcons();

// ===== STATE =====
let allChats = JSON.parse(localStorage.getItem('cropdoc_chats') || '[]');
let activeChatId = null;
let isLoading = false;

// ===== DOM ELEMENTS =====
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const sidebarChats = document.getElementById('sidebar-chats');
const hamburgerBtn = document.getElementById('hamburger-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const messagesArea = document.getElementById('messages-area');
const welcomeScreen = document.getElementById('welcome-screen');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const cameraInput = document.getElementById('camera-input');
const galleryInput = document.getElementById('gallery-input');
const cameraBtn = document.getElementById('camera-btn');
const galleryBtn = document.getElementById('gallery-btn');
const topbarTitle = document.getElementById('topbar-title');
const downloadChatBtn = document.getElementById('download-chat-btn');

// ===== SIDEBAR TOGGLE =====
hamburgerBtn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
});

sidebarOverlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
});

// ===== CHAT MANAGEMENT =====
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function saveChats() {
    localStorage.setItem('cropdoc_chats', JSON.stringify(allChats));
}

function createNewChat() {
    const chat = {
        id: generateId(),
        title: 'New Conversation',
        messages: [],
        createdAt: new Date().toISOString()
    };
    allChats.unshift(chat);
    saveChats();
    switchToChat(chat.id);
    renderSidebar();
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
}

function switchToChat(chatId) {
    activeChatId = chatId;
    renderSidebar();
    renderMessages();
    const chat = allChats.find(c => c.id === chatId);
    topbarTitle.textContent = chat ? chat.title : 'New Conversation';
}

function deleteChat(chatId, event) {
    event.stopPropagation();
    allChats = allChats.filter(c => c.id !== chatId);
    saveChats();
    if (activeChatId === chatId) {
        if (allChats.length > 0) {
            switchToChat(allChats[0].id);
        } else {
            activeChatId = null;
            renderMessages();
            topbarTitle.textContent = 'New Conversation';
        }
    }
    renderSidebar();
}

function getActiveChat() {
    return allChats.find(c => c.id === activeChatId) || null;
}

function ensureActiveChat() {
    if (!activeChatId) {
        createNewChat();
    }
    return getActiveChat();
}

function updateChatTitle(chat) {
    if (chat.title === 'New Conversation' && chat.messages.length > 0) {
        const firstUserMsg = chat.messages.find(m => m.role === 'user');
        if (firstUserMsg) {
            chat.title = firstUserMsg.content.substring(0, 40) + (firstUserMsg.content.length > 40 ? '...' : '');
        }
        const firstDiagnosis = chat.messages.find(m => m.diagnosisData);
        if (firstDiagnosis) {
            chat.title = '🌿 ' + firstDiagnosis.diagnosisData.disease;
        }
        saveChats();
        renderSidebar();
        topbarTitle.textContent = chat.title;
    }
}

// ===== RENDER SIDEBAR =====
function renderSidebar() {
    sidebarChats.innerHTML = '';
    if (allChats.length === 0) {
        sidebarChats.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 2rem 1rem;">No conversations yet</p>';
        return;
    }
    allChats.forEach(chat => {
        const el = document.createElement('div');
        el.className = 'chat-item' + (chat.id === activeChatId ? ' active' : '');
        el.innerHTML = `
            <span class="chat-item-title">${escapeHtml(chat.title)}</span>
            <button class="chat-item-delete" title="Delete chat"><i data-lucide="trash-2"></i></button>
        `;
        el.addEventListener('click', () => {
            switchToChat(chat.id);
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
        });
        el.querySelector('.chat-item-delete').addEventListener('click', (e) => deleteChat(chat.id, e));
        sidebarChats.appendChild(el);
    });
    lucide.createIcons();
}

// ===== RENDER MESSAGES =====
function renderMessages() {
    // Remove all message rows but keep welcome screen
    const existingMessages = messagesArea.querySelectorAll('.message-row, .typing-row');
    existingMessages.forEach(el => el.remove());

    const chat = getActiveChat();

    if (!chat || chat.messages.length === 0) {
        welcomeScreen.style.display = 'flex';
        return;
    }

    welcomeScreen.style.display = 'none';

    chat.messages.forEach(msg => {
        const row = document.createElement('div');
        row.className = `message-row ${msg.role === 'user' ? 'user' : 'ai'}`;

        if (msg.role === 'ai') {
            row.innerHTML = `
                <div class="message-avatar ai-avatar"><i data-lucide="leaf"></i></div>
                <div class="message-content">${formatAIMessage(msg)}</div>
            `;
        } else {
            row.innerHTML = `
                <div class="message-content"><p>${escapeHtml(msg.content)}</p></div>
                <div class="message-avatar user-avatar">You</div>
            `;
        }

        messagesArea.appendChild(row);
    });

    lucide.createIcons();
    scrollToBottom();

    // Animate confidence bars
    setTimeout(() => {
        document.querySelectorAll('.conf-fill[data-width]').forEach(bar => {
            bar.style.width = bar.dataset.width + '%';
        });
    }, 100);
}

function formatAIMessage(msg) {
    let html = '';

    if (msg.diagnosisData) {
        const d = msg.diagnosisData;
        const sevClass = d.severity;
        html += `
            <div class="diagnosis-card">
                <div class="diagnosis-header">
                    <h3>${escapeHtml(d.disease)}</h3>
                    <span class="severity-badge ${sevClass}">${d.severity}</span>
                </div>
                <div class="confidence-row">
                    <div class="conf-bar"><div class="conf-fill" data-width="${d.confidence}"></div></div>
                    <span class="conf-value">${d.confidence}%</span>
                </div>
                <div class="treatment-box">
                    <h4><i data-lucide="shield-check"></i> Treatment</h4>
                    <p>${escapeHtml(d.treatment)}</p>
                </div>
            </div>
        `;
    }

    if (msg.content) {
        html += `<p>${escapeHtml(msg.content)}</p>`;
    }

    return html;
}

function showTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row ai typing-row';
    row.innerHTML = `
        <div class="message-avatar ai-avatar"><i data-lucide="leaf"></i></div>
        <div class="message-content">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    messagesArea.appendChild(row);
    lucide.createIcons();
    scrollToBottom();
}

function removeTypingIndicator() {
    const typingRow = messagesArea.querySelector('.typing-row');
    if (typingRow) typingRow.remove();
}

function scrollToBottom() {
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== SEND TEXT MESSAGE =====
async function sendTextMessage(text) {
    if (!text.trim() || isLoading) return;

    const chat = ensureActiveChat();
    chat.messages.push({ role: 'user', content: text });
    updateChatTitle(chat);
    saveChats();
    renderMessages();

    messageInput.value = '';
    sendBtn.disabled = true;
    isLoading = true;

    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                history: chat.messages.map(m => ({ role: m.role, content: m.content }))
            })
        });

        removeTypingIndicator();

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Server error');
        }

        const data = await response.json();
        chat.messages.push({ role: 'ai', content: data.reply });
        saveChats();
        renderMessages();
    } catch (error) {
        removeTypingIndicator();
        chat.messages.push({ role: 'ai', content: 'Sorry, I encountered an error: ' + error.message });
        saveChats();
        renderMessages();
    } finally {
        isLoading = false;
    }
}

// ===== SEND IMAGE FOR DIAGNOSIS =====
async function sendImageForDiagnosis(file) {
    if (isLoading) return;

    const chat = ensureActiveChat();
    chat.messages.push({ role: 'user', content: '📷 Sent a photo for diagnosis' });
    updateChatTitle(chat);
    saveChats();
    renderMessages();

    isLoading = true;
    showTypingIndicator();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        removeTypingIndicator();

        if (!response.ok) throw new Error('Prediction failed');

        const data = await response.json();

        const isHealthy = data.disease.includes('Healthy');
        let summaryText = isHealthy
            ? `Great news! Your ${data.disease.split(' - ')[0]} crop looks healthy. No treatment is needed.`
            : `I've detected ${data.disease} with ${data.confidence}% confidence. Here's the diagnosis and recommended treatment:`;

        chat.messages.push({
            role: 'ai',
            content: summaryText,
            diagnosisData: data
        });

        // Auto-update title to the disease name
        if (chat.title === 'New Conversation' || chat.title.startsWith('📷')) {
            chat.title = '🌿 ' + data.disease;
            topbarTitle.textContent = chat.title;
        }

        saveChats();
        renderSidebar();
        renderMessages();
    } catch (error) {
        removeTypingIndicator();
        chat.messages.push({ role: 'ai', content: 'Sorry, I could not process the image. Please try again.' });
        saveChats();
        renderMessages();
    } finally {
        isLoading = false;
    }
}

// ===== SUGGESTION CHIPS =====
function sendSuggestion(text) {
    sendTextMessage(text);
}

// ===== DOWNLOAD CHAT =====
function downloadChat() {
    const chat = getActiveChat();
    if (!chat || chat.messages.length === 0) return;

    let content = `CropDoc AI — Chat Export\nTitle: ${chat.title}\nDate: ${new Date().toLocaleString()}\n${'─'.repeat(50)}\n\n`;

    chat.messages.forEach(msg => {
        const label = msg.role === 'ai' ? 'CropDoc AI' : 'You';
        content += `[${label}]\n${msg.content}\n`;
        if (msg.diagnosisData) {
            const d = msg.diagnosisData;
            content += `  Disease: ${d.disease}\n  Confidence: ${d.confidence}%\n  Severity: ${d.severity}\n  Treatment: ${d.treatment}\n`;
        }
        content += '\n';
    });

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CropDoc_${chat.title.replace(/[^a-zA-Z0-9]/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ===== EVENT LISTENERS =====
newChatBtn.addEventListener('click', createNewChat);
downloadChatBtn.addEventListener('click', downloadChat);

messageInput.addEventListener('input', () => {
    sendBtn.disabled = !messageInput.value.trim();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage(messageInput.value);
    }
});

sendBtn.addEventListener('click', () => {
    sendTextMessage(messageInput.value);
});

cameraBtn.addEventListener('click', () => cameraInput.click());
galleryBtn.addEventListener('click', () => galleryInput.click());

cameraInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        sendImageForDiagnosis(e.target.files[0]);
        e.target.value = '';
    }
});

galleryInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        sendImageForDiagnosis(e.target.files[0]);
        e.target.value = '';
    }
});

// ===== INIT =====
function init() {
    renderSidebar();
    if (allChats.length > 0) {
        switchToChat(allChats[0].id);
    } else {
        topbarTitle.textContent = 'New Conversation';
    }
}

init();
