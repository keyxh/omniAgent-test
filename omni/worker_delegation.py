"""
员工协作工具 - 让主员工可以调用其他员工
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkerDelegationTool:
    """
    员工委派工具
    
    允许主员工将任务委派给专业的子员工处理
    """
    
    def __init__(self, worker_manager, engine_factory):
        """
        Args:
            worker_manager: 员工管理器实例
            engine_factory: 用于创建子引擎的工厂函数
        """
        self.worker_manager = worker_manager
        self.engine_factory = engine_factory
        self.delegation_history = []
    
    def get_available_workers(self) -> List[Dict[str, Any]]:
        """获取可用的员工列表"""
        workers = self.worker_manager.list_workers(include_disabled=False)
        return [
            {
                "id": w.id,
                "name": w.name,
                "prompt": w.prompt[:100] + "..." if len(w.prompt) > 100 else w.prompt,
                "tools": w.cli_tools,
                "model": w.model
            }
            for w in workers
        ]
    
    def delegate_task(
        self,
        worker_id: str,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        将任务委派给指定员工
        
        Args:
            worker_id: 目标员工 ID
            task: 任务描述
            context: 可选的上下文信息
            
        Returns:
            包含结果的字典，可能包含文本、图片路径、文件路径等
        """
        worker = self.worker_manager.get_worker(worker_id)
        if not worker:
            return {
                "success": False,
                "error": f"员工 {worker_id} 不存在"
            }
        
        logger.info(f"委派任务给员工 '{worker.name}': {task[:50]}...")
        
        try:
            # 创建子引擎执行任务
            sub_engine = self.engine_factory(worker_id=worker_id)
            
            # 构建完整的任务描述
            full_task = task
            if context:
                full_task = f"上下文：{context}\n\n任务：{task}"
            
            # 执行任务
            result = sub_engine.execute(
                task=full_task,
                capabilities=sub_engine.get_capabilities()
            )
            
            # 记录委派历史
            self.delegation_history.append({
                "worker_id": worker_id,
                "worker_name": worker.name,
                "task": task,
                "result": result[:200] if isinstance(result, str) else str(result)[:200]
            })
            
            # 解析结果，检查是否包含多媒体内容
            parsed_result = self._parse_result(result)
            
            return {
                "success": True,
                "worker_name": worker.name,
                "result": parsed_result
            }
            
        except Exception as e:
            logger.error(f"委派任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_result(self, result: Any) -> Dict[str, Any]:
        """
        解析结果，识别多媒体内容
        
        Returns:
            {
                "text": "文本内容",
                "images": ["path/to/image1.png", ...],
                "files": ["path/to/file1.pdf", ...],
                "data": {...}  # 结构化数据
            }
        """
        parsed = {
            "text": "",
            "images": [],
            "files": [],
            "data": None
        }
        
        if isinstance(result, str):
            parsed["text"] = result
            
            # 检测图片路径
            import re
            image_patterns = [
                r'!\[.*?\]\((.*?\.(?:png|jpg|jpeg|gif|svg|webp))\)',  # Markdown 图片
                r'((?:/|[A-Za-z]:\\).*?\.(?:png|jpg|jpeg|gif|svg|webp))',  # 文件路径
            ]
            
            for pattern in image_patterns:
                matches = re.findall(pattern, result, re.IGNORECASE)
                for match in matches:
                    if Path(match).exists():
                        parsed["images"].append(match)
            
            # 检测文件路径
            file_patterns = [
                r'((?:/|[A-Za-z]:\\).*?\.(?:pdf|doc|docx|xls|xlsx|csv|json|xml))',
            ]
            
            for pattern in file_patterns:
                matches = re.findall(pattern, result, re.IGNORECASE)
                for match in matches:
                    if Path(match).exists():
                        parsed["files"].append(match)
        
        elif isinstance(result, dict):
            parsed["data"] = result
            if "text" in result:
                parsed["text"] = result["text"]
            if "images" in result:
                parsed["images"] = result["images"]
            if "files" in result:
                parsed["files"] = result["files"]
        
        return parsed
    
    def get_delegation_history(self) -> List[Dict[str, Any]]:
        """获取委派历史"""
        return self.delegation_history


def create_worker_delegation_capability(worker_manager, engine_factory):
    """
    创建员工委派能力描述
    
    这个能力会被注册到主员工的工具列表中
    """
    tool = WorkerDelegationTool(worker_manager, engine_factory)
    
    return {
        "name": "delegate_to_worker",
        "description": "将任务委派给专业的子员工处理。当遇到需要特定专业知识或工具的任务时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "worker_id": {
                    "type": "string",
                    "description": "目标员工的 ID"
                },
                "task": {
                    "type": "string",
                    "description": "要委派的任务描述"
                },
                "context": {
                    "type": "string",
                    "description": "可选的上下文信息"
                }
            },
            "required": ["worker_id", "task"]
        },
        "handler": tool.delegate_task,
        "tool_instance": tool
    }


def create_list_workers_capability(worker_manager):
    """
    创建列出员工的能力
    """
    tool = WorkerDelegationTool(worker_manager, None)
    
    return {
        "name": "list_available_workers",
        "description": "列出所有可用的员工及其专长，用于决定将任务委派给谁。",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "handler": tool.get_available_workers
    }
