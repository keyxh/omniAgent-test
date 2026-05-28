let allTools = [];
let currentEditingToolId = null;

const STORAGE_KEY = 'omni_local_tools';

document.addEventListener('DOMContentLoaded', () => {
    loadTools();
});

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        const textarea = document.getElementById('toolDescription');
        textarea.value = content;
        
        // 显示成功提示
        const label = event.target.parentElement;
        const originalText = label.querySelector('span:last-child').textContent;
        label.querySelector('span:last-child').textContent = `✓ 已加载 ${file.name}`;
        label.classList.add('border-green-400', 'bg-green-50');
        
        setTimeout(() => {
            label.querySelector('span:last-child').textContent = originalText;
            label.classList.remove('border-green-400', 'bg-green-50');
        }, 2000);
    };
    reader.readAsText(file);
    
    // 清空文件选择，允许重复上传同一文件
    event.target.value = '';
}

function loadTools() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        try {
            allTools = JSON.parse(stored);
        } catch (e) {
            allTools = [];
        }
    } else {
        allTools = [];
        saveTools();
    }
    renderTools(allTools);
}

function saveTools() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(allTools));
}

function renderTools(tools) {
    const container = document.getElementById('toolsList');
    const emptyState = document.getElementById('emptyState');
    
    if (tools.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    container.innerHTML = '';
    
    tools.forEach(tool => {
        const card = document.createElement('div');
        card.className = 'tool-card rounded-2xl p-6 shadow-lg';
        card.innerHTML = `
            <div class="flex items-start justify-between mb-4">
                <div class="flex-1">
                    <h3 class="font-bold text-gray-800 text-lg mb-2">${escapeHtml(tool.name)}</h3>
                    ${tool.category ? `<span class="category-badge inline-block bg-blue-100 text-blue-700">${getCategoryName(tool.category)}</span>` : ''}
                </div>
                <div class="flex gap-2">
                    <button onclick="editTool(${tool.id})" class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-xl">edit</span>
                    </button>
                    <button onclick="deleteTool(${tool.id})" class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                        <span class="material-symbols-outlined text-xl">delete</span>
                    </button>
                </div>
            </div>
            ${tool.description ? `<p class="text-sm text-gray-600 mb-3">${escapeHtml(tool.description)}</p>` : ''}
            ${tool.path ? `<div class="text-xs text-gray-500 mb-2"><span class="font-semibold">路径:</span> <code class="bg-gray-100 px-2 py-1 rounded">${escapeHtml(tool.path)}</code></div>` : ''}
            ${tool.usage ? `<div class="text-xs text-gray-700 bg-gray-50 p-3 rounded-lg font-mono">${escapeHtml(tool.usage)}</div>` : ''}
        `;
        container.appendChild(card);
    });
}

function getCategoryName(category) {
    const names = {
        'browser': '浏览器',
        'file': '文件操作',
        'search': '搜索',
        'other': '其他'
    };
    return names[category] || category;
}

function searchTools() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const category = document.getElementById('categoryFilter').value;
    
    let filtered = allTools;
    
    if (query) {
        filtered = filtered.filter(tool => 
            tool.name.toLowerCase().includes(query) ||
            (tool.description && tool.description.toLowerCase().includes(query)) ||
            (tool.usage && tool.usage.toLowerCase().includes(query))
        );
    }
    
    if (category) {
        filtered = filtered.filter(tool => tool.category === category);
    }
    
    renderTools(filtered);
}

function filterByCategory() {
    searchTools();
}

function openAddToolModal() {
    currentEditingToolId = null;
    document.getElementById('modalTitle').textContent = '添加本地工具';
    document.getElementById('toolForm').reset();
    document.getElementById('toolId').value = '';
    document.getElementById('toolModal').classList.remove('hidden');
}

function closeToolModal() {
    document.getElementById('toolModal').classList.add('hidden');
    currentEditingToolId = null;
}

function editTool(toolId) {
    const tool = allTools.find(t => t.id === toolId);
    if (!tool) return;
    
    currentEditingToolId = toolId;
    
    document.getElementById('modalTitle').textContent = '编辑本地工具';
    document.getElementById('toolId').value = tool.id;
    document.getElementById('toolName').value = tool.name;
    document.getElementById('toolPath').value = tool.path || '';
    document.getElementById('toolDescription').value = tool.description || '';
    
    document.getElementById('toolModal').classList.remove('hidden');
}

function saveTool(event) {
    event.preventDefault();
    
    const toolData = {
        name: document.getElementById('toolName').value.trim(),
        path: document.getElementById('toolPath').value.trim(),
        description: document.getElementById('toolDescription').value.trim(),
    };
    
    if (!toolData.name || !toolData.description) {
        alert('请填写所有必填字段（名称、工具说明）');
        return;
    }
    
    const toolId = document.getElementById('toolId').value;
    
    if (toolId) {
        const index = allTools.findIndex(t => t.id === parseInt(toolId));
        if (index !== -1) {
            allTools[index] = { ...allTools[index], ...toolData };
        }
    } else {
        const newId = allTools.length > 0 ? Math.max(...allTools.map(t => t.id)) + 1 : 1;
        allTools.push({ id: newId, ...toolData });
    }
    
    saveTools();
    closeToolModal();
    loadTools();
}

function deleteTool(toolId) {
    if (!confirm('确定要删除这个工具吗？')) return;
    
    allTools = allTools.filter(t => t.id !== toolId);
    saveTools();
    loadTools();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
