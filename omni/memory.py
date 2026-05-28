"""
Memory - 上下文管理系统

智能管理对话历史和上下文
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Memory:
    """记忆系统"""
    
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.threshold = 0.75
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """判断是否需要压缩"""
        current = self._estimate_tokens(messages)
        return current > (self.max_tokens * self.threshold)
    
    def compress(self, messages: List[Dict]) -> List[Dict]:
        """压缩消息历史"""
        if len(messages) <= 5:
            return messages
        
        # 保留最近5条
        recent = messages[-5:]
        old = messages[:-5]
        
        # 生成摘要
        summary = self._create_summary(old)
        
        return [summary] + recent
    
    def _create_summary(self, messages: List[Dict]) -> Dict:
        """创建摘要"""
        summary_parts = []
        
        for msg in messages:
            role = msg.get('role')
            content = str(msg.get('content', ''))[:100]
            
            if role == 'user':
                summary_parts.append(f"用户: {content}")
            elif role == 'assistant':
                if msg.get('tool_calls'):
                    tools = [tc['function']['name'] for tc in msg['tool_calls']]
                    summary_parts.append(f"助手使用: {', '.join(tools)}")
        
        return {
            "role": "user",
            "content": f"[历史摘要]\n" + "\n".join(summary_parts) + "\n[摘要结束]"
        }
    
    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """估算 token 数"""
        total = 0
        for msg in messages:
            content = str(msg.get('content', ''))
            total += len(content) // 4
        return total
    
    def get_status(self, messages: List[Dict]) -> Dict:
        """获取状态"""
        current = self._estimate_tokens(messages)
        usage = (current / self.max_tokens) * 100
        
        return {
            "current_tokens": current,
            "max_tokens": self.max_tokens,
            "usage_percent": usage,
            "status": "正常" if usage < 75 else "接近限制",
        }
