import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ContextCompressor:
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
    
    def estimate_messages_tokens(self, messages: List[Dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        total += self.estimate_tokens(item["text"])
        return total
    
    def should_compress(self, messages: List[Dict]) -> bool:
        return self.estimate_messages_tokens(messages) > self.max_tokens
    
    def compress_messages(
        self, 
        messages: List[Dict],
        keep_recent: int = 10,
        keep_system: bool = True
    ) -> tuple[List[Dict], str]:
        if not self.should_compress(messages):
            return messages, ""
        
        system_messages = []
        user_messages = []
        
        for msg in messages:
            if msg.get("role") == "system" and keep_system:
                system_messages.append(msg)
            else:
                user_messages.append(msg)
        
        if len(user_messages) <= keep_recent:
            return messages, ""
        
        old_messages = user_messages[:-keep_recent]
        recent_messages = user_messages[-keep_recent:]
        
        summary = self._create_summary(old_messages)
        
        compressed = system_messages + [
            {
                "role": "system",
                "content": f"[历史对话摘要]\n{summary}\n[以下是最近的对话]"
            }
        ] + recent_messages
        
        old_tokens = self.estimate_messages_tokens(old_messages)
        new_tokens = self.estimate_messages_tokens(compressed)
        
        logger.info(
            f"上下文压缩: {len(old_messages)} 条消息 "
            f"({old_tokens} tokens) -> 摘要 ({new_tokens} tokens)"
        )
        
        return compressed, summary
    
    def _create_summary(self, messages: List[Dict]) -> str:
        summary_parts = []
        
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if isinstance(content, str):
                preview = content[:100] + "..." if len(content) > 100 else content
            else:
                preview = str(content)[:100] + "..."
            
            summary_parts.append(f"{i}. [{role}] {preview}")
        
        return "\n".join(summary_parts)
    
    def compress_with_llm(
        self,
        messages: List[Dict],
        llm_summarize_fn=None
    ) -> tuple[List[Dict], str]:
        if not self.should_compress(messages):
            return messages, ""
        
        if llm_summarize_fn is None:
            return self.compress_messages(messages)
        
        old_messages = messages[:-10]
        recent_messages = messages[-10:]
        
        conversation_text = "\n\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in old_messages
        ])
        
        try:
            summary = llm_summarize_fn(conversation_text)
        except Exception as e:
            logger.warning(f"LLM 摘要失败: {e}, 使用简单摘要")
            summary = self._create_summary(old_messages)
        
        compressed = [
            {
                "role": "system",
                "content": f"[历史对话摘要]\n{summary}\n[以下是最近的对话]"
            }
        ] + recent_messages
        
        return compressed, summary
