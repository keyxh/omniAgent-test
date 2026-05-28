"""
Web 搜索技能示例

演示如何创建自定义技能
"""

from pathlib import Path
from typing import Dict, Any
import subprocess
import json
import logging

from engine.skills import BaseCLI

logger = logging.getLogger(__name__)


class WebSearchCLI(BaseCLI):
    """Web 搜索技能"""
    
    def __init__(self):
        super().__init__(name="web")
        
        self.register_skill(
            name="search",
            handler=self._search_handler,
            description="Search the web using curl and return results",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            category="web"
        )
        
        self.register_skill(
            name="fetch",
            handler=self._fetch_handler,
            description="Fetch content from a URL",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch"
                    }
                },
                "required": ["url"]
            },
            category="web"
        )
    
    def _search_handler(self, args: Dict, working_dir: Path) -> Dict[str, Any]:
        """搜索处理器"""
        query = args.get("query", "")
        num_results = args.get("num_results", 5)
        
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            result = subprocess.run(
                ["curl", "-s", "-A", "Mozilla/5.0", search_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "query": query,
                    "results": f"搜索结果 (前 {num_results} 条)",
                    "raw_html_length": len(result.stdout)
                }
            else:
                return {
                    "success": False,
                    "error": "搜索失败"
                }
                
        except Exception as e:
            logger.error(f"搜索错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fetch_handler(self, args: Dict, working_dir: Path) -> Dict[str, Any]:
        """获取 URL 内容"""
        url = args.get("url", "")
        
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", url],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                content = result.stdout[:5000]
                return {
                    "success": True,
                    "url": url,
                    "content": content,
                    "length": len(result.stdout)
                }
            else:
                return {
                    "success": False,
                    "error": "获取失败"
                }
                
        except Exception as e:
            logger.error(f"获取错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_requirements(self) -> bool:
        """检查 curl 是否可用"""
        try:
            result = subprocess.run(
                ["curl", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False


def create_skill():
    """创建技能实例 - 必须实现这个函数"""
    return WebSearchCLI()
