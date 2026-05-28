"""
代码分析技能示例

使用 AST 分析代码结构
"""

from pathlib import Path
from typing import Dict, Any
import ast
import logging

from engine.skills import BaseCLI

logger = logging.getLogger(__name__)


class CodeAnalysisCLI(BaseCLI):
    """代码分析技能"""
    
    def __init__(self):
        super().__init__(name="code")
        
        self.register_skill(
            name="analyze",
            handler=self._analyze_handler,
            description="Analyze Python code structure and complexity",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Python file to analyze"
                    }
                },
                "required": ["file_path"]
            },
            category="development"
        )
        
        self.register_skill(
            name="count_lines",
            handler=self._count_lines_handler,
            description="Count lines of code in a file or directory",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to include (e.g., ['.py', '.js'])",
                        "default": [".py"]
                    }
                },
                "required": ["path"]
            },
            category="development"
        )
    
    def _analyze_handler(self, args: Dict, working_dir: Path) -> Dict[str, Any]:
        """分析 Python 代码"""
        file_path = Path(args.get("file_path", ""))
        
        if not file_path.is_absolute():
            file_path = working_dir / file_path
        
        try:
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }
            
            code = file_path.read_text(encoding='utf-8')
            tree = ast.parse(code)
            
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
            
            return {
                "success": True,
                "file": str(file_path),
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "class_count": len(classes),
                "function_count": len(functions),
                "import_count": len(imports),
                "lines": len(code.splitlines())
            }
                
        except Exception as e:
            logger.error(f"代码分析错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _count_lines_handler(self, args: Dict, working_dir: Path) -> Dict[str, Any]:
        """统计代码行数"""
        path = Path(args.get("path", ""))
        extensions = args.get("extensions", [".py"])
        
        if not path.is_absolute():
            path = working_dir / path
        
        try:
            total_lines = 0
            total_files = 0
            
            if path.is_file():
                lines = len(path.read_text(encoding='utf-8').splitlines())
                return {
                    "success": True,
                    "path": str(path),
                    "lines": lines,
                    "files": 1
                }
            elif path.is_dir():
                for ext in extensions:
                    for file in path.rglob(f"*{ext}"):
                        try:
                            lines = len(file.read_text(encoding='utf-8').splitlines())
                            total_lines += lines
                            total_files += 1
                        except:
                            pass
                
                return {
                    "success": True,
                    "path": str(path),
                    "lines": total_lines,
                    "files": total_files,
                    "extensions": extensions
                }
            else:
                return {
                    "success": False,
                    "error": "路径不存在"
                }
                
        except Exception as e:
            logger.error(f"统计错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def create_skill():
    return CodeAnalysisCLI()
