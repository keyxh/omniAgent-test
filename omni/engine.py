"""
Omni Engine - 多员工调用制主引擎

核心设计：
1. 主员工负责协调和分配任务
2. 子员工负责执行具体任务
3. 每个员工独立生命周期管理
4. 资源隔离，防止泄漏
5. 使用量追踪，成本控制
"""

import time
import logging
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .lifecycle import LifecycleManager, WorkerSessionPool
from .brain import Brain
from .memory import Memory
from .shield import Shield
from .recovery import Recovery
from .client import OPCClient
from .persistent_memory import PersistentMemory
from .context_compressor import ContextCompressor
from .todo_manager import TodoManager
from .tool_visualizer import ToolVisualizer, EnhancedToolExecutor
from .agent_worker import WorkerManager, AgentWorker, WorkerStatus

logger = logging.getLogger(__name__)


class OmniEngine(LifecycleManager):
    """
    Omni 主引擎 - 多员工调用制
    
    核心架构：
    - 主员工：负责接收任务、分配给子员工、协调执行
    - 子员工：负责执行具体任务、独立生命周期
    - 资源管理：每个员工独立资源，防止泄漏
    - 成本控制：追踪每个员工的使用量
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        stream: bool = True,
        max_iterations: int = 50,
        working_dir: Optional[Path] = None,
        enable_shield: bool = True,
        enable_recovery: bool = True,
        enable_persistent_memory: bool = True,
        enable_context_compression: bool = True,
        worker_id: Optional[str] = None,
        quiet: bool = False,
    ):
        self.model = model
        self.provider = provider
        self.max_iterations = max_iterations
        self.working_dir = working_dir or Path.cwd()
        self.quiet = quiet
        
        self.last_prompt_tokens: int = 0
        self.last_completion_tokens: int = 0
        self.last_total_tokens: int = 0
        self.threshold_tokens: int = 0
        self.context_length: int = 0
        self.compression_count: int = 0
        self.threshold_percent: float = 0.75
        self.protect_first_n: int = 3
        self.protect_last_n: int = 6
        
        self.session_start_time: Optional[datetime] = None
        self.session_end_time: Optional[datetime] = None
        self.is_active: bool = False
        
        self.worker_manager = WorkerManager()
        
        if worker_id:
            self.worker = self.worker_manager.get_worker(worker_id)
        else:
            self.worker = self.worker_manager.get_current_worker()
        
        if self.worker:
            self.model = self.worker.model
            self.provider = self.worker.provider
            self.worker_id = self.worker.id
            self.worker_name = self.worker.name
            logger.info(f"使用员工：{self.worker.name} ({self.worker.id})")
        else:
            self.worker_id = "default"
            self.worker_name = "Default Worker"
        
        self.session_id = str(uuid.uuid4())
        self.task_id = str(uuid.uuid4())
        
        self.client = OPCClient(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            stream=stream,
        )
        
        self.brain = Brain(working_dir=self.working_dir)
        self.memory = Memory(max_tokens=128000)
        self.shield = Shield(working_dir=self.working_dir) if enable_shield else None
        self.recovery = Recovery() if enable_recovery else None
        
        self.persistent_memory = PersistentMemory() if enable_persistent_memory else None
        self.context_compressor = ContextCompressor(max_tokens=100000) if enable_context_compression else None
        self.todo_manager = TodoManager()
        self.visualizer = ToolVisualizer(quiet=quiet)
        self.tool_executor = EnhancedToolExecutor(self.visualizer)
        
        self.messages: List[Dict] = []
        self.iteration = 0
        self.start_time = None
        
        self.total_cost = 0.0
        self.task_history: List[Dict] = []
        
        self.session_pool = WorkerSessionPool()
        self.session_pool.register_worker(self.worker_id, self)
        
        logger.info(f"Omni Engine 初始化完成：{model} @ {provider}")
        logger.info(f"会话 ID: {self.session_id}")
        logger.info(f"员工 ID: {self.worker_id}")
    
    @property
    def name(self) -> str:
        return self.worker_name
    
    def on_session_start(self, worker_id: str, worker_name: str) -> None:
        self.session_start_time = datetime.now()
        self.is_active = True
        self.worker_id = worker_id
        self.worker_name = worker_name
        
        if self.worker:
            self.worker.set_status(WorkerStatus.ACTIVE)
        
        logger.info(f"员工 {worker_name} ({worker_id}) 开始工作")
        logger.info(f"Session 开始时间: {self.session_start_time}")
    
    def update_from_response(self, usage: Dict[str, Any]) -> None:
        self.last_prompt_tokens = usage.get('prompt_tokens', 0)
        self.last_completion_tokens = usage.get('completion_tokens', 0)
        self.last_total_tokens = self.last_prompt_tokens + self.last_completion_tokens
        
        cost_per_1k_tokens = 0.03
        self.total_cost += (self.last_total_tokens / 1000) * cost_per_1k_tokens
        
        logger.debug(f"使用量更新: prompt={self.last_prompt_tokens}, completion={self.last_completion_tokens}, total={self.last_total_tokens}")
        logger.debug(f"累计成本: ${self.total_cost:.4f}")
    
    def should_compress(self, prompt_tokens: Optional[int] = None) -> bool:
        if not self.context_compressor:
            return False
        
        current_tokens = prompt_tokens or self.last_prompt_tokens
        threshold = self.memory.max_tokens * self.threshold_percent
        
        should = current_tokens > threshold
        
        if should:
            logger.info(f"需要压缩: current={current_tokens}, threshold={threshold}")
        
        return should
    
    def compress(self, messages: list, current_tokens: Optional[int] = None) -> list:
        if not self.context_compressor:
            return messages
        
        self.compression_count += 1
        old_count = len(messages)
        
        compressed_messages, summary = self.context_compressor.compress_messages(messages)
        new_count = len(compressed_messages)
        
        logger.info(f"压缩完成: {old_count} -> {new_count} 条消息")
        
        if self.persistent_memory and summary:
            self.persistent_memory.compress_old_messages(
                self.session_id,
                keep_recent=10,
                summary=summary
            )
        
        return compressed_messages
    
    def on_task_complete(self, task_id: str, result: str) -> None:
        task_record = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "result": result[:500],
            "tokens_used": self.last_total_tokens,
            "cost": self.total_cost,
            "iterations": self.iteration,
            "completion_time": datetime.now().isoformat(),
        }
        
        self.task_history.append(task_record)
        
        if self.worker:
            self.worker.set_status(WorkerStatus.IDLE)
        
        logger.info(f"任务 {task_id} 完成，员工 {self.worker_name}")
        logger.info(f"使用量: {self.last_total_tokens} tokens, 成本: ${self.total_cost:.4f}")
    
    def on_session_end(self) -> None:
        self.session_end_time = datetime.now()
        self.is_active = False
        
        if self.persistent_memory:
            self.persistent_memory.close()
        
        if self.worker:
            self.worker.set_status(WorkerStatus.IDLE)
        
        self.messages = []
        
        logger.info(f"员工 {self.worker_name} ({self.worker_id}) 结束工作")
        logger.info(f"Session 结束时间: {self.session_end_time}")
        logger.info(f"总成本: ${self.total_cost:.4f}")
    
    def execute(
        self,
        task: str,
        capabilities: Optional[List[Dict]] = None,
        context: Optional[Dict] = None,
    ) -> str:
        try:
            self.on_session_start(self.worker_id, self.worker_name)
            
            self._reset()
            
            system_prompt = self.brain.generate(
                capabilities=capabilities or [],
                context=context.get('description') if context else None
            )
            
            self.messages.append({
                "role": "user",
                "content": task
            })
            
            if self.persistent_memory:
                self.persistent_memory.add_message(
                    self.session_id,
                    "user",
                    task,
                    tokens=self.persistent_memory.estimate_tokens(task)
                )
            
            if not self.quiet:
                print(f"\n🚀 Omni Engine 启动")
                print(f"📋 任务: {task[:100]}...")
                print(f"🔧 能力: {len(capabilities or [])} 个")
                print(f"🆔 会话: {self.session_id[:8]}...")
                print(f"👤 员工: {self.worker_name} ({self.worker_id})\n")
            
            while self.iteration < self.max_iterations:
                self.iteration += 1
                
                self.visualizer.show_iteration(self.iteration, self.max_iterations)
                
                try:
                    if self.should_compress():
                        self.messages = self.compress(self.messages)
                    
                    response = self._call_model(
                        system_prompt=system_prompt,
                        messages=self.messages,
                        capabilities=capabilities,
                    )
                    
                    if 'usage' in response:
                        self.update_from_response(response['usage'])
                    
                    if response.get('tool_calls'):
                        self._handle_capability_calls(response)
                        continue
                    else:
                        final_response = response.get('content', '')
                        self.messages.append({
                            "role": "assistant",
                            "content": final_response
                        })
                        
                        if self.persistent_memory:
                            self.persistent_memory.add_message(
                                self.session_id,
                                "assistant",
                                final_response,
                                tokens=self.persistent_memory.estimate_tokens(final_response)
                            )
                        
                        self.on_task_complete(self.task_id, final_response)
                        
                        if not self.quiet:
                            elapsed = time.time() - self.start_time
                            self.visualizer.show_summary(
                                iterations=self.iteration,
                                elapsed_time=elapsed,
                                tool_calls=self.tool_executor.get_stats()["tool_calls"]
                            )
                            print(f"\n💰 成本: ${self.total_cost:.4f}")
                            print(f"📊 Tokens: {self.last_total_tokens}")
                        
                        return final_response
                        
                except Exception as e:
                    logger.error(f"执行错误: {e}", exc_info=True)
                    
                    if self.recovery:
                        self.visualizer.show_error(str(e), recoverable=True)
                        
                        self.messages.append({
                            "role": "user",
                            "content": f"上一步出错: {str(e)}. 请尝试其他方法。"
                        })
                        continue
                    else:
                        self.visualizer.show_error(str(e), recoverable=False)
                        raise
            
            return "达到最大迭代次数,任务未完成。"
            
        finally:
            self.on_session_end()
    
    def delegate_to_worker(self, worker_id: str, task: str, capabilities: Optional[List[Dict]] = None) -> str:
        """
        委派任务给其他员工
        
        多员工调用制核心：
        - 主员工委派任务给子员工
        - 子员工独立执行
        - 资源隔离
        
        Args:
            worker_id: 目标员工ID
            task: 任务描述
            capabilities: 可用能力
        
        Returns:
            执行结果
        """
        target_worker = self.worker_manager.get_worker(worker_id)
        
        if not target_worker:
            logger.error(f"员工 {worker_id} 不存在")
            return f"错误: 员工 {worker_id} 不存在"
        
        logger.info(f"委派任务给员工: {target_worker.name} ({worker_id})")
        
        sub_engine = OmniEngine(
            model=target_worker.model,
            provider=target_worker.provider,
            working_dir=self.working_dir,
            worker_id=worker_id,
            quiet=self.quiet,
        )
        
        self.session_pool.assign_task(str(uuid.uuid4()), worker_id)
        
        try:
            result = sub_engine.execute(task, capabilities)
            self.session_pool.complete_task(str(uuid.uuid4()), result)
            return result
        finally:
            sub_engine.on_session_end()
    
    def delegate_to_workers_parallel(
        self,
        worker_tasks: List[Dict[str, str]],
        capabilities: Optional[List[Dict]] = None
    ) -> Dict[str, str]:
        """
        并行委派任务给多个员工
        
        Args:
            worker_tasks: [{"worker_id": "xxx", "task": "xxx"}, ...]
            capabilities: 可用能力
        
        Returns:
            {"worker_id": "result", ...}
        """
        import concurrent.futures
        
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(worker_tasks)) as executor:
            futures = {}
            for wt in worker_tasks:
                future = executor.submit(
                    self.delegate_to_worker,
                    wt["worker_id"],
                    wt["task"],
                    capabilities
                )
                futures[future] = wt["worker_id"]
            
            for future in concurrent.futures.as_completed(futures):
                worker_id = futures[future]
                try:
                    results[worker_id] = future.result()
                except Exception as e:
                    results[worker_id] = f"错误: {str(e)}"
        
        return results
    
    def _call_model(
        self,
        system_prompt: str,
        messages: List[Dict],
        capabilities: Optional[List[Dict]],
    ) -> Dict:
        if self.recovery:
            return self.recovery.execute(
                lambda: self.client.chat(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=capabilities,
                )
            )
        else:
            return self.client.chat(
                system_prompt=system_prompt,
                messages=messages,
                tools=capabilities,
            )
    
    def _handle_capability_calls(self, response: Dict):
        from engine import execute_capability
        import json
        
        tool_calls = response.get('tool_calls', [])
        
        self.messages.append({
            "role": "assistant",
            "content": response.get('content') or "",
            "tool_calls": tool_calls
        })
        
        for call in tool_calls:
            capability_name = call['function']['name']
            tool_call_id = call['id']
            
            try:
                args_str = call['function'].get('arguments', '{}')
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str
            except json.JSONDecodeError as e:
                logger.error(f"参数解析失败: {e}")
                self.visualizer.show_error(f"参数解析失败: {e}", recoverable=False)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({"error": f"参数解析失败: {str(e)}"})
                })
                continue
            
            if self.shield:
                is_safe, reason = self.shield.check_capability(
                    capability_name,
                    args
                )
                
                if not is_safe:
                    result = {"error": f"安全检查失败: {reason}"}
                    self.visualizer.show_error(f"安全检查失败: {reason}", recoverable=False)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(result)
                    })
                    continue
            
            def executor_fn(name, args_dict):
                return execute_capability(
                    name,
                    args_dict,
                    working_dir=self.working_dir,
                )
            
            result = self.tool_executor.execute_tool(
                capability_name,
                args,
                tool_call_id,
                executor_fn
            )
            
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result) if isinstance(result, dict) else str(result)
            })
            
            if self.persistent_memory:
                self.persistent_memory.add_message(
                    self.session_id,
                    "tool",
                    f"[{capability_name}] {json.dumps(result)[:500]}",
                    tokens=self.persistent_memory.estimate_tokens(str(result))
                )
    
    def _reset(self):
        self.messages = []
        self.iteration = 0
        self.start_time = time.time()
        self.task_id = str(uuid.uuid4())
    
    def get_stats(self) -> Dict:
        base_stats = self.get_session_stats()
        
        return {
            **base_stats,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "messages": len(self.messages),
            "memory_status": self.memory.get_status(self.messages),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0,
            "total_cost": self.total_cost,
            "task_history_count": len(self.task_history),
        }
    
    def get_context_info(self) -> Dict:
        info = {
            "session_id": self.session_id,
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "iteration": self.iteration,
            "messages_count": len(self.messages),
            "max_iterations": self.max_iterations,
            "is_active": self.is_active,
        }
        
        if self.memory:
            status = self.memory.get_status(self.messages)
            tokens = status.get("current_tokens", 0)
            max_tokens = self.memory.max_tokens
            info["memory"] = {
                "current_tokens": tokens,
                "max_tokens": max_tokens,
                "usage_percent": (tokens / max_tokens * 100) if max_tokens > 0 else 0,
            }
        
        if self.persistent_memory:
            info["persistent_memory"] = {
                "enabled": True,
                "db_path": str(self.persistent_memory.db_path),
            }
        
        if self.context_compressor:
            info["context_compressor"] = {
                "enabled": True,
                "max_tokens": self.context_compressor.max_tokens,
                "compression_count": self.compression_count,
            }
        
        info["cost_tracking"] = {
            "total_cost": self.total_cost,
            "last_tokens": self.last_total_tokens,
        }
        
        return info
    
    def get_all_workers_stats(self) -> Dict[str, Any]:
        return self.session_pool.get_all_stats()