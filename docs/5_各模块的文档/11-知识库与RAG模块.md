# 知识库与 RAG 模块（knowledge）

## 1. 模块概述

### 1.1 定位

`knowledge` 模块负责管理 ASA 系统的安全知识库，并提供 RAG（Retrieval-Augmented Generation，检索增强生成）检索能力。模块涵盖知识条目录入、向量化、语义检索、检索记录追踪和检索效果分析，是 `code_analyst` 和 `vulnerability_verifier` 两个 AI 角色的核心增强能力。

知识库按来源和用途划分为四个子库：漏洞模式库、安全规范库、修复建议库和历史评估库。所有知识条目与检索记录以 PostgreSQL + pgvector 统一存储，不引入独立向量数据库。

### 1.2 设计依据

- `docs/1_PRD/自动化安全评估系统-PRD.md`
- `docs/3_概要设计/自动化安全评估系统-概要设计总纲.md` — 第 3.4 节（RAG 分析技术）、第 5.2 节（knowledge 模块）、第 6.1 节（支撑表）
- `docs/4_开发规范/API接口文档.md` — 第 8 章（知识库接口）
- `docs/4_开发规范/数据库/数据库设计.md` — `knowledge_entries`、`knowledge_retrievals` 表设计
- `docs/5_各模块的文档/03-调度与AI角色模块.md` — 第 7 章（RAG 知识检索）

### 1.3 职责边界

| 职责 | 说明 |
| --- | --- |
| 知识条目管理 | 创建、编辑、审核（draft → active）、禁用和删除知识条目 |
| 向量化生成 | 条目激活时异步调用 Embedding 模型生成向量 |
| 语义检索 | 接受查询文本 → Embedding 向量化 → pgvector ANN 检索 → 重排序 → 返回结果 |
| 检索记录 | 每次 RAG 检索写入 `knowledge_retrievals`，含项目、阶段、查询摘要和召回条目 |
| 检索效果分析 | 按项目/阶段/任务聚合检索命中率和角色采纳率 |
| 知识沉淀 | 报告阶段自动沉淀验证通过的漏洞特征和修复方案（draft 状态，待管理员审核） |

**不负责：** AI 角色的上下文组装和 Prompt 注入——由 `agents` 模块的 `ContextBuilder` 负责；Embedding 模型的 HTTP 调用——由 `EmbeddingPort` 适配层统一封装；pgvector 索引维护——属于运维侧 DBA 职责，本模块只使用。

## 2. 架构与依赖

### 2.1 涉及的数据库表

| 表 | 角色 |
| --- | --- |
| `knowledge_entries` | 知识条目主表：文本内容、子库分类、语言/框架标签、风险等级、启用状态和 pgvector 向量 |
| `knowledge_retrievals` | 检索追踪表：每次 RAG 检索的项目、阶段、任务、查询文本、召回条目和相似度分数 |
| `audit_logs` | 条目创建/编辑/审核/删除操作审计 |

### 2.2 涉及的 API 接口

| 接口 | 方法 | URL | 认证 |
| --- | --- | --- | --- |
| 查询知识条目列表 | `GET` | `/api/v1/knowledge/entries` | Cookie，admin 可见全部状态，user 仅见 active |
| 创建知识条目 | `POST` | `/api/v1/knowledge/entries` | Cookie + CSRF，仅 admin |
| 查询知识条目详情 | `GET` | `/api/v1/knowledge/entries/{entry_id}` | Cookie |
| 更新知识条目 | `PUT` | `/api/v1/knowledge/entries/{entry_id}` | Cookie + CSRF，仅 admin |
| 删除知识条目 | `DELETE` | `/api/v1/knowledge/entries/{entry_id}` | Cookie + CSRF，仅 admin |
| 语义检索知识库 | `POST` | `/api/v1/knowledge/search` | Cookie，外部验证/管理员手动测试 |
| 查询项目检索历史 | `GET` | `/api/v1/projects/{project_id}/knowledge/retrievals` | Cookie，项目权限 |

### 2.3 上游依赖

```text
调用方                        knowledge 模块暴露的接口
─────────────────────────────────────────────────────
agents/ContextBuilder   →     RAGRetriever.retrieve(context, role, stage)
agents/search_security_knowledge tool → RAGRetriever.retrieve(context, ...)
scheduler（阶段切换）    →     KnowledgeService.get_stage_context(project, stage)
Celery 异步任务         →     EmbeddingService.generate_embedding(entry_id)
API Router             →     KnowledgeService CRUD + SearchService
```

### 2.4 下游依赖

```text
knowledge 模块依赖                说明
─────────────────────────────────────────────────────
PostgreSQL + pgvector         向量存储和 ANN 检索
EmbeddingPort（OpenAI 兼容）   文本 → 向量（默认 1536 维）
audit 模块                    审计日志记录
domain_events                 条目状态变更事件发布（可选）
```

## 3. 领域模型

### 3.1 知识条目实体

```text
KnowledgeEntry（聚合根）
├── id: UUID
├── title: str                         # 标题，1-255 字符
├── content_text: str                  # Markdown 正文
├── content_summary: str?              # 正文摘要（自动生成，≤500 字符）
├── knowledge_type: enum               # vulnerability_pattern | security_standard
│                                      #   | remediation_advice | historical_assessment
├── language: str?                     # 逗号分隔，如 "python,java,go"
├── framework: str?                    # 逗号分隔，如 "django,spring,gin"
├── risk_level: enum?                  # critical | high | medium | low | info
├── tags: str[]                        # 检索标签，无重复
├── entry_status: enum                 # draft | active | disabled
├── embedding: vector(1536)?           # pgvector 向量字段（draft 条目为 NULL）
├── source_type: enum                  # manual | external_import | auto_deposit
├── source_url: str?                   # 外部来源 URL
├── version: int                       # 编辑版本号，从 1 开始递增
├── created_by: UUID                   # 创建者 users.id
├── reviewed_by: UUID?                 # 审核者 users.id（draft → active 时记录）
├── reviewed_at: datetime?
├── created_at: datetime
└── updated_at: datetime
```

### 3.2 检索记录实体

```text
KnowledgeRetrieval（追加型记录）
├── id: BIGINT IDENTITY
├── project_id: UUID                   # 检索所属项目
├── stage_id: UUID?                    # 检索所属阶段
├── worker_task_id: UUID?              # 触发检索的角色任务
├── retrieval_type: enum               # stage_pre | role_pre | tool_triggered
├── query_text: str                    # 脱敏后的检索查询文本
├── query_embedding: vector(1536)?     # 查询向量（可选保留，用于检索质量分析）
├── filter_language: str?              # 检索时的语言过滤条件
├── filter_knowledge_types: str[]?     # 检索时的子库过滤条件
├── top_k: int                         # 请求的召回数量
├── retrieved_entries: jsonb           # [{entry_id, title, similarity, rank}] 实际召回条目
├── retrieval_duration_ms: int?        # 检索耗时（毫秒）
├── created_at: datetime
```

### 3.3 业务规则

| 规则 | 说明 | 实现 |
| --- | --- | --- |
| 三步生命周期 | draft（待审核，无向量）→ active（已审核，有向量，参与检索）→ disabled（已禁用，保留向量，不参与检索） | 状态机 |
| 向量延迟生成 | 创建时 entry_status=draft 不生成向量；管理员审核通过将状态改为 active 后，异步任务生成向量 | Celery 任务 |
| 内容变更触发重新向量化 | `content_text` 或 `knowledge_type` 变更且当前为 active 时，自动触发异步重新向量化 | 应用层钩子 |
| 禁用的条目不参与检索 | `entry_status = 'disabled'` 的条目保留数据但 `WHERE entry_status = 'active'` 过滤 | 查询条件 |
| 删除不可恢复 | 前端需二次确认；`knowledge_retrievals.retrieved_entries` 保留已删除条目的 ID 和分数 | 软引用 |
| 自动沉淀条目需审核 | 报告阶段自动创建的条目 status=draft、source_type=auto_deposit，必须管理员审核后激活 | 默认值 + 校验 |
| 检索降级非阻塞 | Embedding 不可用时角色继续执行，不中断分析流程 | 异常捕获 |
| 向量维度一致性 | Worker 启动时校验 Embedding 模型输出维度与 `knowledge_entries.embedding` 列定义一致 | 启动校验 |

### 3.4 知识条目状态机

```text
        ┌─────────┐     管理员审核       ┌────────┐    管理员禁用    ┌──────────┐
        │  draft  │ ─────────────────→  │ active │ ─────────────→ │ disabled │
        └─────────┘                     └────────┘                └──────────┘
             │                               │                         │
             │ 管理员删除                     │ 管理员删除               │ 管理员删除
             ▼                               ▼                         ▼
          [删除]                          [删除]                     [删除]

  draft → active: 异步任务生成 Embedding 向量，写入 reviewed_by/reviewed_at
  active → disabled: 立即生效，从检索结果中排除；可重新激活为 active（已有向量则无需重新生成）
  disabled → active: 若向量仍存在则直接激活；若向量为空则触发异步生成
  active 条目内容变更: 自动触发异步重新向量化
```

### 3.5 领域异常

| 异常 | HTTP 状态 | 业务码 |
| --- | --- | --- |
| `KnowledgeEntryNotFound` | 404 | `KNOWLEDGE_ENTRY_NOT_FOUND` |
| `KnowledgeEntryAlreadyExists` | 409 | `KNOWLEDGE_ENTRY_ALREADY_EXISTS` |
| `InvalidKnowledgeType` | 422 | `VALIDATION_ERROR` |
| `EmbeddingDimensionMismatch` | — | Fatal Error（Worker 启动失败） |
| `EmbeddingTimeout` | — | 降级处理（角色继续，记录 warning） |
| `AdminRequired` | 403 | `ADMIN_REQUIRED` |

## 4. 核心流程

### 4.1 知识条目创建与激活

```text
POST /api/v1/knowledge/entries
  │
  ├── 1. 校验 CSRF Token + role='admin'
  ├── 2. 校验请求体（title/content_text/knowledge_type 必填）
  ├── 3. 事务写入：
  │     ├── INSERT INTO knowledge_entries (entry_status='draft', version=1)
  │     ├── 写入 audit_logs（action='knowledge_entry_created'）
  │     └── 提交事务
  └── 4. 返回 201 + 条目详情（不含 embedding）

管理员审核激活（通过 PUT 接口将 entry_status 改为 'active'）：
  │
  ├── 1. 校验当前 entry_status 允许转换
  ├── 2. 事务写入：
  │     ├── UPDATE entry_status='active', reviewed_by=..., reviewed_at=NOW()
  │     └── 写入 audit_logs（action='knowledge_entry_activated'）
  ├── 3. 提交事务后投递异步任务：
  │     └── Celery Task: generate_embedding(entry_id)
  └── 4. 异步任务执行：
        ├── 调用 EmbeddingPort.embed([content_text])
        ├── UPDATE knowledge_entries SET embedding = $vector WHERE id = $entry_id
        └── 向量化成功前，条目已为 active 但不参与检索（embedding IS NULL 被查询条件排除）
```

### 4.2 RAG 语义检索流程

```text
RAGRetriever.retrieve(context, role, stage)
  │
  ├── 1. 查询要素提取（QueryExtractor）
  │      ├── 编程语言与技术栈（来自 environment_scan 结果）
  │      ├── 关键函数调用（eval、system、exec、file_get_contents 等）
  │      ├── 文件路径模式（controller/、auth/、admin/ 暗示安全功能域）
  │      ├── 变量名与注释中的安全关键词（password、token、secret、bypass）
  │      └── 候选漏洞类型（来自 code_analyst 前序输出）
  │
  ├── 2. 查询向量化
  │      EmbeddingPort.embed_query(extracted_query_text)
  │        → 1536 维向量
  │
  ├── 3. pgvector ANN 检索
  │      SELECT id, title, content_text, knowledge_type, risk_level,
  │             1 - (embedding <=> $query_vector) AS similarity
  │      FROM knowledge_entries
  │      WHERE entry_status = 'active'
  │        AND embedding IS NOT NULL
  │        AND (language IS NULL OR language LIKE '%' || $lang || '%')
  │        AND knowledge_type = ANY($allowed_types)
  │      ORDER BY embedding <=> $query_vector
  │      LIMIT $top_k
  │
  ├── 4. 重排序（Reranker）
  │      ├── 向量相似度（权重 0.6）
  │      ├── 语言/框架精确匹配加分（权重 0.2）
  │      └── 风险等级与当前分析上下文匹配加分（权重 0.2）
  │
  ├── 5. 上下文裁剪
  │      按 ASA_RAG_MAX_RESULT_TOKENS 截断，优先保留高相似度条目
  │
  ├── 6. 检索记录落库
  │      INSERT INTO knowledge_retrievals (
  │        project_id, stage_id, worker_task_id, retrieval_type,
  │        query_text, filter_language, filter_knowledge_types,
  │        top_k, retrieved_entries, retrieval_duration_ms
  │      )
  │
  └── 7. 返回给 ContextBuilder → 注入角色上下文
```

### 4.3 检索降级与容错

RAG 是增强而非必需——检索链路中任何环节失败时，角色在无知识增强的情况下继续执行：

```text
检索异常处理：
  ├── Embedding 模型不可用 → 跳过检索，角色正常执行，记录 warning 日志
  ├── pgvector 查询超时 → 降级为标签/关键词匹配（LIKE/ILIKE），记录 degradation 日志
  ├── 检索结果为空 → 返回空列表，不注入额外上下文
  ├── 向量维度不匹配 → 启动时 Fatal Error，阻止 Worker 启动
  └── 检索记录写入失败 → 记录 error 日志，不影响角色执行
```

### 4.4 自动知识沉淀

```text
报告生成阶段（report_generate）完成后：
  │
  ├── 1. 提取沉淀候选：遍历 verified=true 的漏洞及其修复建议
  ├── 2. 按漏洞类型去重：同一规则类型 + 同一语言的漏洞合并
  ├── 3. 创建知识条目：
  │     ├── knowledge_type = 'historical_assessment'
  │     ├── entry_status = 'draft'
  │     ├── source_type = 'auto_deposit'
  │     ├── 正文 = 漏洞模式 + 攻击路径摘要 + 修复方案
  │     └── 关联项目通过 source_url 指向项目报告
  └── 4. 管理员通过知识条目列表审核后激活
```

## 5. 数据库设计要点

### 5.1 向量字段

```sql
-- knowledge_entries 核心向量字段
embedding vector(1536)  -- 维度由 Embedding 模型决定，首次 Migration 注释可配置性

-- IVFFlat 向量索引（数据量达千条级别后创建）
CREATE INDEX ix_knowledge_entries__embedding_ivfflat
  ON knowledge_entries
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = <N>);  -- lists = 条目数 / 1000，周期性重建
```

### 5.2 关键索引

| 索引 | 用途 |
| --- | --- |
| `ix_knowledge_entries__knowledge_type_entry_status` | 按子库和状态筛选 |
| `ix_knowledge_entries__language` | 按编程语言过滤 |
| `ix_knowledge_entries__risk_level` | 按风险等级过滤 |
| `ix_knowledge_entries__tags` | GIN 索引，标签数组包含查询 |
| `ix_knowledge_entries__embedding_ivfflat` | IVFFlat 向量 ANN 检索（`vector_cosine_ops`） |
| `ix_knowledge_retrievals__project_id_created_at` | 项目检索历史 |
| `ix_knowledge_retrievals__stage_id_created_at` | 阶段检索效果分析 |
| `ix_knowledge_retrievals__worker_task_id_created_at` | 任务级检索追溯 |

### 5.3 设计约束

- `language` 和 `framework` 使用逗号分隔多值字符串而非 PostgreSQL 数组，以便与 pgvector 的结构化过滤配合。
- `embedding` 维度（默认 1536）必须与所选 Embedding 模型输出维度一致。
- `entry_status = 'disabled'` 的条目不参与检索但保留向量数据。
- `entry_status = 'active'` 且 `embedding IS NULL` 的条目（向量生成中）不参与检索。
- `knowledge_retrievals` 作为追加型表，预计每项目每天 < 100 条，无需提前分区。
- IVFFlat 向量的 lists 参数在数据量增长后需周期性重建索引。

## 6. 代码实现指南

### 6.1 目录结构

```text
packages/backend-core/src/asa_core/domain/knowledge/
├── entities.py                 # KnowledgeEntry 聚合根、KnowledgeRetrieval 实体
├── value_objects.py            # KnowledgeType, EntryStatus, RetrievalType 值对象
├── repository.py               # KnowledgeEntryRepository, KnowledgeRetrievalRepository 接口
└── exceptions.py               # KnowledgeEntryNotFound, EmbeddingDimensionMismatch

packages/backend-core/src/asa_core/application/
├── commands/
│   ├── create_entry.py         # CreateKnowledgeEntry Handler
│   ├── update_entry.py         # UpdateKnowledgeEntry Handler
│   ├── activate_entry.py       # ActivateKnowledgeEntry（draft → active + 投递向量化任务）
│   ├── delete_entry.py         # DeleteKnowledgeEntry Handler
│   └── generate_embedding.py   # GenerateEmbedding Celery Task Handler
├── queries/
│   ├── list_entries.py         # ListKnowledgeEntries Query
│   ├── get_entry.py            # GetKnowledgeEntry Query
│   ├── search_knowledge.py     # SemanticSearch Query
│   └── list_retrievals.py      # ListProjectRetrievals Query
├── services/
│   ├── rag_retriever.py        # RAGRetriever（查询提取、向量检索、重排序、上下文裁剪）
│   ├── reranker.py             # Reranker（多维度加权排序）
│   └── query_extractor.py      # QueryExtractor（从源码上下文提取检索要素）
└── ports/
    ├── embedding_port.py       # EmbeddingPort 接口
    ├── knowledge_repository.py # KnowledgeEntryRepository 接口
    └── retrieval_repository.py # KnowledgeRetrievalRepository 接口

apps/api/src/asa_api/routers/v1/knowledge.py
apps/api/src/asa_api/schemas/knowledge.py

packages/backend-core/src/asa_core/infrastructure/
├── pgvector/
│   ├── embedding_adapter.py    # Embedding 模型适配器
│   └── vector_search.py        # pgvector 检索查询构建
└── repositories/
    ├── knowledge_entry_repo.py # KnowledgeEntryRepository 实现
    └── knowledge_retrieval_repo.py  # KnowledgeRetrievalRepository 实现
```

### 6.2 关键实现约束

- **EmbeddingPort 接口隔离**：业务代码只依赖 `EmbeddingPort` 抽象，不直接调用 OpenAI SDK 或 HTTP 客户端。
- **向量维度启动校验**：Worker 启动时调用 Embedding 模型获取维度，与数据库 `knowledge_entries.embedding` 列定义对比，不匹配则 Fatal Error。
- **向量异步生成**：条目激活后通过 Celery 异步生成向量，不阻塞 API 响应。
- **pgvector 查询使用参数化**：查询向量使用 `$query_vector` 参数绑定，禁止拼接向量字面量。
- **检索结果脱敏**：`query_text` 写入 `knowledge_retrievals` 前移除完整源码片段、IP 地址和密钥模式。
- **检索记录不参与业务状态流转**：`knowledge_retrievals` 表仅用于分析，写入失败只记录日志不影响角色任务执行。
- **RAG 降级优雅**：Embedding 不可用、pgvector 超时、结果为空等场景均不中断分析流程。

## 7. 安全要点

- 角色通过 `search_security_knowledge` 工具只能进行语义检索，不能执行任意 SQL 或直接向量查询。
- 检索过滤条件（语言、子库类型）由 Worker 端根据任务上下文自动附加，角色不能绕过。
- 检索查询文本在进入 Embedding 模型前脱敏（移除完整源码片段、IP 地址、密钥模式）。
- `knowledge_retrievals.query_text` 写入数据库前脱敏。
- 知识条目通过 `entry_status` 控制可见性，禁用条目不参与检索。
- 仅管理员可管理知识条目（创建、编辑、激活、禁用、删除）。
- 普通用户仅能查询 `active` 条目和使用语义检索接口。
- 删除用户时 `created_by` 和 `reviewed_by` 外键使用 `SET NULL`，不删除知识条目。

## 8. 配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| 检索 top-k | `ASA_RAG_TOP_K` | 8 | 单次检索召回数 |
| 最小相似度阈值 | `ASA_RAG_MIN_SIMILARITY` | 0.65 | 低于此值的条目被过滤 |
| 单任务最大工具调用次数 | `ASA_RAG_MAX_TOOL_CALLS` | 5 | 防止角色过度依赖检索 |
| 检索结果最大 token | `ASA_RAG_MAX_RESULT_TOKENS` | 2000 | 注入上下文前的截断上限 |
| 子库默认权重 | `ASA_RAG_TYPE_WEIGHTS` | `vuln=1.0,standard=0.8,remed=0.9,history=0.6` | 四个子库的排序权重 |
| Embedding 模型名称 | `ASA_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI 兼容模型名 |
| Embedding 请求超时（秒） | `ASA_EMBEDDING_TIMEOUT_SECONDS` | 10 | 单次 Embedding 请求超时 |
| Embedding 最大批量大小 | `ASA_EMBEDDING_MAX_BATCH_SIZE` | 100 | 单次请求批量文本数上限 |

## 9. 测试要点

### 9.1 单元测试

- 知识条目状态机：draft → active → disabled 及非法转换拒绝
- 查询要素提取（QueryExtractor）：从源码片段提取语言、函数调用、安全关键词
- 重排序（Reranker）：多维度加权、语言匹配加分、相似度阈值过滤
- 检索降级：Embedding 超时 → 降级关键词匹配、pgvector 超时 → 降级 LIKE 查询
- 向量维度一致性校验：匹配/不匹配的行为

### 9.2 API 测试

- `GET /api/v1/knowledge/entries` — admin 可见全部状态、user 仅见 active、分页筛选正确
- `POST /api/v1/knowledge/entries` — 创建成功返回 draft（201）、字段校验（422）、非 admin 拒绝（403）
- `PUT /api/v1/knowledge/entries/{id}` — 更新成功、status 改为 active 后触发向量生成
- `DELETE /api/v1/knowledge/entries/{id}` — 删除成功（204）、二次确认、不存在（404）
- `POST /api/v1/knowledge/search` — 语义检索返回相似度降序、空查询拒绝、top_k 边界校验
- `GET /api/v1/projects/{id}/knowledge/retrievals` — 分页正确、无权限拒绝（403）

### 9.3 数据库集成测试

- 向量索引：ANN 检索召回正确、相似度排序正确
- 向量维度不匹配时 Worker 启动失败
- `entry_status = 'disabled'` 条目不参与检索
- `embedding IS NULL` 的 active 条目不参与检索
- 并发创建知识条目无冲突

## 10. 相关文档

- [概要设计总纲 - 第 3.4 节 RAG 分析技术](../3_概要设计/自动化安全评估系统-概要设计总纲.md#34-rag-分析技术)
- [API 接口文档 - 第 8 章 知识库接口](../4_开发规范/API接口文档.md#8-知识库接口)
- [数据库设计 - knowledge_entries 表](../4_开发规范/数据库/数据库设计.md#517-knowledge_entries)
- [数据库设计 - knowledge_retrievals 表](../4_开发规范/数据库/数据库设计.md#518-knowledge_retrievals)
- [调度与AI角色模块 - 第 7 章 RAG 知识检索](./03-调度与AI角色模块.md#7-rag-知识检索)
