"""
Agent Worker - 员工系统

每个员工 = Prompt + CLI 工具集 + 模型配置
支持：
- 主员工（默认，不可删除）
- 自定义员工（可创建、编辑、删除）
- 员工切换
- 员工协作
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    DISABLED = "disabled"


@dataclass
class AgentWorker:
    """
    员工定义
    
    Attributes:
        id: 员工 ID
        name: 员工名称
        prompt: 系统提示词（定义员工角色和职责）
        cli_tools: 分配的 CLI 工具 ID 列表
        model: 模型配置（如 "gpt-4", "claude-3"）
        provider: 提供商（如 "openai", "anthropic"）
        status: 员工状态
        created_at: 创建时间
        updated_at: 更新时间
        is_default: 是否为主员工（不可删除）
        metadata: 额外元数据
    """
    id: str
    name: str
    prompt: str
    cli_tools: List[str] = field(default_factory=list)
    model: str = "gpt-4"
    provider: str = "openai"
    status: WorkerStatus = WorkerStatus.IDLE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentWorker':
        """从字典创建"""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = WorkerStatus(data['status'])
        return cls(**data)
    
    def add_tool(self, tool_id: str) -> bool:
        """添加工具"""
        if tool_id not in self.cli_tools:
            self.cli_tools.append(tool_id)
            self.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def remove_tool(self, tool_id: str) -> bool:
        """移除工具"""
        if tool_id in self.cli_tools:
            self.cli_tools.remove(tool_id)
            self.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def set_status(self, status: WorkerStatus):
        """设置状态"""
        self.status = status
        self.updated_at = datetime.now().isoformat()


class WorkerManager:
    """
    员工管理器
    
    负责：
    - 创建、读取、更新、删除员工
    - 员工持久化（SQLite）
    - 主员工保护
    - 员工切换
    """
    
    DEFAULT_WORKER_PROMPT = """你是一个全能的 AI 助手，拥有以下核心能力：
- 读取和写入文件
- 执行 shell 命令
- 搜索文件和内容
- 管理项目结构

你的职责是帮助用户完成各种编程和系统管理任务。
请使用提供的工具高效、安全地完成任务。
"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "workers.db"
        
        self.db_path = db_path
        self.workers: Dict[str, AgentWorker] = {}
        self.current_worker_id: Optional[str] = None
        self._init_database()
        self._load_workers()
        logger.info(f"员工管理器初始化完成：{db_path}")
    
    def _init_database(self):
        """初始化数据库"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                cli_tools TEXT NOT NULL DEFAULT '[]',
                model TEXT NOT NULL DEFAULT 'gpt-4',
                provider TEXT NOT NULL DEFAULT 'openai',
                status TEXT NOT NULL DEFAULT 'idle',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS current_worker (
                id INTEGER PRIMARY KEY CHECK (id = 0),
                worker_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_workers(self):
        """从数据库加载员工"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM workers')
        
        for row in cursor.fetchall():
            worker_data = dict(row)
            worker_data['cli_tools'] = json.loads(worker_data['cli_tools'])
            worker_data['is_default'] = bool(worker_data['is_default'])
            worker_data['status'] = WorkerStatus(worker_data['status'])
            if worker_data['metadata']:
                worker_data['metadata'] = json.loads(worker_data['metadata'])
            
            worker = AgentWorker.from_dict(worker_data)
            self.workers[worker.id] = worker
        
        # 加载当前员工
        cursor.execute('SELECT worker_id FROM current_worker WHERE id = 0')
        row = cursor.fetchone()
        if row:
            self.current_worker_id = row['worker_id']
        
        conn.close()
        
        # 如果没有主员工，创建默认的
        if not any(w.is_default for w in self.workers.values()):
            self._create_default_worker()
        
        logger.info(f"加载了 {len(self.workers)} 个员工")
    
    def _create_default_worker(self):
        """创建默认主员工"""
        default_worker = AgentWorker(
            id="default",
            name="主员工",
            prompt=self.DEFAULT_WORKER_PROMPT,
            cli_tools=[],
            model="gpt-4",
            provider="openai",
            is_default=True,
            status=WorkerStatus.IDLE
        )
        
        self._save_worker(default_worker)
        self.workers[default_worker.id] = default_worker
        self.current_worker_id = default_worker.id
        logger.info("创建默认主员工")
    
    def _save_worker(self, worker: AgentWorker):
        """保存员工到数据库"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        worker_data = worker.to_dict()
        worker_data['cli_tools'] = json.dumps(worker_data['cli_tools'])
        worker_data['is_default'] = 1 if worker_data['is_default'] else 0
        metadata_str = json.dumps(worker_data.get('metadata', {})) if worker_data.get('metadata') else '{}'
        
        cursor.execute('''
            INSERT OR REPLACE INTO workers 
            (id, name, prompt, cli_tools, model, provider, status, created_at, updated_at, is_default, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            worker_data['id'],
            worker_data['name'],
            worker_data['prompt'],
            worker_data['cli_tools'],
            worker_data['model'],
            worker_data['provider'],
            worker_data['status'],
            worker_data['created_at'],
            worker_data['updated_at'],
            worker_data['is_default'],
            metadata_str
        ))
        
        conn.commit()
        conn.close()
    
    def create_worker(
        self,
        name: str,
        prompt: str,
        cli_tools: Optional[List[str]] = None,
        model: str = "gpt-4",
        provider: str = "openai",
        metadata: Optional[Dict] = None
    ) -> AgentWorker:
        """创建新员工"""
        import uuid
        
        worker = AgentWorker(
            id=str(uuid.uuid4()),
            name=name,
            prompt=prompt,
            cli_tools=cli_tools or [],
            model=model,
            provider=provider,
            metadata=metadata or {}
        )
        
        self._save_worker(worker)
        self.workers[worker.id] = worker
        
        logger.info(f"创建新员工：{name} ({worker.id})")
        return worker
    
    def get_worker(self, worker_id: str) -> Optional[AgentWorker]:
        """获取员工"""
        return self.workers.get(worker_id)
    
    def list_workers(self, include_disabled: bool = False) -> List[AgentWorker]:
        """列出所有员工"""
        workers = list(self.workers.values())
        
        if not include_disabled:
            workers = [w for w in workers if w.status != WorkerStatus.DISABLED]
        
        # 主员工排在前面
        workers.sort(key=lambda w: (not w.is_default, w.name))
        
        return workers
    
    def update_worker(
        self,
        worker_id: str,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        cli_tools: Optional[List[str]] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """更新员工"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        if name is not None:
            worker.name = name
        
        if prompt is not None:
            worker.prompt = prompt
        
        if cli_tools is not None:
            worker.cli_tools = cli_tools
        
        if model is not None:
            worker.model = model
        
        if provider is not None:
            worker.provider = provider
        
        if metadata is not None:
            worker.metadata = metadata
        
        worker.updated_at = datetime.now().isoformat()
        self._save_worker(worker)
        
        logger.info(f"更新员工：{worker.name}")
        return True
    
    def delete_worker(self, worker_id: str) -> bool:
        """删除员工"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        # 主员工不可删除
        if worker.is_default:
            logger.error(f"无法删除主员工：{worker.name}")
            return False
        
        # 从数据库删除
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workers WHERE id = ?', (worker_id,))
        conn.commit()
        conn.close()
        
        # 从内存删除
        del self.workers[worker_id]
        
        # 如果删除的是当前员工，切换到主员工
        if self.current_worker_id == worker_id:
            default_worker = next((w for w in self.workers.values() if w.is_default), None)
            if default_worker:
                self.current_worker_id = default_worker.id
        
        logger.info(f"删除员工：{worker.name}")
        return True
    
    def set_current_worker(self, worker_id: str) -> bool:
        """设置当前员工"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        self.current_worker_id = worker_id
        
        # 保存到数据库
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO current_worker (id, worker_id)
            VALUES (0, ?)
        ''', (worker_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"切换到员工：{worker.name}")
        return True
    
    def get_current_worker(self) -> Optional[AgentWorker]:
        """获取当前员工"""
        if not self.current_worker_id:
            return None
        return self.workers.get(self.current_worker_id)
    
    def add_tool_to_worker(self, worker_id: str, tool_id: str) -> bool:
        """为员工添加工具"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        if worker.add_tool(tool_id):
            self._save_worker(worker)
            logger.info(f"为员工 {worker.name} 添加工具 {tool_id}")
            return True
        return False
    
    def remove_tool_from_worker(self, worker_id: str, tool_id: str) -> bool:
        """从员工移除工具"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        if worker.remove_tool(tool_id):
            self._save_worker(worker)
            logger.info(f"从员工 {worker.name} 移除工具 {tool_id}")
            return True
        return False
    
    def get_worker_tools(self, worker_id: str) -> List[str]:
        """获取员工的工具列表"""
        worker = self.workers.get(worker_id)
        return worker.cli_tools if worker else []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        workers = list(self.workers.values())
        
        return {
            "total_workers": len(workers),
            "default_workers": sum(1 for w in workers if w.is_default),
            "custom_workers": sum(1 for w in workers if not w.is_default),
            "active_workers": sum(1 for w in workers if w.status == WorkerStatus.ACTIVE),
            "busy_workers": sum(1 for w in workers if w.status == WorkerStatus.BUSY),
            "idle_workers": sum(1 for w in workers if w.status == WorkerStatus.IDLE),
            "current_worker": self.workers[self.current_worker_id].name if self.current_worker_id and self.current_worker_id in self.workers else None
        }
