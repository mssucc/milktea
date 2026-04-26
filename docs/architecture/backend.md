# 后端架构设计

<!-- BEGIN_MODULE: backend-architecture -->
<!-- BEGIN_TOC -->
## 目录
1. [项目结构](#project-structure)
2. [FastAPI应用](#fastapi-application)
3. [数据库层](#database-layer)
4. [LLM集成](#llm-integration)
5. [知识图谱](#knowledge-graph)
6. [任务调度](#task-scheduling)
7. [配置管理](#configuration-management)
8. [错误处理](#error-handling)
<!-- END_TOC -->

<!-- BEGIN_SECTION: project-structure -->
## 1. 项目结构

```
agent/
├── backend/
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 应用配置
│   ├── routes/              # API路由
│   │   ├── chat.py          # 聊天相关端点
│   │   ├── graph.py         # 知识图谱端点
│   │   ├── review.py        # 复习系统端点
│   │   └── models.py        # 模型管理端点
│   ├── database/            # 数据库层
│   │   ├── session.py       # 数据库会话管理
│   │   ├── model.py         # SQLAlchemy模型
│   │   └── crud.py          # 数据库操作函数
│   ├── llm/                 # LLM集成
│   │   ├── chat_handler.py  # 对话处理
│   │   └── model_registry.py # 模型配置
│   ├── graph_db/            # Neo4j集成
│   │   ├── neo4j_client.py  # Neo4j连接
│   │   ├── knowledge_extractor.py # 实体关系提取
│   │   └── graph_generator.py # 图谱数据生成
│   ├── utils/               # 工具模块
│   │   ├── summarizer.py    # 文本总结
│   │   ├── review_generator.py # 复习生成（旧）
│   │   └── structured_review_generator.py # 结构化复习生成（新）
│   ├── scheduler/           # 任务调度
│   │   ├── __init__.py      # 调度器初始化
│   │   ├── config.py        # 调度配置
│   │   ├── job_store.py     # 作业存储
│   │   └── task_executor.py # 任务执行器
│   ├── tasks/               # 后台任务
│   │   └── review_generation.py # 复习生成任务
│   └── minitest/            # 测试工具
│       ├── clear_sqlite.py  # 清空SQLite
│       ├── clear_neo4j.py   # 清空Neo4j
│       └── 各种测试脚本
└── pyproject.toml           # Python项目配置
```
<!-- END_SECTION: project-structure -->

<!-- BEGIN_SECTION: fastapi-application -->
## 2. FastAPI应用

### 2.1 应用初始化 (main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Chatbox API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 前端开发地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(models.router, prefix="/api", tags=["models"])

# 数据库初始化
@app.on_event("startup")
def startup_event():
    init_database()
    init_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()
```

### 2.2 路由组织
- **模块化路由**：每个功能领域有独立的路由文件
- **统一前缀**：所有API使用`/api`前缀
- **OpenAPI文档**：自动生成Swagger UI和ReDoc文档
<!-- END_SECTION: fastapi-application -->

<!-- BEGIN_SECTION: database-layer -->
## 3. 数据库层

### 3.1 SQLAlchemy配置
```python
# database/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """依赖注入数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3.2 核心数据模型
```python
# database/model.py
class Session(Base):
    """会话表"""
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, index=True)  # session_id
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="session")
    review_data = relationship("ReviewData", back_populates="session", uselist=False)

class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)  # "user"或"assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ReviewData(Base):
    """复习数据表（新结构化格式）"""
    __tablename__ = "review_data"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), unique=True, index=True)
    review_groups = Column(JSON)  # 结构化分组数据
    aggregated_summary = Column(Text)  # 总体总结
    generation_status = Column(String, default="pending")
    generated_at = Column(DateTime)
    expires_at = Column(DateTime)  # 缓存过期时间
```

### 3.3 CRUD操作 (crud.py)
```python
def create_session(db: Session, session_id: str):
    """创建新会话"""
    db_session = Session(id=session_id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_messages_by_session(db: Session, session_id: str):
    """获取会话消息"""
    return db.query(Message).filter(Message.session_id == session_id).all()

def save_review_data(db: Session, session_id: str, review_data: dict):
    """保存复习数据"""
    # 创建或更新ReviewData记录
    record = db.query(ReviewData).filter(ReviewData.session_id == session_id).first()
    if record:
        # 更新现有记录
        record.review_groups = review_data.get("review_groups", [])
        record.aggregated_summary = review_data.get("aggregated_summary", "")
        record.generation_status = "completed"
        record.generated_at = datetime.utcnow()
        record.expires_at = datetime.utcnow() + timedelta(hours=24)
    else:
        # 创建新记录
        record = ReviewData(
            session_id=session_id,
            review_groups=review_data.get("review_groups", []),
            aggregated_summary=review_data.get("aggregated_summary", ""),
            generation_status="completed",
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(record)
    
    db.commit()
    return record
```
<!-- END_SECTION: database-layer -->

<!-- BEGIN_SECTION: llm-integration -->
## 4. LLM集成

### 4.1 前端驱动配置
**核心设计**：API配置由前端管理，后端仅作为代理

```python
# llm/chat_handler.py
async def stream_chat_response(messages, api_key=None, base_url=None, model=None):
    """流式聊天响应"""
    # 使用前端提供的配置，或回退到环境变量
    final_api_key = api_key or os.getenv("OPENAI_API_KEY")
    final_base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    final_model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # 创建OpenAI客户端
    client = AsyncOpenAI(
        api_key=final_api_key,
        base_url=final_base_url
    )
    
    # 流式响应
    stream = await client.chat.completions.create(
        model=final_model,
        messages=messages,
        stream=True
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### 4.2 模型注册表
```python
# llm/model_registry.py
MODEL_REGISTRY = {
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "max_tokens": 4096,
        "provider": "openai"
    },
    "gpt-4": {
        "name": "GPT-4",
        "max_tokens": 8192,
        "provider": "openai"
    },
    "claude-3-haiku": {
        "name": "Claude 3 Haiku",
        "max_tokens": 4096,
        "provider": "anthropic"
    }
}
```

### 4.3 结构化复习生成器
```python
# utils/structured_review_generator.py
class StructuredReviewGenerator:
    """使用单个prompt生成结构化复习数据"""
    
    def generate(self, conversation_text, api_config=None):
        """生成知识卡片和选择题"""
        prompt = self._build_prompt(conversation_text)
        llm_response = self._call_llm(prompt, api_config)
        return self._parse_response(llm_response)
```
<!-- END_SECTION: llm-integration -->

<!-- BEGIN_SECTION: knowledge-graph -->
## 5. 知识图谱

### 5.1 Neo4j客户端
```python
# graph_db/neo4j_client.py
class Neo4jClient:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def extract_entities_relations(self, text, session_id):
        """从文本中提取实体和关系"""
        # 使用LLM或NLP工具提取
        # 存储到Neo4j
        pass
    
    def get_graph_data(self, session_id=None):
        """获取图谱数据用于前端可视化"""
        # 查询Neo4j，转换为前端格式
        pass
    
    def get_top_entities_by_mention_count(self, days=2, limit=20):
        """获取提及次数最多的实体"""
        query = """
        MATCH (e:Entity)
        WHERE e.last_mentioned >= datetime() - duration({days: $days})
        RETURN e.name AS name, e.mention_count AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        return self._execute_query(query, days=days, limit=limit)
```

### 5.2 知识提取流程
1. 用户发送消息 → 保存到SQLite
2. 后台异步提取实体和关系 → 存储到Neo4j
3. 前端通过`/api/graph/{session_id}`查询图谱数据
<!-- END_SECTION: knowledge-graph -->

<!-- BEGIN_SECTION: task-scheduling -->
## 6. 任务调度

### 6.1 APScheduler集成
```python
# scheduler/config.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

scheduler = BackgroundScheduler()

def init_scheduler():
    """初始化调度器"""
    job_store = SQLAlchemyJobStore(url="sqlite:///./scheduler.db")
    scheduler.add_jobstore(job_store)
    
    # 添加定期任务
    scheduler.add_job(
        execute_scheduled_scan,
        'interval',
        hours=12,
        id='review_scan',
        replace_existing=True
    )
    
    scheduler.start()
```

### 6.2 复习生成任务
```python
# tasks/review_generation.py
async def generate_integrated_review_background(limit=10, days=7, force_refresh=False):
    """后台生成集成复习数据"""
    # 1. 基于高频节点选择会话
    session_ids = crud.select_sessions_for_review_generation(limit, days)
    
    # 2. 获取会话内容
    sessions_data = []
    for session_id in session_ids:
        messages = crud.get_messages_by_session(db, session_id)
        sessions_data.append({
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages)
        })
    
    # 3. 聚合和生成
    review_data = await aggregate_and_generate_review(sessions_data)
    
    # 4. 存储结果
    crud.save_integrated_review(db, review_data)
```
<!-- END_SECTION: task-scheduling -->

<!-- BEGIN_SECTION: configuration-management -->
## 7. 配置管理

### 7.1 环境变量 (.env)
```env
# OpenAI配置（默认值，可被前端覆盖）
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置
DATABASE_URL=sqlite:///./chat.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:5173

# 复习系统配置
REVIEW_CACHE_TTL_HOURS=24
REVIEW_GENERATION_TIMEOUT=300
REVIEW_SCAN_FREQUENCY_HOURS=12
```

### 7.2 配置加载 (config.py)
```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_base_url: str = "https://api.openai.com/v1"
    database_url: str = "sqlite:///./chat.db"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    class Config:
        env_file = ".env"

settings = Settings()
```
<!-- END_SECTION: configuration-management -->

<!-- BEGIN_SECTION: error-handling -->
## 8. 错误处理

### 8.1 统一错误响应
```python
from fastapi import HTTPException

def handle_llm_error(e: Exception):
    """处理LLM相关错误"""
    error_msg = str(e)
    if "insufficient_quota" in error_msg:
        raise HTTPException(402, "API配额不足")
    elif "invalid_api_key" in error_msg:
        raise HTTPException(401, "API密钥无效")
    else:
        raise HTTPException(500, f"LLM服务错误: {error_msg}")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """全局HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

### 8.2 日志配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backend.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```
<!-- END_SECTION: error-handling -->

## 相关文档
- [复习系统架构](review-system.md)
- [前端架构](frontend.md)
- [API文档](../api/overview.md)

---
<!-- END_MODULE: backend-architecture -->

*文档最后更新：2026-04-15*