import sys
import time
import json
import threading
from typing import Dict, Any, Optional
from itertools import cycle


class ToolVisualizer:
    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_running = False
        self.spinner_thread = None
    
    def show_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        tool_call_id: Optional[str] = None
    ):
        if self.quiet:
            return
        
        print(f"\n⚡ 执行工具: {tool_name}")
        
        if tool_call_id:
            print(f"🆔 调用ID: {tool_call_id}")
        
        print(f"📝 参数:")
        formatted_args = json.dumps(args, ensure_ascii=False, indent=2)
        for line in formatted_args.split('\n'):
            print(f"   {line}")
    
    def show_tool_result(
        self, 
        tool_name: str, 
        result: Any,
        success: bool = True,
        elapsed_time: Optional[float] = None
    ):
        if self.quiet:
            return
        
        status_icon = "✅" if success else "❌"
        status_text = "完成" if success else "失败"
        
        time_info = f" (用时: {elapsed_time:.2f}s)" if elapsed_time else ""
        print(f"{status_icon} {status_text}{time_info}")
        
        if isinstance(result, dict):
            if result.get("error"):
                print(f"   错误: {result['error']}")
            else:
                result_preview = json.dumps(result, ensure_ascii=False)[:200]
                if len(str(result)) > 200:
                    result_preview += "..."
                print(f"   结果: {result_preview}")
        elif isinstance(result, str):
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"   结果: {preview}")
        else:
            print(f"   结果: {str(result)[:200]}")
    
    def start_spinner(self, message: str = "执行中"):
        if self.quiet or self.spinner_running:
            return
        
        self.spinner_running = True
        
        def spin():
            spinner = cycle(self.spinner_frames)
            while self.spinner_running:
                sys.stdout.write(f"\r{next(spinner)} {message}...")
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")
            sys.stdout.flush()
        
        self.spinner_thread = threading.Thread(target=spin, daemon=True)
        self.spinner_thread.start()
    
    def stop_spinner(self):
        if self.spinner_running:
            self.spinner_running = False
            if self.spinner_thread:
                self.spinner_thread.join(timeout=0.5)
    
    def show_progress(self, current: int, total: int, message: str = ""):
        if self.quiet:
            return
        
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 30
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        
        sys.stdout.write(f"\r[{bar}] {percentage:.1f}% {message}")
        sys.stdout.flush()
        
        if current >= total:
            print()
    
    def show_iteration(self, current: int, max_iterations: int):
        if self.quiet:
            return
        
        print(f"\n🔄 迭代 {current}/{max_iterations}")
    
    def show_context_compression(self, old_count: int, new_count: int):
        if self.quiet:
            return
        
        print(f"\n💾 上下文压缩: {old_count} 条消息 -> {new_count} 条消息")
    
    def show_error(self, error: str, recoverable: bool = True):
        if self.quiet:
            return
        
        icon = "⚠️ " if recoverable else "❌"
        print(f"\n{icon} 错误: {error}")
        
        if recoverable:
            print("   尝试恢复...")
    
    def show_summary(
        self, 
        iterations: int, 
        elapsed_time: float,
        tool_calls: int = 0
    ):
        if self.quiet:
            return
        
        print(f"\n" + "="*50)
        print(f"📊 执行摘要")
        print(f"   迭代次数: {iterations}")
        print(f"   工具调用: {tool_calls}")
        print(f"   总用时: {elapsed_time:.2f}s")
        print("="*50 + "\n")


class EnhancedToolExecutor:
    def __init__(self, visualizer: ToolVisualizer):
        self.visualizer = visualizer
        self.tool_call_count = 0
    
    def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        tool_call_id: Optional[str],
        executor_fn
    ) -> Any:
        self.tool_call_count += 1
        
        self.visualizer.show_tool_call(tool_name, args, tool_call_id)
        
        self.visualizer.start_spinner(f"执行 {tool_name}")
        
        start_time = time.time()
        success = True
        result = None
        
        try:
            result = executor_fn(tool_name, args)
        except Exception as e:
            success = False
            result = {"error": str(e)}
        finally:
            self.visualizer.stop_spinner()
        
        elapsed = time.time() - start_time
        
        self.visualizer.show_tool_result(
            tool_name, 
            result, 
            success=success,
            elapsed_time=elapsed
        )
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        return {
            "tool_calls": self.tool_call_count
        }
