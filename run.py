#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OmniAgent 启动脚本
一个命令启动所有服务
"""

import sys
import subprocess
import time
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def print_banner():
    print(f"""
{Colors.GREEN}╔{'═'*68}╗
║{Colors.BLUE}  OmniAgent - 生产级 AI Agent 系统                          {Colors.GREEN}║
║{Colors.BLUE}  员工系统 | 上下文压缩 | 持久化记忆 | 任务管理              {Colors.GREEN}║
╚{'═'*68}╝{Colors.END}
    """)

def check_dependencies():
    """检查依赖"""
    print(f"{Colors.YELLOW}📦 检查依赖...{Colors.END}")
    
    required = ['fastapi', 'uvicorn', 'pydantic']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"{Colors.RED}❌ 缺少依赖：{', '.join(missing)}{Colors.END}")
        print(f"{Colors.YELLOW}💡 请运行：pip install {' '.join(missing)}{Colors.END}")
        return False
    
    print(f"{Colors.GREEN}✅ 依赖检查通过{Colors.END}")
    return True

def start_server(host='0.0.0.0', port=8080):
    """启动 Web 服务器"""
    print(f"{Colors.BLUE}🚀 启动 OmniAgent Web Server...{Colors.END}")
    print(f"{Colors.YELLOW}📍 访问地址：http://localhost:{port}{Colors.END}")
    print(f"{Colors.YELLOW}👥 员工管理：http://localhost:{port}/workers.html{Colors.END}")
    print(f"{Colors.YELLOW}🔧 CLI 工具：http://localhost:{port}/cli-tools.html{Colors.END}")
    print(f"{Colors.YELLOW}⚙️  API 设置：http://localhost:{port}/settings.html{Colors.END}")
    print(f"{Colors.GREEN}✨ 按 Ctrl+C 停止服务{Colors.END}\n")
    
    # 启动 uvicorn
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'web_server:app',
        '--host', host,
        '--port', str(port),
        '--reload'
    ], cwd=Path(__file__).parent)

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 解析参数
    host = '0.0.0.0'
    port = 8080
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    # 启动服务器
    try:
        start_server(host, port)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 服务已停止{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}❌ 启动失败：{e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
