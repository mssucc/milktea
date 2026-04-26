# AI Chatbox

一个支持知识图谱和结构化复习系统的 AI 聊天应用。

## 项目结构

```
milktea/
├── agent/                    # FastAPI 后端
│   ├── backend/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置（从 .env 读取）
│   │   ├── routes/          # API 路由
│   │   ├── database/        # SQLAlchemy 数据模型与 CRUD
│   │   ├── graph_db/        # Neo4j 知识图谱
│   │   ├── scheduler/       # APScheduler 后台任务
│   │   ├── tasks/           # 后台任务执行
│   │   └── minitest/        # 开发测试工具
│   ├── .env                 # 敏感配置（已 gitignore）
│   └── .env.example         # 配置模板
│
├── ai-chatbox-vue/          # Vue 3 前端
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── api/             # API 调用
│   │   └── styles/          # 样式
│   └── .env.development     # 前端开发配置
│
├── docs/                    # 架构文档
├── .gitignore
└── README.md
```

> **Powered by 麻衣学姐** — 项目的灵魂人物，点击学姐头像即可刷新复习内容。没有麻衣学姐的保佑，知识卡片和选择题都无法生成。

<h1 align="center">人活着就是为了樱岛麻衣</h1>
```

## 快速开始

### 前置要求

- Python 3.11+ + [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Neo4j 数据库（本地或云端）

### 1. 后端

```bash
cd agent

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API key 和 Neo4j 连接信息

# 启动服务
uv run python -m backend.main
```

后端默认运行在 `http://localhost:8000`。

### 2. 前端

```bash
cd ai-chatbox-vue

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端默认运行在 `http://localhost:5173`。

### 3. Neo4j（可选，用于知识图谱）

使用 Docker 启动本地 Neo4j：

```bash
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password neo4j:latest
```

然后在 `.env` 中配置 `NEO4J_PASSWORD`。

## 功能

### AI 对话

- 支持任何 OpenAI 兼容 API（DeepSeek、OpenAI、Ollama、LocalAI 等）
- 流式响应
- 模型切换（可在前端设置中配置）

### 知识图谱

- 对话中自动提取实体和关系
- 存入 Neo4j 图数据库
- 可视化展示实体关系网络
- 跨会话实体聚合与重要性评分

### 结构化复习系统

- 基于对话内容自动生成知识卡片和选择题
- 跨会话聚合复习
- 后台定时生成（APScheduler）
- 进度追踪与持久化

## 配置

所有敏感配置集中在 `agent/.env`，已加入 `.gitignore`。参考 `agent/.env.example` 获取配置项说明。

### 后端配置项

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite:///./chat.db` |
| `NEO4J_URI` | Neo4j 连接地址 | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 用户名 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码 | 必填 |
| `OPENAI_API_KEY` | API 密钥 | 可选（前端可覆盖） |
| `OPENAI_BASE_URL` | API 地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 默认模型 | `gpt-3.5-turbo` |
| `API_HOST` | 监听地址 | `0.0.0.0` |
| `API_PORT` | 监听端口 | `8000` |
| `FRONTEND_URL` | 前端地址（CORS） | `http://localhost:5173` |

### 前端配置项

编辑 `ai-chatbox-vue/.env.development`：

| 变量 | 说明 |
| --- | --- |
| `VITE_API_URL` | 后端 API 地址 |
| `VITE_ENABLE_GRAPH` | 启用知识图谱 |
| `VITE_ENABLE_REVIEW` | 启用复习系统 |
| `VITE_ENABLE_MODEL_SWITCHING` | 启用模型切换 |

## 数据清理

```bash
cd agent
uv run python -m backend.minitest.clear_sqlite     # 清空 SQLite
uv run python -m backend.minitest.clear_neo4j       # 清空 Neo4j
uv run python -m backend.minitest.clear_review_data # 仅清空复习数据
```

所有清理命令在删除前都会要求确认。
