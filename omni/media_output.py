"""
多媒体输出处理模块

支持图片、文件等非文本内容的输出和展示
"""

import json
import base64
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MediaOutput:
    """多媒体输出类"""
    
    def __init__(self, output_type: str, content: Any, metadata: Optional[Dict] = None):
        """
        Args:
            output_type: 输出类型 (text, image, file, data)
            content: 内容（文本、路径、数据等）
            metadata: 元数据
        """
        self.type = output_type
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata
        }


class MediaOutputHandler:
    """
    多媒体输出处理器
    
    负责处理和格式化各种类型的输出
    """
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.outputs = []
    
    def add_text(self, text: str, metadata: Optional[Dict] = None):
        """添加文本输出"""
        output = MediaOutput("text", text, metadata)
        self.outputs.append(output)
        return output
    
    def add_image(self, image_path: str, metadata: Optional[Dict] = None):
        """
        添加图片输出
        
        Args:
            image_path: 图片文件路径
            metadata: 元数据（如宽度、高度、描述等）
        """
        path = Path(image_path)
        if not path.exists():
            logger.warning(f"图片文件不存在: {image_path}")
            return None
        
        # 读取图片并转换为 base64
        try:
            with open(path, 'rb') as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            mime_type = mimetypes.guess_type(str(path))[0] or 'image/png'
            
            output_metadata = {
                "filename": path.name,
                "mime_type": mime_type,
                "size": len(image_data),
                **(metadata or {})
            }
            
            output = MediaOutput(
                "image",
                {
                    "path": str(path),
                    "base64": image_base64,
                    "mime_type": mime_type
                },
                output_metadata
            )
            
            self.outputs.append(output)
            return output
            
        except Exception as e:
            logger.error(f"读取图片失败: {e}")
            return None
    
    def add_file(self, file_path: str, metadata: Optional[Dict] = None):
        """
        添加文件输出
        
        Args:
            file_path: 文件路径
            metadata: 元数据
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return None
        
        mime_type = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
        
        output_metadata = {
            "filename": path.name,
            "mime_type": mime_type,
            "size": path.stat().st_size,
            "extension": path.suffix,
            **(metadata or {})
        }
        
        output = MediaOutput(
            "file",
            {
                "path": str(path),
                "download_url": f"{self.base_url}/api/files/{path.name}"
            },
            output_metadata
        )
        
        self.outputs.append(output)
        return output
    
    def add_data(self, data: Dict[str, Any], metadata: Optional[Dict] = None):
        """
        添加结构化数据输出
        
        Args:
            data: 结构化数据（字典）
            metadata: 元数据
        """
        output = MediaOutput("data", data, metadata)
        self.outputs.append(output)
        return output
    
    def parse_and_add(self, content: Any) -> List[MediaOutput]:
        """
        自动解析内容并添加相应的输出
        
        Args:
            content: 可能包含文本、图片路径、文件路径等的内容
            
        Returns:
            添加的输出列表
        """
        added = []
        
        if isinstance(content, str):
            # 检测图片路径
            import re
            
            # Markdown 图片格式
            md_images = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for img_path in md_images:
                if Path(img_path).exists():
                    output = self.add_image(img_path)
                    if output:
                        added.append(output)
            
            # 检测文件路径（常见扩展名）
            file_pattern = r'(?:^|\s)((?:[A-Za-z]:\\|/)[\w\\/.-]+\.(?:pdf|doc|docx|xls|xlsx|csv|json|xml|zip|tar|gz))(?:\s|$)'
            files = re.findall(file_pattern, content)
            for file_path in files:
                if Path(file_path).exists():
                    output = self.add_file(file_path)
                    if output:
                        added.append(output)
            
            # 添加文本
            if content.strip():
                text_output = self.add_text(content)
                added.append(text_output)
        
        elif isinstance(content, dict):
            # 结构化数据
            if "images" in content:
                for img in content["images"]:
                    output = self.add_image(img)
                    if output:
                        added.append(output)
            
            if "files" in content:
                for file in content["files"]:
                    output = self.add_file(file)
                    if output:
                        added.append(output)
            
            if "text" in content:
                text_output = self.add_text(content["text"])
                added.append(text_output)
            
            if "data" in content:
                data_output = self.add_data(content["data"])
                added.append(data_output)
        
        return added
    
    def get_all_outputs(self) -> List[Dict[str, Any]]:
        """获取所有输出"""
        return [output.to_dict() for output in self.outputs]
    
    def clear(self):
        """清空输出"""
        self.outputs = []
    
    def format_for_stream(self) -> List[Dict[str, Any]]:
        """
        格式化为流式输出格式
        
        Returns:
            适合 SSE 流式传输的消息列表
        """
        messages = []
        
        for output in self.outputs:
            if output.type == "text":
                messages.append({
                    "type": "content",
                    "content": output.content
                })
            
            elif output.type == "image":
                messages.append({
                    "type": "image",
                    "data": output.content["base64"],
                    "mime_type": output.content["mime_type"],
                    "filename": output.metadata.get("filename", "image.png")
                })
            
            elif output.type == "file":
                messages.append({
                    "type": "file",
                    "filename": output.metadata["filename"],
                    "size": output.metadata["size"],
                    "mime_type": output.metadata["mime_type"],
                    "download_url": output.content["download_url"]
                })
            
            elif output.type == "data":
                messages.append({
                    "type": "data",
                    "data": output.content
                })
        
        return messages


def create_media_output_handler(base_url: str = "http://localhost:8080") -> MediaOutputHandler:
    """创建多媒体输出处理器"""
    return MediaOutputHandler(base_url)
