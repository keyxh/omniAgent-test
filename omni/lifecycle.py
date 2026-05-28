"""
生命周期管理基类

为多员工调用制提供统一的资源管理接口
确保每个员工的资源都能正确初始化、更新和清理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LifecycleManager(ABC):
    """
    生命周期管理抽象基类
    
    生命周期流程：
    1. on_session_start() - 员工开始工作
    2. update_from_response() - 每次API响应后更新状态
    3. should_compress() - 判断是否需要压缩上下文
    4. compress() - 执行压缩
    5. on_task_complete() - 任务完成
    6. on_session_end() - 员工结束工作
    
    多员工调用制特殊处理：
    - 主员工负责协调，子员工负责执行
    - 每个子员工独立生命周期
    - 资源隔离，避免相互影响
    """
    
    last_prompt_tokens: int = 0
    last_completion_tokens: int = 0
    last_total_tokens: int = 0
    threshold_tokens: int = 0
    context_length: int = 0
    compression_count: int = 0
    
    threshold_percent: float = 0.75
    protect_first_n: int = 3
    protect_last_n: int = 6
    
    session_start_time: Optional[datetime] = None
    session_end_time: Optional[datetime] = None
    is_active: bool = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """员工名称标识"""
    
    @abstractmethod
    def on_session_start(self, worker_id: str, worker_name: str) -> None:
        """
        Session 开始时初始化资源
        
        Args:
            worker_id: 员工ID
            worker_name: 员工名称
        """
    
    @abstractmethod
    def update_from_response(self, usage: Dict[str, Any]) -> None:
        """
        每次API响应后更新状态
        
        Args:
            usage: API响应中的使用量信息
        """
    
    @abstractmethod
    def should_compress(self, prompt_tokens: Optional[int] = None) -> bool:
        """
        判断是否需要压缩上下文
        
        Args:
            prompt_tokens: 当前prompt的token数量
        
        Returns:
            是否需要压缩
        """
    
    @abstractmethod
    def compress(self, messages: list, current_tokens: Optional[int] = None) -> list:
        """
        执行上下文压缩
        
        Args:
            messages: 当前消息列表
            current_tokens: 当前token数量
        
        Returns:
            压缩后的消息列表
        """
    
    @abstractmethod
    def on_task_complete(self, task_id: str, result: str) -> None:
        """
        任务完成时记录
        
        Args:
            task_id: 任务ID
            result: 任务结果
        """
    
    @abstractmethod
    def on_session_end(self) -> None:
        """
        Session 结束时清理资源
        
        多员工调用制特殊处理：
        - 清理该员工的所有资源
        - 释放数据库连接
        - 清理内存缓存
        - 记录session结束时间
        """
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        获取session统计信息
        
        Returns:
            统计信息字典
        """
        duration = None
        if self.session_start_time and self.session_end_time:
            duration = (self.session_end_time - self.session_start_time).total_seconds()
        
        return {
            "name": self.name,
            "total_tokens": self.last_total_tokens,
            "prompt_tokens": self.last_prompt_tokens,
            "completion_tokens": self.last_completion_tokens,
            "compression_count": self.compression_count,
            "session_duration": duration,
            "is_active": self.is_active,
        }


class WorkerSessionPool:
    """
    员工Session池管理器
    
    多员工调用制核心：
    - 管理所有员工的session
    - 确保资源隔离
    - 防止资源泄漏
    """
    
    def __init__(self):
        self.sessions: Dict[str, LifecycleManager] = {}
        self.active_workers: Dict[str, bool] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> worker_id
    
    def register_worker(self, worker_id: str, session: LifecycleManager) -> None:
        """
        注册员工session
        
        Args:
            worker_id: 员工ID
            session: 生命周期管理器
        """
        self.sessions[worker_id] = session
        self.active_workers[worker_id] = False
        logger.info(f"注册员工session: {worker_id}")
    
    def start_worker_session(self, worker_id: str, worker_name: str) -> None:
        """
        启动员工session
        
        Args:
            worker_id: 员工ID
            worker_name: 员工名称
        """
        if worker_id in self.sessions:
            self.sessions[worker_id].on_session_start(worker_id, worker_name)
            self.active_workers[worker_id] = True
            logger.info(f"启动员工session: {worker_id} - {worker_name}")
    
    def end_worker_session(self, worker_id: str) -> None:
        """
        结束员工session
        
        Args:
            worker_id: 员工ID
        """
        if worker_id in self.sessions:
            self.sessions[worker_id].on_session_end()
            self.active_workers[worker_id] = False
            logger.info(f"结束员工session: {worker_id}")
    
    def assign_task(self, task_id: str, worker_id: str) -> None:
        """
        分配任务给员工
        
        Args:
            task_id: 任务ID
            worker_id: 员工ID
        """
        self.task_assignments[task_id] = worker_id
        logger.info(f"分配任务 {task_id} 给员工 {worker_id}")
    
    def complete_task(self, task_id: str, result: str) -> None:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            result: 任务结果
        """
        if task_id in self.task_assignments:
            worker_id = self.task_assignments[task_id]
            if worker_id in self.sessions:
                self.sessions[worker_id].on_task_complete(task_id, result)
            del self.task_assignments[task_id]
            logger.info(f"任务 {task_id} 完成，由员工 {worker_id} 执行")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        获取所有员工的统计信息
        
        Returns:
            所有员工的统计信息
        """
        stats = {}
        for worker_id, session in self.sessions.items():
            stats[worker_id] = session.get_session_stats()
        return stats
    
    def cleanup_all(self) -> None:
        """
        清理所有员工session
        
        用于系统关闭时清理所有资源
        """
        for worker_id in list(self.sessions.keys()):
            self.end_worker_session(worker_id)
        logger.info("清理所有员工session")