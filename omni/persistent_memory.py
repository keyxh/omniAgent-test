import sqlite3
import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PersistentMemory:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "memory.db"
        
        self.db_path = db_path
        self._lock = threading.RLock()
        self._local = threading.local()
        self._create_tables()
        logger.info(f"持久化记忆初始化: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _create_tables(self):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER DEFAULT 0,
                    compressed INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON sessions(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON sessions(timestamp)
            """)
            
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts 
                USING fts5(
                    content, 
                    content=sessions, 
                    content_rowid=id
                )
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
                    INSERT INTO sessions_fts(rowid, content) 
                    VALUES (new.id, new.content);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, content) 
                    VALUES('delete', old.id, old.content);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, content) 
                    VALUES('delete', old.id, old.content);
                    INSERT INTO sessions_fts(rowid, content) 
                    VALUES (new.id, new.content);
                END
            """)
            
            conn.commit()
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        tokens: int = 0
    ) -> int:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, timestamp, role, content, tokens)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, datetime.now().isoformat(), role, content, tokens)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_session_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT id, timestamp, role, content, tokens, compressed
                FROM sessions
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (session_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_messages(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if session_id:
                sql = """
                    SELECT s.id, s.session_id, s.timestamp, s.role, s.content, s.tokens
                    FROM sessions s
                    WHERE s.id IN (
                        SELECT rowid FROM sessions_fts WHERE content MATCH ?
                    )
                    AND s.session_id = ?
                    ORDER BY s.timestamp DESC
                    LIMIT ?
                """
                cursor.execute(sql, (query, session_id, limit))
            else:
                sql = """
                    SELECT s.id, s.session_id, s.timestamp, s.role, s.content, s.tokens
                    FROM sessions s
                    WHERE s.id IN (
                        SELECT rowid FROM sessions_fts WHERE content MATCH ?
                    )
                    ORDER BY s.timestamp DESC
                    LIMIT ?
                """
                cursor.execute(sql, (query, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT session_id, MAX(timestamp) as last_timestamp
                FROM sessions
                GROUP BY session_id
                ORDER BY last_timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def compress_old_messages(
        self, 
        session_id: str, 
        keep_recent: int = 10,
        summary: str = ""
    ) -> int:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM sessions
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT -1 OFFSET ?
            """, (session_id, keep_recent))
            
            old_ids = [row[0] for row in cursor.fetchall()]
            
            if not old_ids:
                return 0
            
            if summary:
                cursor.execute("""
                    INSERT INTO sessions (session_id, timestamp, role, content, compressed)
                    VALUES (?, ?, 'system', ?, 1)
                """, (session_id, datetime.now().isoformat(), summary))
            
            placeholders = ','.join('?' * len(old_ids))
            cursor.execute(f"""
                DELETE FROM sessions
                WHERE id IN ({placeholders})
            """, old_ids)
            
            conn.commit()
            
            logger.info(f"压缩会话 {session_id}: 删除 {len(old_ids)} 条旧消息")
            return len(old_ids)
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
    
    def get_session_token_count(self, session_id: str) -> int:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(tokens) FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            result = cursor.fetchone()[0]
            return result if result else 0
    
    def delete_session(self, session_id: str) -> int:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount
    
    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()