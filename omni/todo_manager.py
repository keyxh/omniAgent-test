import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoManager:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "todos.db"
        
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"任务管理初始化: {db_path}")
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                parent_id INTEGER,
                metadata TEXT,
                FOREIGN KEY (parent_id) REFERENCES tasks(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON tasks(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON tasks(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_priority 
            ON tasks(priority)
        """)
        
        self.conn.commit()
    
    def create_task(
        self,
        session_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        parent_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO tasks 
            (session_id, title, description, status, priority, created_at, updated_at, parent_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, title, description, TaskStatus.PENDING.value, 
            priority, now, now, parent_id, 
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
        task_id = cursor.lastrowid
        
        logger.info(f"创建任务 #{task_id}: {title}")
        return task_id
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        if row:
            task = dict(row)
            if task.get("metadata"):
                task["metadata"] = json.loads(task["metadata"])
            return task
        return None
    
    def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        query += " ORDER BY priority DESC, created_at ASC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        
        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            if task.get("metadata"):
                task["metadata"] = json.loads(task["metadata"])
            tasks.append(task)
        
        return tasks
    
    def update_task_status(
        self,
        task_id: int,
        status: str
    ) -> bool:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        completed_at = now if status == TaskStatus.COMPLETED.value else None
        
        cursor.execute("""
            UPDATE tasks 
            SET status = ?, updated_at = ?, completed_at = ?
            WHERE id = ?
        """, (status, now, completed_at, task_id))
        
        self.conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"更新任务 #{task_id} 状态: {status}")
            return True
        return False
    
    def complete_task(self, task_id: int) -> bool:
        return self.update_task_status(task_id, TaskStatus.COMPLETED.value)
    
    def start_task(self, task_id: int) -> bool:
        return self.update_task_status(task_id, TaskStatus.IN_PROGRESS.value)
    
    def block_task(self, task_id: int) -> bool:
        return self.update_task_status(task_id, TaskStatus.BLOCKED.value)
    
    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None
    ) -> bool:
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        updates = ["updated_at = ?"]
        params = [now]
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        params.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    def delete_task(self, task_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"删除任务 #{task_id}")
            return True
        return False
    
    def get_task_tree(self, session_id: str) -> List[Dict[str, Any]]:
        tasks = self.list_tasks(session_id=session_id)
        
        task_map = {task["id"]: task for task in tasks}
        
        for task in tasks:
            task["subtasks"] = []
        
        root_tasks = []
        for task in tasks:
            parent_id = task.get("parent_id")
            if parent_id and parent_id in task_map:
                task_map[parent_id]["subtasks"].append(task)
            else:
                root_tasks.append(task)
        
        return root_tasks
    
    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, int]:
        cursor = self.conn.cursor()
        
        query = "SELECT status, COUNT(*) as count FROM tasks"
        params = []
        
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        
        query += " GROUP BY status"
        
        cursor.execute(query, params)
        
        stats = {
            "total": 0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "blocked": 0
        }
        
        for row in cursor.fetchall():
            status = row["status"]
            count = row["count"]
            stats[status] = count
            stats["total"] += count
        
        return stats
    
    def close(self):
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
