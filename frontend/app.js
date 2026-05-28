let currentUser = null;
let currentChatId = null;
let chats = [];
let currentMode = null;
let streamingMessageEl = null;
let currentEventSource = null;
let isStreaming = false;

const API_BASE = '';


document.addEventListener('DOMContentLoaded', () => {
    autoResizeTextarea();
    skipLogin();
});


function skipLogin() {
    document.getElementById('loginModal').classList.add('hidden');
    document.getElementById('appContainer').classList.remove('hidden');
    
    const guestUser = { username: '访客用户', id: 'guest' };
    initApp(guestUser);
}

function initApp(user) {
    currentUser = user;
    const initials = '访';
    document.getElementById('userInfo').textContent = '访客用户';
    document.getElementById('userAvatar').textContent = initials;
    document.getElementById('headerUserAvatar').textContent = initials;
    
    loadChats();
    createNewChat();
}

function logout() {
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
    currentChatId = null;
    chats = [];
    location.reload();
}

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active', 'bg-gray-100'));
    const btn = document.getElementById('btn-' + mode);
    if (btn) btn.classList.add('active', 'bg-gray-100');
}


async function loadChats() {
    try {
        const response = await fetch(`${API_BASE}/api/conversations`);
        if (response.ok) {
            chats = await response.json();
            renderHistoryList();
        }
    } catch (err) {
        console.error('加载对话列表失败:', err);
    }
}

function renderHistoryList() {
    const container = document.getElementById('historyList');
    if (!container) return;
    
    if (chats.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 text-xs py-4">暂无历史对话</div>';
        return;
    }
    
    container.innerHTML = '';
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = `history-item px-3 py-2 rounded-lg cursor-pointer flex items-center justify-between group ${chat.id === currentChatId ? 'active' : ''}`;
        
        const titleDiv = document.createElement('div');
        titleDiv.className = 'flex-1 truncate text-sm';
        titleDiv.textContent = chat.title;
        titleDiv.onclick = () => selectChat(chat.id);
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity';
        
        const renameBtn = document.createElement('button');
        renameBtn.className = 'p-1 hover:bg-gray-200 rounded';
        renameBtn.title = '重命名';
        renameBtn.innerHTML = '<span class="material-symbols-outlined text-xs">edit</span>';
        renameBtn.onclick = (e) => {
            e.stopPropagation();
            renameChat(chat.id);
        };
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'p-1 hover:bg-red-100 rounded';
        deleteBtn.title = '删除';
        deleteBtn.innerHTML = '<span class="material-symbols-outlined text-xs">delete</span>';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        };
        
        actionsDiv.appendChild(renameBtn);
        actionsDiv.appendChild(deleteBtn);
        
        item.appendChild(titleDiv);
        item.appendChild(actionsDiv);
        container.appendChild(item);
    });
}

async function createNewChat() {
    const newChat = {
        id: 'chat_' + Date.now(),
        title: '新对话',
        created_at: new Date().toISOString()
    };
    
    currentChatId = newChat.id;
    chats = [newChat];
    
    const welcomeMsg = document.getElementById('welcomeMessage');
    const messagesContainer = document.getElementById('messagesContainer');
    const inputBar = document.getElementById('inputBar');
    
    if (welcomeMsg) welcomeMsg.classList.remove('hidden');
    if (messagesContainer) messagesContainer.classList.add('hidden');
    if (inputBar) inputBar.classList.add('hidden');
}

async function selectChat(chatId) {
    try {
        const response = await fetch(`${API_BASE}/api/conversations/${chatId}`);
        if (response.ok) {
            const data = await response.json();
            currentChatId = chatId;
            
            const welcomeMsg = document.getElementById('welcomeMessage');
            const messagesContainer = document.getElementById('messagesContainer');
            const inputBar = document.getElementById('inputBar');
            
            if (welcomeMsg) welcomeMsg.classList.add('hidden');
            if (messagesContainer) messagesContainer.classList.remove('hidden');
            if (inputBar) inputBar.classList.remove('hidden');
            
            const msgArea = messagesContainer.querySelector('.space-y-6');
            if (msgArea) {
                msgArea.innerHTML = '';
                data.messages.forEach(msg => {
                    appendHistoryMessage(msg);
                });
            }
            
            renderHistoryList();
        }
    } catch (err) {
        console.error('加载对话失败:', err);
    }
}

async function deleteChat(chatId) {
    if (!confirm('确定要删除这个对话吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/conversations/${chatId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (currentChatId === chatId) {
                createNewChat();
            }
            await loadChats();
        }
    } catch (err) {
        console.error('删除对话失败:', err);
    }
}

async function renameChat(chatId) {
    const newTitle = prompt('请输入新的对话标题:');
    if (!newTitle || !newTitle.trim()) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/conversations/${chatId}?title=${encodeURIComponent(newTitle)}`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            await loadChats();
        }
    } catch (err) {
        console.error('重命名对话失败:', err);
    }
}

function appendHistoryMessage(message) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    
    const msgArea = messagesContainer.querySelector('.space-y-6');
    if (!msgArea) return;
    
    const isUser = message.role === 'user';
    const avatar = isUser ? '访' : 'AI';
    const bgColor = isUser ? 'from-blue-400 to-blue-600' : 'from-purple-400 to-purple-600';
    const contentBg = isUser ? 'bg-gray-50' : 'bg-white border border-gray-200';
    const contentClass = isUser ? '' : 'prose prose-sm max-w-none';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'flex gap-3 mb-4';
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-gradient-to-br ${bgColor} flex items-center justify-center text-white text-xs font-bold flex-shrink-0">${avatar}</div>
        <div class="flex-1 ${contentBg} rounded-lg p-3 text-sm ${contentClass}">${isUser ? escapeHtml(message.content) : marked.parse(message.content)}</div>
    `;
    
    msgArea.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


async function sendMessage() {
    const input = document.getElementById('messageInput');
    const inputChat = document.getElementById('messageInputChat');
    const activeInput = input && input.offsetParent !== null ? input : inputChat;
    
    if (!activeInput) return;
    
    const content = activeInput.value.trim();
    if (!content) return;

    activeInput.value = '';
    activeInput.style.height = 'auto';

    const welcomeMsg = document.getElementById('welcomeMessage');
    const messagesContainer = document.getElementById('messagesContainer');
    const inputBar = document.getElementById('inputBar');
    
    if (welcomeMsg) welcomeMsg.classList.add('hidden');
    if (messagesContainer) {
        messagesContainer.classList.remove('hidden');
        const msgArea = messagesContainer.querySelector('.space-y-6');
        if (msgArea && !currentChatId) msgArea.innerHTML = '';
    }
    if (inputBar) inputBar.classList.remove('hidden');

    appendUserMessage(content);

    try {
        await connectToBackend(content);
    } catch (err) {
        console.error('发送消息失败:', err);
        showErrorMessage(err.message);
    }
}

async function connectToBackend(message) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    
    const msgArea = messagesContainer.querySelector('.space-y-6');
    if (!msgArea) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'flex gap-3 mb-4';
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">AI</div>
        <div class="flex-1 bg-white rounded-lg p-3 text-sm border border-gray-200">
            <div class="message-text prose prose-sm max-w-none"></div>
        </div>
    `;
    
    msgArea.appendChild(msgDiv);
    const messageEl = msgDiv.querySelector('.message-text');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    let accumulatedText = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: currentChatId
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'session_id') {
                            currentChatId = data.session_id;
                        } else if (data.type === 'content') {
                            accumulatedText += data.content;
                            messageEl.innerHTML = marked.parse(accumulatedText);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (data.type === 'image') {
                            // 显示图片
                            const imgDiv = document.createElement('div');
                            imgDiv.className = 'mt-3 rounded-lg overflow-hidden border border-gray-200';
                            imgDiv.innerHTML = `<img src="data:${data.mime_type};base64,${data.data}" alt="${data.filename}" class="max-w-full h-auto">`;
                            msgDiv.querySelector('.flex-1').appendChild(imgDiv);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (data.type === 'file') {
                            // 显示文件下载链接
                            const fileDiv = document.createElement('div');
                            fileDiv.className = 'mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200 flex items-center gap-3';
                            fileDiv.innerHTML = `
                                <span class="material-symbols-outlined text-blue-500">description</span>
                                <div class="flex-1">
                                    <div class="text-sm font-medium text-gray-800">${escapeHtml(data.filename)}</div>
                                    <div class="text-xs text-gray-500">${formatFileSize(data.size)}</div>
                                </div>
                                <a href="${data.download_url}" download class="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600">下载</a>
                            `;
                            msgDiv.querySelector('.flex-1').appendChild(fileDiv);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (data.type === 'data') {
                            // 显示结构化数据
                            const dataDiv = document.createElement('div');
                            dataDiv.className = 'mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200';
                            dataDiv.innerHTML = `<pre class="text-xs text-gray-700 overflow-x-auto">${JSON.stringify(data.data, null, 2)}</pre>`;
                            msgDiv.querySelector('.flex-1').appendChild(dataDiv);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (data.type === 'error') {
                            accumulatedText += '\n\n❌ 错误: ' + data.error;
                            messageEl.innerHTML = marked.parse(accumulatedText);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        } else if (data.type === 'done') {
                            isStreaming = false;
                        }
                    } catch (e) {
                        console.error('解析消息失败:', e);
                    }
                }
            }
        }
    } catch (err) {
        messageEl.textContent = '❌ 连接失败: ' + err.message + '\n\n请检查：\n1. 后端服务是否启动\n2. API Key 是否已配置（访问设置页面配置）';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        throw err;
    }
}

function showErrorMessage(message) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    
    const msgArea = messagesContainer.querySelector('.space-y-6');
    if (!msgArea) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'flex gap-3 mb-4';
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-red-400 to-red-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">!</div>
        <div class="flex-1 bg-red-50 rounded-lg p-3 text-sm border border-red-200">
            <p class="text-red-700">${escapeHtml(message)}</p>
        </div>
    `;
    msgArea.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendUserMessage(content) {
    const welcomeMsg = document.getElementById('welcomeMessage');
    const messagesContainer = document.getElementById('messagesContainer');
    const inputBar = document.getElementById('inputBar');
    
    if (welcomeMsg) welcomeMsg.classList.add('hidden');
    if (messagesContainer) messagesContainer.classList.remove('hidden');
    if (inputBar) inputBar.classList.remove('hidden');
    
    const msgArea = messagesContainer.querySelector('.space-y-6');
    if (!msgArea) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex gap-3 mb-4';
    messageDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">访</div>
        <div class="flex-1 bg-gray-50 rounded-lg p-3 text-sm">${escapeHtml(content)}</div>
    `;
    msgArea.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendMessage(message) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    
    const msgArea = messagesContainer.querySelector('.space-y-6');
    if (!msgArea) return;
    
    const isUser = message.role === 'user';
    const avatar = isUser ? '访' : 'AI';
    const bgColor = isUser ? 'from-blue-400 to-blue-600' : 'from-purple-400 to-purple-600';
    const contentBg = isUser ? 'bg-gray-50' : 'bg-white border border-gray-200';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'flex gap-3 mb-4';
    msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-gradient-to-br ${bgColor} flex items-center justify-center text-white text-xs font-bold flex-shrink-0">${avatar}</div>
        <div class="flex-1 ${contentBg} rounded-lg p-3 text-sm">${escapeHtml(message.content)}</div>
    `;
    
    msgArea.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}


function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    const textarea = document.getElementById('messageInput');
    const textareaChat = document.getElementById('messageInputChat');
    
    [textarea, textareaChat].forEach(el => {
        if (!el) return;
        
        el.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    });
}


function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
