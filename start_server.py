#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OmniAgent Server 启动脚本
"""

import sys
import logging
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """打印启动横幅"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  OmniAgent - 生产级 AI Agent 系统                                ║
║  多员工调用 | 上下文压缩 | 持久化记忆 | 任务管理                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def check_dependencies():
    """检查依赖"""
    logger.info("检查依赖...")
    
    required = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'openai': 'OpenAI',
        'pydantic': 'Pydantic',
    }
    
    missing = []
    for module, name in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    
    if missing:
        logger.error(f"缺少依赖: {', '.join(missing)}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("依赖检查通过 ✓")
    return True


def init_database():
    """初始化数据库"""
    logger.info("初始化数据库...")
    
    db_dir = current_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"数据库目录: {db_dir}")
    logger.info("数据库初始化完成 ✓")


def start_server(host='0.0.0.0', port=8080):
    """启动服务器"""
    import uvicorn
    from web_server import app
    
    logger.info(f"启动服务器: http://{host}:{port}")
    logger.info(f"API 文档: http://{host}:{port}/docs")
    logger.info(f"工作目录: {current_dir}")
    
    print("\n" + "="*70)
    print(f"  服务器地址: http://localhost:{port}")
    print(f"  API 文档:   http://localhost:{port}/docs")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


def main():
    """主函数"""
    print_banner()
    
    if not check_dependencies():
        sys.exit(1)
    
    init_database()
    
    try:
        start_server(host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        logger.info("\n服务器已停止")
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
