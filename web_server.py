"""
OmniAgent Web Server - 生产级 AI Agent 系统

简洁的 FastAPI 后端，独立的生产级版本
"""

import asyncio
import json
import uuid
import logging
import sys
from typing import Dict, Optional
from pathlib import Path
from queue import Queue
from threading import Thread

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database import Database
from omni.persistent_memory import PersistentMemory
from omni.todo_manager import TodoManager
from omni.engine import OmniEngine
from engine import get_capabilities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONFIG_FILE = Path(__file__).parent / "config.json"
DB_DIR = Path(__file__).parent / "db"
DB_FILE = DB_DIR / "omniagent.db"
MEMORY_DB = DB_DIR / "memory.db"
TODO_DB = DB_DIR / "todos.db"
WORKERS_DB = DB_DIR / "workers.db"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
        
        return {
            "apis": [],
            "default_api_id": None,
            "max_iterations": 50
        }
    
    def save_config(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    def get_api(self, api_id: str) -> Optional[Dict]:
        for api in self.config.get("apis", []):
            if api.get("id") == api_id:
                return api
        return None
    
    def get_default_api(self) -> Optional[Dict]:
        default_id = self.config.get("default_api_id")
        if default_id:
            return self.get_api(default_id)
        
        apis = self.config.get("apis", [])
        return apis[0] if apis else None
    
    def add_api(self, api_config: Dict) -> str:
        if "apis" not in self.config:
            self.config["apis"] = []
        
        if not api_config.get("id"):
            api_config["id"] = str(uuid.uuid4())
        
        self.config["apis"].append(api_config)
        
        if not self.config.get("default_api_id"):
            self.config["default_api_id"] = api_config["id"]
        
        self.save_config()
        return api_config["id"]
    
    def update_api(self, api_id: str, updates: Dict) -> bool:
        for i, api in enumerate(self.config.get("apis", [])):
            if api.get("id") == api_id:
                self.config["apis"][i].update(updates)
                self.config["apis"][i]["id"] = api_id
                self.save_config()
                return True
        return False
    
    def delete_api(self, api_id: str) -> bool:
        self.config["apis"] = [
            api for api in self.config.get("apis", [])
            if api.get("id") != api_id
        ]
        
        if self.config.get("default_api_id") == api_id:
            apis = self.config.get("apis", [])
            self.config["default_api_id"] = apis[0]["id"] if apis else None
        
        self.save_config()
        return True
    
    def set_default_api(self, api_id: str) -> bool:
        if self.get_api(api_id):
            self.config["default_api_id"] = api_id
            self.save_config()
            return True
        return False


class SessionManager:
    """会话管理器 - 支持持久化"""
    
    def __init__(self, config_manager: ConfigManager, database: Database):
        self.config_manager = config_manager
        self.database = database
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self, session_id: str, api_id: Optional[str] = None) -> Dict:
        api_config = None
        if api_id:
            api_config = self.config_manager.get_api(api_id)
        else:
            api_config = self.config_manager.get_default_api()
        
        if not api_config:
            raise ValueError("未找到可用的 API 配置，请先在设置中添加")
        
        messages = self.database.get_messages(session_id)
        
        session_data = {
            "id": session_id,
            "api_config": api_config,
            "messages": messages
        }
        
        self.sessions[session_id] = session_data
        logger.info(f"创建会话: {session_id} (API: {api_config.get('name')}, 已加载 {len(messages)} 条消息)")
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        conversation = self.database.get_conversation(session_id)
        if conversation:
            api_id = conversation.get('api_id')
            return self.create_session(session_id, api_id)
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"删除会话缓存: {session_id}")
        return True


config_manager = ConfigManager(CONFIG_FILE)
database = Database(DB_FILE)
persistent_memory = PersistentMemory(MEMORY_DB)
todo_manager = TodoManager(TODO_DB)
session_manager = SessionManager(config_manager, database)

from omni.agent_worker import WorkerManager
workers_manager = WorkerManager(WORKERS_DB)


app = FastAPI(
    title="OmniAgent Web",
    description="基于 MVP 的 Web Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    api_id: Optional[str] = None


class ApiConfigRequest(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None


@app.get("/")
async def root():
    frontend_path = Path(__file__).parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "OmniAgent Web Server", "status": "running"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "active_sessions": len(session_manager.sessions)
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id, request.api_id)
        
        api_id = request.api_id or config_manager.config.get("default_api_id")
        database.create_conversation(session_id, "新对话", api_id)
    
    api_config = session["api_config"]
    
    database.add_message(session_id, "user", request.message)
    
    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            
            output_queue = Queue()
            error_holder = {"error": None}
            full_response = {"text": ""}
            
            def run_engine():
                try:
                    engine = OmniEngine(
                        model=api_config.get("model", "gpt-4"),
                        provider=api_config.get("provider", "openai"),
                        api_key=api_config.get("api_key"),
                        base_url=api_config.get("base_url"),
                        stream=True,
                        max_iterations=config_manager.config.get("max_iterations", 50),
                        enable_shield=True,
                        enable_recovery=True,
                        quiet=True,
                    )
                    
                    original_print = print
                    
                    def custom_print(*args, **kwargs):
                        text = ' '.join(str(arg) for arg in args)
                        output_queue.put({"type": "content", "content": text + "\n"})
                    
                    import builtins
                    builtins.print = custom_print
                    
                    try:
                        capabilities = get_capabilities()
                        result = engine.execute(
                            task=request.message,
                            capabilities=capabilities
                        )
                        
                        full_response["text"] = result
                        output_queue.put({"type": "content", "content": f"\n\n{result}"})
                        
                    finally:
                        builtins.print = original_print
                    
                    output_queue.put({"type": "done"})
                    
                except Exception as e:
                    logger.error(f"执行错误: {e}", exc_info=True)
                    error_holder["error"] = str(e)
                    output_queue.put({"type": "error", "error": str(e)})
                    output_queue.put({"type": "done"})
            
            thread = Thread(target=run_engine, daemon=True)
            thread.start()
            
            while True:
                await asyncio.sleep(0.01)
                
                while not output_queue.empty():
                    msg = output_queue.get()
                    
                    if msg["type"] == "done":
                        if full_response["text"]:
                            database.add_message(session_id, "assistant", full_response["text"])
                            database.update_conversation(session_id)
                        return
                    
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                if not thread.is_alive() and output_queue.empty():
                    break
            
        except Exception as e:
            logger.error(f"流式响应错误: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/apis")
async def get_apis():
    config = config_manager.config.copy()
    
    if "apis" in config:
        config["apis"] = [
            {
                **api,
                "api_key": ("*" * 8 + api["api_key"][-4:] if api.get("api_key") and len(api["api_key"]) > 4 else "")
            }
            for api in config["apis"]
        ]
    
    return config


@app.post("/api/apis")
async def create_api(request: ApiConfigRequest):
    api_config = request.dict()
    api_id = config_manager.add_api(api_config)
    return {"id": api_id, "message": "API 配置已添加"}


@app.put("/api/apis/{api_id}")
async def update_api(api_id: str, request: ApiConfigRequest):
    updates = request.dict()
    success = config_manager.update_api(api_id, updates)
    
    if not success:
        raise HTTPException(status_code=404, detail="API 配置不存在")
    
    return {"message": "API 配置已更新"}


@app.delete("/api/apis/{api_id}")
async def delete_api(api_id: str):
    success = config_manager.delete_api(api_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API 配置不存在")
    
    return {"message": "API 配置已删除"}


@app.post("/api/apis/{api_id}/set-default")
async def set_default_api(api_id: str):
    success = config_manager.set_default_api(api_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API 配置不存在")
    
    return {"message": "默认 API 已设置"}


@app.get("/api/conversations")
async def get_conversations():
    """获取对话列表"""
    return database.get_conversations()


@app.post("/api/conversations")
async def create_conversation(title: str = "新对话", api_id: str = None):
    """创建新对话"""
    conversation_id = str(uuid.uuid4())
    api_id = api_id or config_manager.config.get("default_api_id")
    success = database.create_conversation(conversation_id, title, api_id)
    
    if success:
        return {"id": conversation_id, "title": title}
    else:
        raise HTTPException(status_code=500, detail="创建对话失败")


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    conversation = database.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    messages = database.get_messages(conversation_id)
    return {
        "conversation": conversation,
        "messages": messages
    }


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    success = database.delete_conversation(conversation_id)
    session_manager.delete_session(conversation_id)
    
    if success:
        return {"message": "对话已删除"}
    else:
        raise HTTPException(status_code=404, detail="对话不存在")


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, title: str):
    """更新对话标题"""
    success = database.update_conversation(conversation_id, title)
    
    if success:
        return {"message": "对话已更新"}
    else:
        raise HTTPException(status_code=404, detail="对话不存在")


@app.get("/api/cli-tools")
async def get_cli_tools():
    """获取所有 CLI 工具"""
    return database.get_cli_tools()


@app.post("/api/cli-tools")
async def add_cli_tool(
    name: str,
    usage: str,
    description: str,
    cli_path: str = "",
    category: str = "",
    default_args: str = ""
):
    """添加 CLI 工具"""
    success = database.add_cli_tool(name, usage, description, cli_path, category, default_args)
    
    if success:
        return {"message": "CLI 工具已添加"}
    else:
        raise HTTPException(status_code=500, detail="添加失败")


@app.put("/api/cli-tools/{tool_id}")
async def update_cli_tool(tool_id: int, **kwargs):
    """更新 CLI 工具"""
    success = database.update_cli_tool(tool_id, **kwargs)
    
    if success:
        return {"message": "CLI 工具已更新"}
    else:
        raise HTTPException(status_code=404, detail="工具不存在")


@app.delete("/api/cli-tools/{tool_id}")
async def delete_cli_tool(tool_id: int):
    """删除 CLI 工具"""
    success = database.delete_cli_tool(tool_id)
    
    if success:
        return {"message": "CLI 工具已删除"}
    else:
        raise HTTPException(status_code=404, detail="工具不存在")


# ============== 员工管理 API ==============

@app.get("/api/workers")
async def list_workers(include_disabled: bool = False):
    """获取所有员工列表"""
    workers = workers_manager.list_workers(include_disabled=include_disabled)
    return {
        "workers": [w.to_dict() for w in workers],
        "statistics": workers_manager.get_statistics()
    }


@app.get("/api/workers/current")
async def get_current_worker():
    """获取当前员工"""
    worker = workers_manager.get_current_worker()
    if not worker:
        raise HTTPException(status_code=404, detail="未设置当前员工")
    return worker.to_dict()


@app.get("/api/workers/{worker_id}")
async def get_worker(worker_id: str):
    """获取单个员工"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    return worker.to_dict()


@app.post("/api/workers")
async def create_worker(
    name: str,
    prompt: str,
    cli_tools: list = [],
    model: str = "gpt-4",
    provider: str = "openai",
    metadata: dict = {}
):
    """创建新员工"""
    try:
        worker = workers_manager.create_worker(
            name=name,
            prompt=prompt,
            cli_tools=cli_tools,
            model=model,
            provider=provider,
            metadata=metadata
        )
        return {
            "success": True,
            "worker": worker.to_dict()
        }
    except Exception as e:
        logger.error(f"创建员工失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/workers/{worker_id}")
async def update_worker(worker_id: str, **kwargs):
    """更新员工"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    # 过滤 None 值
    updates = {k: v for k, v in kwargs.items() if v is not None}
    
    try:
        success = workers_manager.update_worker(worker_id=worker_id, **updates)
        if not success:
            raise HTTPException(status_code=500, detail="更新失败")
        
        updated_worker = workers_manager.get_worker(worker_id)
        return {
            "success": True,
            "worker": updated_worker.to_dict()
        }
    except Exception as e:
        logger.error(f"更新员工失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workers/{worker_id}")
async def delete_worker(worker_id: str):
    """删除员工"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    if worker.is_default:
        raise HTTPException(status_code=400, detail="主员工不可删除")
    
    try:
        success = workers_manager.delete_worker(worker_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"删除员工失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workers/{worker_id}/set-current")
async def set_current_worker(worker_id: str):
    """设置当前员工"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    try:
        success = workers_manager.set_current_worker(worker_id)
        if not success:
            raise HTTPException(status_code=500, detail="设置失败")
        
        return {
            "success": True,
            "worker": worker.to_dict()
        }
    except Exception as e:
        logger.error(f"设置当前员工失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workers/{worker_id}/tools")
async def add_tool_to_worker(worker_id: str, tool_id: str):
    """为员工添加工具"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    try:
        success = workers_manager.add_tool_to_worker(worker_id, tool_id)
        if not success:
            raise HTTPException(status_code=400, detail="工具已存在")
        
        updated_worker = workers_manager.get_worker(worker_id)
        return {
            "success": True,
            "worker": updated_worker.to_dict()
        }
    except Exception as e:
        logger.error(f"添加工具失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workers/{worker_id}/tools/{tool_id}")
async def remove_tool_from_worker(worker_id: str, tool_id: str):
    """从员工移除工具"""
    worker = workers_manager.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    try:
        success = workers_manager.remove_tool_from_worker(worker_id, tool_id)
        if not success:
            raise HTTPException(status_code=400, detail="工具不存在")
        
        updated_worker = workers_manager.get_worker(worker_id)
        return {
            "success": True,
            "worker": updated_worker.to_dict()
        }
    except Exception as e:
        logger.error(f"移除工具失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workers/statistics")
async def get_workers_statistics():
    """获取员工统计信息"""
    return workers_manager.get_statistics()


@app.get("/api/files/{filename}")
async def download_file(filename: str):
    """下载文件"""
    from fastapi.responses import FileResponse
    import os
    
    # 安全检查：防止路径遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    
    # 文件存储目录
    files_dir = Path(__file__).parent.parent / "files"
    files_dir.mkdir(exist_ok=True)
    
    file_path = files_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 OmniAgent Web Server 启动中...")
    print("="*70)
    print(f"\n📍 访问地址: http://localhost:8080")
    print(f"⚙️  设置页面: http://localhost:8080/settings.html")
    print(f"\n💡 提示：首次使用请访问设置页面配置 API Key\n")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
