# CLAUDE.md

<!-- BEGIN_MODULE: 项目指导 -->
<!-- BEGIN_TOC -->
## 目录
1. [项目概述](#project-overview)
2. [文档系统](#documentation-system)
3. [开发命令](#development-commands)
4. [重要事项](#important-notes)
5. [开发者指导](#developer-guidance)
<!-- END_TOC -->

## 项目概述

这是一个AI聊天框应用，包含：

- **AI对话功能** - 使用OpenAI兼容API（可通过前端配置）
- **模型切换能力** - 支持各种OpenAI兼容服务
- **二次元风格前端** - 动漫风格UI设计
- **知识图谱集成** - 使用Neo4j存储实体关系
- **结构化复习系统** - 基于会话内容生成知识卡片和选择题，支持跨会话聚合

应用包含两个主要组件：
1. **前端**: Vue 3 + TypeScript + Pinia + Vite + Tauri
2. **后端**: FastAPI + SQLAlchemy + Neo4j + OpenAI兼容API

## 文档系统

项目使用模块化文档系统，便于快速查阅和决策。所有技术文档位于 `docs/` 目录。

### 文档结构
```
docs/
├── README.md                    # 文档索引和搜索指南
├── architecture/                # 架构文档
│   ├── frontend.md             # 前端架构
│   ├── backend.md              # 后端架构
│   └── review-system.md        # 复习系统架构（重点）
├── api/                        # API文档
├── database/                   # 数据库设计
├── deployment/                 # 部署配置
└── development/                # 开发指南
```

### 文档搜索方法
所有技术文档使用标准化的标记系统，便于快速定位和读取特定部分。

#### 标记系统概述
每个文档包含三种标记：
1. **模块标记** (`BEGIN_MODULE: 模块名` / `END_MODULE: 模块名`) - 文档级封装
2. **目录标记** (`BEGIN_TOC` / `END_TOC`) - 必须在文档开头，包含目录
3. **章节标记** (`BEGIN_SECTION: 章节名` / `END_SECTION: 章节名`) - 章节级封装

#### 基本定位方法
- **查找标记位置**: 使用 `grep -n` 查找标记的起始和结束行
- **查看可用标记**: 使用 `grep -o` 查看文档中所有章节和模块
- **确定读取范围**: 根据起始和结束标记确定内容范围

#### 工作流程
1. **浏览文档结构**: 读取目录(`BEGIN_TOC`/`END_TOC`)了解组织
2. **定位感兴趣内容**: 查看可用章节列表
3. **读取特定部分**: 根据标记确定范围，读取所需内容

**完整搜索指南**: 详细实现方法、工具使用和示例请查阅 [docs/README.md](d:/Desktop/milktea/docs/README.md) (`BEGIN_SECTION: search-guide`)

### 重点文档
- **复习系统**: `docs/architecture/review-system.md` (`BEGIN_MODULE: review-system`)
- **后端架构**: `docs/architecture/backend.md` (`BEGIN_MODULE: backend-architecture`)
- **前端架构**: `docs/architecture/frontend.md` (`BEGIN_MODULE: frontend-architecture`)

## 架构概览

详细架构文档请查阅 `docs/architecture/` 目录：

### 后端架构
- **文档**: `docs/architecture/backend.md` (`BEGIN_MODULE: backend-architecture`)
- **要点**: FastAPI应用、SQLAlchemy数据库、Neo4j知识图谱、APScheduler任务调度
- **快速定位**: `grep -n "BEGIN_MODULE: backend-architecture" docs/architecture/backend.md`

### 前端架构  
- **文档**: `docs/architecture/frontend.md` (`BEGIN_MODULE: frontend-architecture`)
- **要点**: Vue 3 + Composition API、Pinia状态管理、动漫风格UI、流式聊天
- **快速定位**: `grep -n "BEGIN_MODULE: frontend-architecture" docs/architecture/frontend.md`

### 复习系统架构（重点）
- **文档**: `docs/architecture/review-system.md` (`BEGIN_MODULE: review-system`)
- **要点**: 结构化数据格式、知识深度优先聚合、单提示词生成、后台任务调度
- **快速定位**: `grep -n "BEGIN_MODULE: review-system" docs/architecture/review-system.md`

### 数据流概览
1. 用户发送消息 → 前端调用 `POST /api/chat/stream`
2. 后端流式响应，消息保存到SQLite
3. 后台提取实体关系存储到Neo4j
4. 定期扫描生成结构化复习（知识卡片+选择题）
5. 前端通过 `ReviewPanel.vue` 显示和交互

## 开发命令

### 一键启动 / 停止
```bash
# 一键启动前后端（后台运行，日志写入 logs/ 目录）
python start.py

# 停止所有服务
python stop.py
```

### 后端开发

```bash
cd agent
# 运行FastAPI服务器（热重载）
uv run python -m backend.main

# 使用特定主机/端口运行
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 安装依赖（如果pyproject.toml有变更）
uv sync
```

### 前端开发
```bash
cd ai-chatbox-vue
# 启动Vite开发服务器
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview

# Tauri桌面应用开发
npm run tauri dev
npm run tauri build

# 类型检查
npm run type-check
```

### 数据库和Neo4j管理
```bash
# 清空SQLite数据库
cd agent
uv run python ../minitest/clear_sqlite.py

# 清空Neo4j知识图谱
uv run python ../minitest/clear_neo4j.py

# 通过Docker本地运行Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# 访问Neo4j浏览器 http://localhost:7474
```

### 测试工具
```bash
# 测试API服务器
cd agent
uv run python ../minitest/test_server.py

# 检查Neo4j连接
uv run python ../minitest/test_neo4j.py

# 检查会话数据
uv run python ../minitest/check_session.py
```

## 环境配置

### 后端 (`agent/.env`)
```env
# OpenAI兼容API配置（默认值，可被前端覆盖）
OPENAI_API_KEY=  # 可选：OpenAI或兼容服务的API密钥
OPENAI_MODEL=gpt-3.5-turbo  # 默认模型
OPENAI_BASE_URL=https://api.openai.com/v1  # 可设置为其他OpenAI兼容API，使用在线api

# 数据库配置
DATABASE_URL=sqlite:///./chat.db
NEO4J_URI=bolt://localhost:7687  # 或 neo4j+s:// 用于云端
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:5173
```

### 前端 (`ai-chatbox-vue/.env.development`)
```env
VITE_API_URL=http://127.0.0.1:8000/api
VITE_APP_NAME=AI Chatbox
VITE_ENABLE_GRAPH=true
VITE_ENABLE_REVIEW=true
VITE_ENABLE_MODEL_SWITCHING=true
```

## 关键设计模式

详细设计模式请查阅架构文档：

- **流式聊天和状态管理**：参见前端架构文档 (`docs/architecture/frontend.md`)
- **动漫风格设计**：参见前端架构文档的样式设计章节
- **错误处理机制**：参见后端架构文档 (`docs/architecture/backend.md`)
- **API配置管理**：参见后端架构文档的LLM集成章节

**快速定位**：
- 前端设计模式：`grep -n "BEGIN_SECTION: styling-design" docs/architecture/frontend.md`
- 后端设计模式：`grep -n "BEGIN_SECTION: error-handling" docs/architecture/backend.md`

## 常见开发任务

详细开发流程和最佳实践请查阅 `docs/development/` 目录下的开发指南文档。关键开发任务包括：

1. **添加API端点**：参见后端开发流程文档
2. **创建前端组件**：参见前端开发流程文档
3. **调试技巧**：参见测试和调试相关文档

**快速查找**：开发文档使用相同的标记系统，可通过 `grep -n "BEGIN_MODULE:" docs/development/*.md` 查找可用文档。

## 注意事项

**依赖管理**：项目使用**UV**进行Python依赖管理（非pip）

**API兼容性**：支持任何OpenAI兼容服务（OpenAI、Ollama、LocalAI等）
- **Ollama配置**：运行`ollama serve`，前端`base_url`设置为`http://localhost:11434/v1`
- **API管理**：API配置通过前端设置管理，而非后端环境变量

**数据库**：Neo4j支持云端（Neo4j Aura）或本地Docker容器

**安全提示**：所有数据库清空工具在删除前都需要确认

## 重要事项

0. 当前项目的python环境是D:\Desktop\milktea\agent\.venv路径下的uv环境，开发平台为windows
1. 通过文档系统了解模块现状再修改
2. 不要做无意义的修改，抓住当前目标，不要过度设置debug输出，积极与开发者互动讨论
3. 不要为了证明自己存在而参与进行某一项修改
4. 让开发者管理前端后端的运行，因为在后台开启前端后端可能导致进程残留
5. 进行代码模块的修改前，首先进行充分的交流讨论，鼓励讨论交流，探讨更加优雅朴素合理的实现，避免反模式实现、过度设计
6. 当需要实现一个功能时，应当考虑与整体的关系，如果功能曾被是用过，则考虑是否该封装为函数/类来复用
7. 减少客套话输出，不要使用emoji，除非开发者要求
8. 面对bug修改，先考虑产生当前bug的原因是什么，不急于修复，如不能确定，则先输出可能情况，与开发者讨论，首先需要准确定位问题原因
9. 及时修改本文件
<!-- END_MODULE: 项目指导 -->
