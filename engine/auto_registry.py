"""
自动工具注册系统
自动发现和注册所有工具
"""

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Callable, Any
import logging

logger = logging.getLogger(__name__)


class AutoToolRegistry:
    """自动工具注册器"""
    
    def __init__(self, registry):
        self.registry = registry
        self.discovered_tools = {}
    
    def discover_tools_from_directory(self, directory: str, category: str = "auto"):
        """从目录自动发现工具"""
        tools_dir = Path(directory)
        
        if not tools_dir.exists():
            logger.warning(f"工具目录不存在: {directory}")
            return
        
        for file_path in tools_dir.rglob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                cwd = Path.cwd()
                try:
                    relative_path = file_path.relative_to(cwd)
                except ValueError:
                    relative_path = file_path
                
                module_name = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
                
                if module_name.startswith("."):
                    module_name = module_name[1:]
                
                print(f"  📦 尝试加载: {module_name}")
                
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module):
                    if self._is_tool_function(obj):
                        self._register_tool(obj, category)
                        
            except Exception as e:
                print(f"  ⚠️ 跳过 {file_path.name}: {e}")
    
    def _is_tool_function(self, obj) -> bool:
        """判断是否是工具函数"""
        if not callable(obj):
            return False
        
        if not hasattr(obj, '_tool_info'):
            return False
        
        return True
    
    def _register_tool(self, func: Callable, category: str):
        """注册工具"""
        tool_info = getattr(func, '_tool_info', {})
        
        name = tool_info.get('name', func.__name__)
        description = tool_info.get('description', func.__doc__ or '')
        parameters = tool_info.get('parameters', {})
        
        self.registry.register(
            name=name,
            handler=func,
            description=description,
            parameters=parameters,
            category=category
        )
        
        self.discovered_tools[name] = {
            'function': func,
            'info': tool_info
        }
        
        print(f"  ✓ 已注册工具: {name}")


def tool(name: str, description: str, parameters: Dict = None):
    """工具装饰器"""
    def decorator(func):
        func._tool_info = {
            'name': name,
            'description': description,
            'parameters': parameters or {}
        }
        return func
    return decorator


def auto_register_tools(registry, tool_dirs: List[str] = None):
    """自动注册所有工具"""
    auto_registry = AutoToolRegistry(registry)
    
    if tool_dirs is None:
        tool_dirs = [
            'engine',
            'skills',
            'tool'
        ]
    
    print("\n🔧 自动发现工具...")
    
    for tool_dir in tool_dirs:
        print(f"\n📂 扫描目录: {tool_dir}/")
        auto_registry.discover_tools_from_directory(tool_dir)
    
    if auto_registry.discovered_tools:
        print(f"\n✅ 成功注册 {len(auto_registry.discovered_tools)} 个工具")
    else:
        print(f"\n⚠️ 未发现任何工具")
    
    return auto_registry.discovered_tools
