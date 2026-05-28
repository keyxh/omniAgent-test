"""
数据库管理 - SQLite
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite 数据库管理"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                api_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cli_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                cli_path TEXT,
                usage TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT,
                default_args TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cli_tools_category 
            ON cli_tools(category)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    def create_conversation(self, conversation_id: str, title: str, api_id: str) -> bool:
        """创建新对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO conversations (id, title, api_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (conversation_id, title, api_id, now, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            return False
    
    def get_conversations(self, limit: int = 50) -> List[Dict]:
        """获取对话列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, api_id, created_at, updated_at, message_count
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            return []
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """获取单个对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, api_id, created_at, updated_at, message_count
                FROM conversations
                WHERE id = ?
            ''', (conversation_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取对话失败: {e}")
            return None
    
    def update_conversation(self, conversation_id: str, title: Optional[str] = None) -> bool:
        """更新对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            if title:
                cursor.execute('''
                    UPDATE conversations
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                ''', (title, now, conversation_id))
            else:
                cursor.execute('''
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE id = ?
                ''', (now, conversation_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新对话失败: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除对话失败: {e}")
            return False
    
    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """添加消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (conversation_id, role, content, now))
            
            cursor.execute('''
                UPDATE conversations
                SET message_count = message_count + 1, updated_at = ?
                WHERE id = ?
            ''', (now, conversation_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False
    
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """获取对话的所有消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            ''', (conversation_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    def add_cli_tool(self, name: str, usage: str, description: str, 
                     cli_path: str = "", category: str = "", default_args: str = "") -> bool:
        """添加 CLI 工具"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO cli_tools (name, cli_path, usage, description, category, default_args, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, cli_path, usage, description, category, default_args, now, now))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"添加 CLI 工具失败: {e}")
            return False
    
    def get_cli_tools(self) -> List[Dict]:
        """获取所有 CLI 工具"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, cli_path, usage, description, category, default_args, created_at, updated_at
                FROM cli_tools
                ORDER BY created_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取 CLI 工具失败: {e}")
            return []
    
    def update_cli_tool(self, tool_id: int, **kwargs) -> bool:
        """更新 CLI 工具"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['name', 'cli_path', 'usage', 'description', 'category', 'default_args']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return False
            
            fields.append("updated_at = ?")
            values.append(now)
            values.append(tool_id)
            
            cursor.execute(f'''
                UPDATE cli_tools
                SET {", ".join(fields)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新 CLI 工具失败: {e}")
            return False
    
    def delete_cli_tool(self, tool_id: int) -> bool:
        """删除 CLI 工具"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM cli_tools WHERE id = ?', (tool_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除 CLI 工具失败: {e}")
            return False
