const API_BASE = '';

let allApis = [];
let defaultApiId = null;
let currentEditingApiId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadApis();
});

async function loadApis() {
    try {
        const response = await fetch(`${API_BASE}/api/apis`);
        if (response.ok) {
            const data = await response.json();
            allApis = data.apis || [];
            defaultApiId = data.default_api_id;
            renderApis();
        }
    } catch (err) {
        console.error('加载 API 配置失败:', err);
        showMessage('加载配置失败: ' + err.message, 'error');
    }
}

function renderApis() {
    const container = document.getElementById('apisList');
    const emptyState = document.getElementById('emptyState');
    
    if (allApis.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    container.innerHTML = '';
    
    allApis.forEach(api => {
        const isDefault = api.id === defaultApiId;
        const card = document.createElement('div');
        card.className = `api-card rounded-2xl p-6 shadow-lg ${isDefault ? 'default' : ''}`;
        
        const providerNames = {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic',
            'azure': 'Azure',
            'local': '本地模型'
        };
        
        card.innerHTML = `
            <div class="flex items-start justify-between mb-4">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-2">
                        <h3 class="font-bold text-gray-800 text-lg">${escapeHtml(api.name)}</h3>
                        ${isDefault ? '<span class="badge bg-blue-100 text-blue-700">默认</span>' : ''}
                    </div>
                    <p class="text-sm text-gray-600">${providerNames[api.provider] || api.provider}</p>
                </div>
                <div class="flex gap-2">
                    <button onclick="editApi('${api.id}')" class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-xl">edit</span>
                    </button>
                    <button onclick="deleteApi('${api.id}')" class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-xl">delete</span>
                    </button>
                </div>
            </div>
            <div class="space-y-2 text-sm">
                <div class="flex items-center gap-2 text-gray-600">
                    <span class="material-symbols-outlined text-base">smart_toy</span>
                    <span class="font-mono text-xs">${escapeHtml(api.model)}</span>
                </div>
                ${api.base_url ? `
                <div class="flex items-center gap-2 text-gray-600">
                    <span class="material-symbols-outlined text-base">link</span>
                    <span class="font-mono text-xs truncate">${escapeHtml(api.base_url)}</span>
                </div>
                ` : ''}
                ${api.api_key ? `
                <div class="flex items-center gap-2 text-gray-600">
                    <span class="material-symbols-outlined text-base">key</span>
                    <span class="text-xs">已配置</span>
                </div>
                ` : ''}
            </div>
            ${!isDefault ? `
            <div class="mt-4 pt-4 border-t border-gray-200">
                <button onclick="setDefaultApi('${api.id}')" class="text-sm text-blue-600 hover:text-blue-700 font-medium">
                    设为默认
                </button>
            </div>
            ` : ''}
        `;
        container.appendChild(card);
    });
}

function openAddApiModal() {
    currentEditingApiId = null;
    document.getElementById('modalTitle').textContent = '添加 API 配置';
    document.getElementById('apiForm').reset();
    document.getElementById('apiId').value = '';
    document.getElementById('apiModal').classList.remove('hidden');
}

function closeApiModal() {
    document.getElementById('apiModal').classList.add('hidden');
    currentEditingApiId = null;
}

function editApi(apiId) {
    const api = allApis.find(a => a.id === apiId);
    if (!api) return;
    
    currentEditingApiId = apiId;
    
    document.getElementById('modalTitle').textContent = '编辑 API 配置';
    document.getElementById('apiId').value = api.id;
    document.getElementById('apiName').value = api.name;
    document.getElementById('apiProvider').value = api.provider;
    document.getElementById('apiModel').value = api.model;
    document.getElementById('apiKey').value = '';
    document.getElementById('apiBaseUrl').value = api.base_url || '';
    
    document.getElementById('apiModal').classList.remove('hidden');
}

async function saveApi(event) {
    event.preventDefault();
    
    const apiData = {
        id: document.getElementById('apiId').value || undefined,
        name: document.getElementById('apiName').value.trim(),
        provider: document.getElementById('apiProvider').value,
        model: document.getElementById('apiModel').value.trim(),
        api_key: document.getElementById('apiKey').value.trim(),
        base_url: document.getElementById('apiBaseUrl').value.trim() || null
    };
    
    if (!apiData.name || !apiData.model) {
        alert('请填写所有必填字段');
        return;
    }
    
    try {
        let response;
        if (currentEditingApiId) {
            response = await fetch(`${API_BASE}/api/apis/${currentEditingApiId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(apiData)
            });
        } else {
            response = await fetch(`${API_BASE}/api/apis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(apiData)
            });
        }
        
        if (response.ok) {
            closeApiModal();
            loadApis();
            showMessage('保存成功！', 'success');
        } else {
            const error = await response.json();
            showMessage('保存失败: ' + (error.detail || '未知错误'), 'error');
        }
    } catch (err) {
        console.error('保存失败:', err);
        showMessage('保存失败: ' + err.message, 'error');
    }
}

async function deleteApi(apiId) {
    if (!confirm('确定要删除这个 API 配置吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/apis/${apiId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadApis();
            showMessage('删除成功！', 'success');
        } else {
            const error = await response.json();
            showMessage('删除失败: ' + (error.detail || '未知错误'), 'error');
        }
    } catch (err) {
        console.error('删除失败:', err);
        showMessage('删除失败: ' + err.message, 'error');
    }
}

async function setDefaultApi(apiId) {
    try {
        const response = await fetch(`${API_BASE}/api/apis/${apiId}/set-default`, {
            method: 'POST'
        });
        
        if (response.ok) {
            defaultApiId = apiId;
            renderApis();
            showMessage('已设置为默认 API', 'success');
        } else {
            const error = await response.json();
            showMessage('设置失败: ' + (error.detail || '未知错误'), 'error');
        }
    } catch (err) {
        console.error('设置失败:', err);
        showMessage('设置失败: ' + err.message, 'error');
    }
}

function toggleApiKeyVisibility() {
    const apiKeyInput = document.getElementById('apiKey');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (apiKeyInput.type === 'password') {
        apiKeyInput.type = 'text';
        eyeIcon.textContent = 'visibility_off';
    } else {
        apiKeyInput.type = 'password';
        eyeIcon.textContent = 'visibility';
    }
}

function showMessage(message, type) {
    const colors = {
        'success': 'bg-green-100 text-green-700 border-green-200',
        'error': 'bg-red-100 text-red-700 border-red-200',
        'info': 'bg-blue-100 text-blue-700 border-blue-200'
    };
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `fixed top-4 right-4 px-6 py-3 rounded-xl border-2 ${colors[type]} shadow-lg z-50 animate-fade-in`;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
