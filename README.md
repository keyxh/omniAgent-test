# OmniAgent v001 - 测试版本

**⚠️ 重要提示：此版本未经测试，仅供临时存储和参考**

## 项目简介

OmniAgent 是一个大型 Agent 项目，采用 C/S（客户端/服务器）架构设计，具有商业化潜力。当前版本为测试版本，用于临时存储代码。

## 架构特点

- **C/S 架构**: FastAPI 后端 + Web 前端
- **多员工调用制**: 主员工协调、子员工执行的模式
- **生命周期管理**: 统一的资源管理接口
- **会话持久化**: 数据库存储支持服务重启后恢复

## 目录结构

```
agent/
├── omni/               # 核心 Agent 模块
│   ├── brain.py        # 主控制器
│   ├── engine.py       # 执行引擎
│   ├── lifecycle.py    # 生命周期管理
│   ├── memory.py       # 内存管理
│   ├── worker_delegation.py  # 员工委托系统
│   └── ...
├── engine/             # 工具引擎
│   ├── filesystem.py   # 文件系统操作
│   ├── shell.py        # Shell 命令执行
│   ├── search.py       # 搜索功能
│   └── ...
├── skills/             # 技能模块
├── frontend/           # Web 前端界面
├── db/                 # 数据库目录（运行时创建）
├── web_server.py       # Web 服务器入口
├── start_server.py     # 启动脚本
├── database.py         # 数据库管理
├── requirements.txt    # Python 依赖
└── run.py              # 运行入口
```

## 快速启动

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 配置 API:
复制 `config.example.json` 为 `config.json`，填入你的 API 配置

3. 启动服务:
```bash
python start_server.py
```

4. 访问界面:
打开浏览器访问 http://localhost:8000

## ⚠️ 注意事项

- **此版本未经测试**: 可能存在未知问题和 bug
- **仅供参考**: 代码结构可能需要调整
- **配置文件**: 需要手动配置 API 密钥
- **数据库**: 运行时会在 `db/` 目录创建数据库文件

## 依赖说明

主要依赖包括：
- FastAPI (Web 服务器)
- OpenAI SDK (API 调用)
- SQLite (数据库)
- Playwright (可选，浏览器自动化)

## 许可证

暂未确定

## 联系方式

如有问题请通过 GitHub Issues 反馈