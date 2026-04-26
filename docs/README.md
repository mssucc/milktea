# AI聊天框项目文档

<!-- BEGIN_MODULE: 文档索引 -->
<!-- BEGIN_TOC -->
## 目录
1. [架构文档](#architecture-docs)
2. [API文档](#api-docs)  
3. [数据库设计](#database-docs)
4. [部署配置](#deployment-docs)
5. [开发指南](#development-docs)
6. [文档搜索指南](#search-guide)
7. [开发场景指南](#development-scenarios)
8. [文档维护](#documentation-maintenance)
<!-- END_TOC -->

<!-- BEGIN_SECTION: architecture-docs -->
## 架构文档
1. [前端架构](architecture/frontend.md) - Vue 3组件结构、状态管理、UI设计
2. [后端架构](architecture/backend.md) - FastAPI结构、数据库层、任务调度  
3. [复习系统架构](architecture/review-system.md) - **重点**：结构化复习系统设计
<!-- END_SECTION: architecture-docs -->

<!-- BEGIN_SECTION: api-docs -->
## API文档
4. [API概览](api/overview.md) - REST API设计和约定
5. [聊天API](api/chat-api.md) - 流式聊天端点
6. [图谱API](api/graph-api.md) - 知识图谱查询
7. [复习API](api/review-api.md) - 复习系统相关端点
<!-- END_SECTION: api-docs -->

<!-- BEGIN_SECTION: database-docs -->
## 数据库设计
8. [数据模型](database/models.md) - SQLAlchemy模型定义
9. [迁移策略](database/migrations.md) - 数据库变更管理
<!-- END_SECTION: database-docs -->

<!-- BEGIN_SECTION: deployment-docs -->
## 部署配置
10. [环境设置](deployment/setup.md) - 开发和生产环境配置
11. [运维维护](deployment/maintenance.md) - 日常运维任务
<!-- END_SECTION: deployment-docs -->

<!-- BEGIN_SECTION: development-docs -->
## 开发指南
12. [前端开发流程](development/frontend-workflow.md) - Vue开发最佳实践
13. [后端开发流程](development/backend-workflow.md) - Python开发指南
14. [测试策略](development/testing.md) - 单元和集成测试
<!-- END_SECTION: development-docs -->

<!-- BEGIN_SECTION: search-guide -->
## 文档搜索指南

### 标记系统规范
所有技术文档必须使用以下标记系统：

#### 1. 模块标记 (文档级)
```markdown
<!-- BEGIN_MODULE: 模块名 -->
文档完整内容...
<!-- END_MODULE: 模块名 -->
```

#### 2. 目录标记 (必须在文档开头)
```markdown
<!-- BEGIN_TOC -->
## 目录
1. [章节1](#section-1)
2. [章节2](#section-2)
...
<!-- END_TOC -->
```

#### 3. 章节标记 (章节级)
```markdown
<!-- BEGIN_SECTION: section-1 -->
## 1. 章节标题
章节内容...
<!-- END_SECTION: section-1 -->
```

### 快速定位方法

#### 查找模块内容
```bash
# 查找模块起始行
start=$(grep -n "BEGIN_MODULE: 模块名" file.md | cut -d: -f1)

# 查找模块结束行
end=$(grep -n "END_MODULE: 模块名" file.md | cut -d: -f1)

# 读取模块内容
sed -n "${start},${end}p" file.md
```

#### 查找章节内容
```bash
# 查找章节起始行
start=$(grep -n "BEGIN_SECTION: 章节名" file.md | cut -d: -f1)

# 查找章节结束行  
end=$(grep -n "END_SECTION: 章节名" file.md | cut -d: -f1)

# 读取章节内容
sed -n "${start},${end}p" file.md
```

#### 查找目录
```bash
# 查找目录起始行
start=$(grep -n "BEGIN_TOC" file.md | cut -d: -f1)

# 查找目录结束行
end=$(grep -n "END_TOC" file.md | cut -d: -f1)

# 读取目录
sed -n "${start},${end}p" file.md
```

### 标记命名规范
1. **模块名**: 使用英文，描述文档主题，如 `backend-architecture`, `review-system`
2. **章节名**: 使用英文连字符，如 `design-overview`, `data-structures`
3. **一致性**: 模块和章节名在文档内必须唯一
<!-- END_SECTION: search-guide -->

<!-- BEGIN_SECTION: development-scenarios -->
## 开发场景指南

### 复习系统开发
如果正在进行复习系统相关开发，按此顺序查阅：

1. **架构设计** → `docs/architecture/review-system.md` (`BEGIN_MODULE: review-system`)
2. **API接口** → `docs/api/review-api.md` (`BEGIN_MODULE: review-api`)  
3. **数据模型** → `docs/database/models.md` (`BEGIN_MODULE: database-models`)

### 前端开发
1. **组件结构** → `docs/architecture/frontend.md` (`BEGIN_MODULE: frontend-architecture`)
2. **开发流程** → `docs/development/frontend-workflow.md` (`BEGIN_MODULE: frontend-workflow`)

### 后端开发
1. **应用架构** → `docs/architecture/backend.md` (`BEGIN_MODULE: backend-architecture`)
2. **开发流程** → `docs/development/backend-workflow.md` (`BEGIN_MODULE: backend-workflow`)
<!-- END_SECTION: development-scenarios -->

<!-- BEGIN_SECTION: documentation-maintenance -->
## 文档维护

### 更新原则
1. **创建新文档**：必须包含BEGIN_MODULE/END_MODULE标记
2. **添加目录**：必须在文档开头包含BEGIN_TOC/END_TOC标记
3. **组织章节**：重要章节使用BEGIN_SECTION/END_SECTION标记
4. **保持一致性**：模块名和章节名必须符合命名规范

### 一致性检查
定期运行以下命令检查标记完整性：

```bash
# 检查所有文档是否都有MODULE标记
find docs -name "*.md" -exec grep -l "BEGIN_MODULE:" {} \;

# 检查所有文档是否都有TOC标记
find docs -name "*.md" -exec grep -l "BEGIN_TOC" {} \;

# 检查标记配对
for file in docs/**/*.md; do
    begin_count=$(grep -c "BEGIN_MODULE:" "$file")
    end_count=$(grep -c "END_MODULE:" "$file")
    if [ "$begin_count" != "$end_count" ]; then
        echo "标记不配对: $file (BEGIN: $begin_count, END: $end_count)"
    fi
done
```

### 文档模板
创建新文档时使用以下模板：

```markdown
# 文档标题

<!-- BEGIN_MODULE: 模块名 -->
<!-- BEGIN_TOC -->
## 目录
1. [章节1](#section-1)
2. [章节2](#section-2)
...
<!-- END_TOC -->

<!-- BEGIN_SECTION: section-1 -->
## 1. 章节标题
章节内容...
<!-- END_SECTION: section-1 -->

<!-- BEGIN_SECTION: section-2 -->
## 2. 章节标题
章节内容...
<!-- END_SECTION: section-2 -->
<!-- END_MODULE: 模块名 -->
```
<!-- END_SECTION: documentation-maintenance -->
<!-- END_MODULE: 文档索引 -->

---

*文档标记系统最后更新：2026-04-15*