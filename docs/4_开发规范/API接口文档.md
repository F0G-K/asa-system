本文档约 15000 字，阅读约 30 分钟。

# 自动化安全评估系统 API 接口文档

## 1. 文档说明

### 1.1 目的

本文档定义自动化安全评估系统（ASA System）MVP 的外部 REST API、WebSocket 协议、认证规则、错误码和数据格式，作为前端、FastAPI 后端、自动化测试和 OpenAPI 实现的统一契约。

### 1.2 设计依据

- `docs/1_PRD/自动化安全评估系统-PRD.md`
- `docs/3_概要设计/自动化安全评估系统-概要设计总纲.md`
- `docs/4_开发规范/数据库/数据库设计.md`
- `docs/0_draft/1.4 自动化安全评估系统.md`

文档优先遵循 PRD 的业务范围与验收标准，接口统一使用概要设计确定的 `/api/v1` 版本前缀。

### 1.3 接口范围

本文档覆盖以下外部接口：

| 领域 | 接口数量 | 说明 |
| --- | ---: | --- |
| 系统与认证 | 6 | 初始化状态、初始化、登录、退出、配置读取、配置更新 |
| 项目管理 | 6 | 创建、列表、详情、启动、停止、删除 |
| 过程监控 | 5 | 阶段、角色任务、消息、日志、资源 |
| 评估结果 | 6 | 漏洞列表与详情、攻击路径列表与详情、报告预览与下载 |
| 实时通信 | 1 | 项目事件 WebSocket |

PRD 未逐项列出但为页面闭环所必需的接口如下：

| 补充接口 | 补充原因 |
| --- | --- |
| `GET /api/v1/system/status` | 前端在初始化页与登录页之间进行安全路由 |
| `POST /api/v1/system/logout` | 清除服务端登录态并使认证 Cookie 失效 |
| `GET /api/v1/system/config`、`PUT /api/v1/system/config` | 落实管理员读取与更新系统配置需求 |
| `GET /api/v1/projects/{project_id}/messages` | 支持角色消息历史回放和断线数据补偿 |
| 漏洞与攻击路径详情接口 | 落实详情页展示要求 |
| 报告下载接口 | 落实报告文件下载要求 |

内部执行网关、Celery 任务、模型适配器和 Event Relay 不属于浏览器可访问的外部 API，不在本文档中定义。

## 2. 通用约定

### 2.1 服务地址与协议

| 项目 | 值 |
| --- | --- |
| REST 基础路径 | `/api/v1` |
| REST 协议 | HTTPS；本地开发环境可使用 HTTP |
| WebSocket 路径 | `/api/v1/projects/{project_id}/stream` |
| WebSocket 协议 | WSS；本地开发环境可使用 WS |
| 数据格式 | `application/json; charset=utf-8` |
| 时间格式 | ISO 8601 UTC，例如 `2026-07-24T08:30:00Z` |
| 标识格式 | 对外业务实体使用 UUID；日志、消息等游标为 int64 |
| 字符编码 | UTF-8 |

生产环境不得通过 HTTP 或 WS 传输认证信息。

### 2.2 认证与授权

登录成功后，服务端通过 `Set-Cookie` 返回短期会话 Cookie：

```http
Set-Cookie: asa_session=<opaque-session>; Path=/; HttpOnly; Secure; SameSite=Lax
Set-Cookie: asa_csrf=<csrf-token>; Path=/; Secure; SameSite=Lax
```

- `asa_session` 为不透明会话值，前端不得读取或持久化到 `localStorage`。
- 浏览器访问受保护接口时自动携带 `asa_session`。
- 使用 Cookie 认证的 `POST`、`PUT`、`PATCH`、`DELETE` 请求必须在 `X-CSRF-Token` 中回传 `asa_csrf` 的值。
- Cookie、密码、仓库凭证和 CSRF Token 不得写入日志、审计载荷、事件载荷或报告。
- 普通用户默认只能访问本人创建的项目；当前 MVP 未定义项目共享授权模型。
- 管理员可以访问系统配置。管理员访问项目敏感资源时仍执行项目权限判断并记录审计。

### 2.3 通用请求头

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Accept` | string | 否 | `application/json` | 期望的响应媒体类型 |
| `Content-Type` | string | 有请求体时必填 | 无 | JSON 请求固定为 `application/json` |
| `Cookie` | string | 受保护接口必填 | 无 | 浏览器自动携带 `asa_session` |
| `X-CSRF-Token` | string | 已认证写操作必填 | 无 | 防止跨站请求伪造 |
| `X-Request-ID` | string(uuid) | 否 | 服务端生成 | 调用方提供的链路标识；格式无效时返回 `422` |
| `Idempotency-Key` | string | 指定写接口必填 | 无 | 长度 1 至 128；用于启动、停止和删除去重 |

所有响应返回 `X-Request-ID`。服务端生成或接受的请求标识同时写入统一响应体的 `request_id`。

### 2.4 统一响应结构

除文件下载和 WebSocket 外，成功与失败响应均使用以下结构：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `code` | string | 是 | 无 | 稳定的业务码，大写下划线格式 |
| `message` | string | 是 | 无 | 面向用户的简洁中文提示 |
| `data` | object、array 或 null | 是 | `null` | 成功数据或结构化错误详情 |
| `request_id` | string(uuid) | 是 | 服务端生成 | 请求链路标识 |

成功响应示例：

```json
{
  "code": "PROJECT_DETAIL_OK",
  "message": "查询成功",
  "data": {
    "id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "project_name": "商城支付服务安全评估"
  },
  "request_id": "80e09d7e-92ab-4dbb-8982-ef891ce0d5f0"
}
```

失败响应示例：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "data": {
    "errors": [
      {
        "field": "body.source_type",
        "reason": "必须为 local 或 repository"
      }
    ]
  },
  "request_id": "80e09d7e-92ab-4dbb-8982-ef891ce0d5f0"
}
```

### 2.5 分页与排序

普通列表使用页码分页：

| 查询参数 | 类型 | 必填 | 默认值 | 约束与说明 |
| --- | --- | :---: | --- | --- |
| `page` | integer | 否 | `1` | 最小值 1 |
| `page_size` | integer | 否 | `20` | 取值 1 至 100 |

页码分页返回：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_next": false
}
```

日志、消息和资源等追加型数据使用游标分页：

| 查询参数 | 类型 | 必填 | 默认值 | 约束与说明 |
| --- | --- | :---: | --- | --- |
| `cursor` | integer(int64) | 否 | 无 | 上一页返回的 `next_cursor`；首次请求不传 |
| `limit` | integer | 否 | 各接口定义 | 不得超过接口规定上限 |

游标分页返回：

```json
{
  "items": [],
  "next_cursor": null,
  "has_more": false
}
```

服务端必须使用稳定的次级排序键，避免同一时间戳下重复或遗漏数据。

### 2.6 幂等规则

- 启动、停止和删除请求必须携带 `Idempotency-Key`。
- 同一用户、同一项目、同一操作和同一 Key 的重复请求返回首次受理结果，不创建重复任务。
- 同一 Key 被用于不同项目、不同操作或不同请求体时返回 `409 IDEMPOTENCY_KEY_REUSED`。
- 幂等只保证请求受理不重复，不表示异步任务一定成功。
- 前端发生超时或网络中断时，应使用原 Key 重试，不得生成新 Key。

### 2.7 异步操作

源码拉取、隔离环境创建、评估启动、停止收敛、报告生成和项目物理文件清理均为异步操作。相关接口返回 `202 Accepted` 后，前端通过项目详情、过程查询或 WebSocket 获取最终状态。

项目停止受理后，在 Worker 完成收敛前 `project_status` 仍可能为 `running`，取消意图由 `stop_requested_at` 表达；阶段和角色任务状态不增加 `stopped` 值。

### 2.8 数据类型与单位

| 字段类型 | 表示方式 |
| --- | --- |
| UUID | 小写带连字符字符串 |
| 时间 | UTC ISO 8601 字符串 |
| CPU | number，单位为百分比，可超过 100 |
| 内存 | integer(int64)，单位为字节 |
| Token | integer(int64)，当前项目运行实例的累计用量 |
| 文件路径 | 项目内相对路径或受控逻辑键，不返回宿主机绝对路径 |
| 大文本 | string；报告 Markdown、证据和日志在展示前执行安全转义 |

### 2.9 HTTP 状态码

| HTTP 状态码 | 使用场景 |
| ---: | --- |
| `200 OK` | 查询成功、登录成功、退出成功、配置更新成功 |
| `201 Created` | 管理员初始化成功、项目创建成功 |
| `202 Accepted` | 启动、停止或删除请求已异步受理 |
| `400 Bad Request` | JSON 语法错误或协议格式无法解析 |
| `401 Unauthorized` | 未登录、会话无效或会话过期 |
| `403 Forbidden` | 已登录但角色或项目权限不足，或 CSRF 校验失败 |
| `404 Not Found` | 资源不存在 |
| `409 Conflict` | 初始化、项目状态、幂等键或配置版本冲突 |
| `422 Unprocessable Entity` | 字段、查询参数或路径参数校验失败 |
| `429 Too Many Requests` | 登录、写操作或连接频率超过限制 |
| `500 Internal Server Error` | 未预期的服务端错误 |
| `503 Service Unavailable` | 依赖未就绪或系统暂时无法受理 |

### 2.10 通用错误码

| 错误码 | HTTP 状态 | 说明 |
| --- | ---: | --- |
| `MALFORMED_JSON` | 400 | JSON 无法解析 |
| `AUTH_REQUIRED` | 401 | 未提供有效登录态 |
| `SESSION_EXPIRED` | 401 | 会话已过期 |
| `ACCOUNT_DISABLED` | 403 | 账户已禁用 |
| `PERMISSION_DENIED` | 403 | 当前用户无操作权限 |
| `CSRF_INVALID` | 403 | CSRF Token 缺失或不匹配 |
| `RESOURCE_NOT_FOUND` | 404 | 通用资源不存在 |
| `VALIDATION_ERROR` | 422 | 参数校验失败 |
| `TIME_RANGE_INVALID` | 422 | 时间范围或起止顺序无效 |
| `CURSOR_INVALID` | 422 | 游标格式无效或不属于当前查询 |
| `IDEMPOTENCY_KEY_REUSED` | 409 | 幂等键与原请求不一致 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `DEPENDENCY_UNAVAILABLE` | 503 | PostgreSQL、Redis 或执行网关等关键依赖不可用 |
| `INTERNAL_ERROR` | 500 | 未预期错误；响应不得包含堆栈 |

## 3. 公共数据模型

### 3.1 UserSummary

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `id` | string(uuid) | 是 | 无 | 用户标识 |
| `username` | string | 是 | 无 | 登录名 |
| `role` | string | 是 | 无 | `user` 或 `admin` |
| `status` | string | 是 | 无 | `active` 或 `disabled` |

### 3.2 ProjectSummary

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `id` | string(uuid) | 是 | 无 | 项目标识 |
| `project_name` | string | 是 | 无 | 项目名称 |
| `source_type` | string | 是 | 无 | `local` 或 `repository` |
| `source_path` | string | 是 | 无 | 本地相对路径或已脱敏仓库地址 |
| `environment_type` | string | 是 | 无 | 创建时选择的隔离环境类型 |
| `project_status` | string | 是 | 无 | `created`、`running`、`completed`、`failed`、`stopped` |
| `last_started_at` | string(date-time) 或 null | 是 | `null` | 最近运行开始时间 |
| `last_finished_at` | string(date-time) 或 null | 是 | `null` | 最近运行结束时间 |
| `created_at` | string(date-time) | 是 | 无 | 创建时间 |
| `updated_at` | string(date-time) | 是 | 无 | 更新时间 |

### 3.3 ProjectDetail

`ProjectDetail` 包含 `ProjectSummary` 的全部字段，并增加：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `task_content` | string | 是 | 无 | 评估任务说明 |
| `created_by` | string(uuid) | 是 | 无 | 创建者标识 |
| `stop_requested_at` | string(date-time) 或 null | 是 | `null` | 停止请求时间 |
| `runtime` | object 或 null | 是 | `null` | 隔离环境摘要 |
| `statistics` | object | 是 | 无 | 漏洞、攻击路径和任务统计 |
| `report_status` | string 或 null | 是 | `null` | `pending`、`generating`、`ready`、`failed` |

`runtime` 字段：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `id` | string(uuid) | 是 | 无 | 运行实例标识 |
| `runtime_identifier` | string 或 null | 是 | `null` | 执行网关环境编号 |
| `container_status` | string | 是 | 无 | `pending`、`starting`、`running`、`stopping`、`stopped`、`destroyed`、`failed` |
| `started_at` | string(date-time) 或 null | 是 | `null` | 环境启动时间 |
| `stopped_at` | string(date-time) 或 null | 是 | `null` | 环境停止时间 |
| `error_message` | string 或 null | 是 | `null` | 脱敏错误摘要 |

`statistics` 字段：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `vulnerability_count` | integer | 是 | `0` | 漏洞总数 |
| `verified_vulnerability_count` | integer | 是 | `0` | 已验证漏洞数 |
| `attack_path_count` | integer | 是 | `0` | 攻击路径总数 |
| `worker_task_count` | integer | 是 | `0` | 角色任务总数 |

### 3.4 状态值

| 分类 | 允许值 |
| --- | --- |
| 用户角色 | `user`、`admin` |
| 项目状态 | `created`、`running`、`completed`、`failed`、`stopped` |
| 阶段名称 | `environment_scan`、`code_analysis`、`vulnerability_verify`、`report_generate`、`done` |
| 阶段状态 | `idle`、`running`、`success`、`failed` |
| 角色任务状态 | `idle`、`running`、`success`、`failed` |
| 执行角色 | `general`、`environment_inspector`、`code_analyst`、`vulnerability_verifier`、`report_editor`、`operations_assistant` |
| 风险等级 | `critical`、`high`、`medium`、`low`、`info` |
| 验证状态 | `pending`、`verified`、`rejected` |
| 日志级别 | `debug`、`info`、`warning`、`error` |
| 报告状态 | `pending`、`generating`、`ready`、`failed` |

## 4. 系统与认证接口

### 4.1 查询系统初始化状态

接口名称：查询系统初始化状态。

用途：供未登录前端判断展示初始化页还是登录页，不返回账户、配置或依赖详情。

请求方式：`GET`

URL：`/api/v1/system/status`

认证方式：无需认证。

请求头：使用通用请求头；不需要 `Cookie` 和 `X-CSRF-Token`。

路径参数：无。

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "SYSTEM_STATUS_OK",
  "message": "查询成功",
  "data": {
    "initialized": true
  },
  "request_id": "b27c5347-34bf-457f-a1a8-d860ec0b30ac"
}
```

失败响应：`503 Service Unavailable`

```json
{
  "code": "DEPENDENCY_UNAVAILABLE",
  "message": "系统暂时不可用",
  "data": null,
  "request_id": "b27c5347-34bf-457f-a1a8-d860ec0b30ac"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `SYSTEM_STATUS_OK` | 查询成功 |
| 503 | `DEPENDENCY_UNAVAILABLE` | 无法读取初始化状态 |
| 500 | `INTERNAL_ERROR` | 未预期错误 |

注意事项：

- 接口可被频繁访问，服务端应设置基础限流。
- 不得通过该接口泄露管理员用户名、系统配置或组件版本。

### 4.2 初始化管理员

接口名称：初始化管理员账户。

用途：系统首次使用时创建唯一的初始管理员。

请求方式：`POST`

URL：`/api/v1/system/init`

认证方式：无需认证；仅在系统未初始化时允许调用。

请求头：

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Content-Type` | string | 是 | 无 | `application/json` |
| `X-Request-ID` | string(uuid) | 否 | 服务端生成 | 链路标识 |

路径参数：无。

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `username` | string | 是 | 无 | 1 至 64 个字符，写入前转小写，不允许空白字符 |
| `password` | string | 是 | 无 | 管理员密码；仅用于本次校验与 Argon2id 哈希 |

请求示例：

```json
{
  "username": "security_admin",
  "password": "Sas-Admin-2026!"
}
```

成功响应：`201 Created`

```json
{
  "code": "SYSTEM_INITIALIZED",
  "message": "系统初始化成功，请登录",
  "data": {
    "admin": {
      "id": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
      "username": "security_admin",
      "role": "admin",
      "status": "active"
    }
  },
  "request_id": "7698c098-ac08-4210-bb81-469d17e1b3c3"
}
```

失败响应：`409 Conflict`

```json
{
  "code": "SYSTEM_ALREADY_INITIALIZED",
  "message": "系统已完成初始化",
  "data": null,
  "request_id": "7698c098-ac08-4210-bb81-469d17e1b3c3"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 201 | `SYSTEM_INITIALIZED` | 初始管理员创建成功 |
| 409 | `SYSTEM_ALREADY_INITIALIZED` | 系统已存在管理员或初始化已完成 |
| 422 | `VALIDATION_ERROR` | 用户名或密码格式不合法 |
| 429 | `RATE_LIMITED` | 初始化尝试过于频繁 |
| 503 | `DEPENDENCY_UNAVAILABLE` | 数据库不可用 |

注意事项：

- “检查未初始化”和“创建管理员”必须在同一数据库事务及互斥范围内完成，防止并发创建多个初始管理员。
- 成功响应不自动建立登录态，调用方应继续调用登录接口。
- 密码不得出现在响应、日志、审计元数据或异常信息中。

### 4.3 用户登录

接口名称：用户登录。

用途：校验用户名和密码，创建短期登录会话。

请求方式：`POST`

URL：`/api/v1/system/login`

认证方式：无需认证。

请求头：

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Content-Type` | string | 是 | 无 | `application/json` |
| `X-Request-ID` | string(uuid) | 否 | 服务端生成 | 链路标识 |

路径参数：无。

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `username` | string | 是 | 无 | 登录名 |
| `password` | string | 是 | 无 | 登录密码 |

请求示例：

```json
{
  "username": "security_admin",
  "password": "Sas-Admin-2026!"
}
```

成功响应：`200 OK`

```json
{
  "code": "LOGIN_SUCCESS",
  "message": "登录成功",
  "data": {
    "user": {
      "id": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
      "username": "security_admin",
      "role": "admin",
      "status": "active"
    },
    "expires_at": "2026-07-24T10:30:00Z"
  },
  "request_id": "7e27031b-bebd-4c15-976d-3f49ed7f9ebc"
}
```

响应头同时设置 `asa_session` 和 `asa_csrf` Cookie。

失败响应：`401 Unauthorized`

```json
{
  "code": "INVALID_CREDENTIALS",
  "message": "用户名或密码错误",
  "data": null,
  "request_id": "7e27031b-bebd-4c15-976d-3f49ed7f9ebc"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `LOGIN_SUCCESS` | 登录成功 |
| 401 | `INVALID_CREDENTIALS` | 用户不存在或密码错误 |
| 403 | `ACCOUNT_DISABLED` | 账户已禁用 |
| 409 | `SYSTEM_NOT_INITIALIZED` | 系统尚未初始化 |
| 422 | `VALIDATION_ERROR` | 请求字段不合法 |
| 429 | `RATE_LIMITED` | 登录失败次数超过限制 |

注意事项：

- 用户不存在和密码错误统一返回 `INVALID_CREDENTIALS`，避免账户枚举。
- 密码校验使用 Argon2id，失败路径保持相近耗时。
- 前端请求必须启用 Cookie 凭证，例如 Axios 的 `withCredentials: true`。

### 4.4 用户退出

接口名称：用户退出。

用途：使当前会话失效并清除认证 Cookie。

请求方式：`POST`

URL：`/api/v1/system/logout`

认证方式：Cookie 会话认证。

请求头：`Cookie` 和 `X-CSRF-Token` 必填，其他使用通用请求头。

路径参数：无。

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "LOGOUT_SUCCESS",
  "message": "已安全退出",
  "data": null,
  "request_id": "6bd99158-286c-4eb4-a65f-b3e22d25f075"
}
```

失败响应：`403 Forbidden`

```json
{
  "code": "CSRF_INVALID",
  "message": "请求校验失败",
  "data": null,
  "request_id": "6bd99158-286c-4eb4-a65f-b3e22d25f075"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `LOGOUT_SUCCESS` | 会话已失效；重复退出也返回成功 |
| 401 | `AUTH_REQUIRED` | 未携带可识别的会话 |
| 403 | `CSRF_INVALID` | CSRF 校验失败 |

注意事项：

- 成功响应应将两个 Cookie 的过期时间设置为过去。
- 服务端退出操作设计为幂等。

### 4.5 查询系统配置

接口名称：查询当前系统配置。

用途：供管理员查看当前生效的隔离环境类型、超时、并发和保留策略。

请求方式：`GET`

URL：`/api/v1/system/config`

认证方式：Cookie 会话认证，仅 `admin`。

请求头：使用受保护查询接口的通用请求头。

路径参数：无。

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "SYSTEM_CONFIG_OK",
  "message": "查询成功",
  "data": {
    "id": "bd3067d7-106f-4c26-9f37-66a141916f46",
    "version": 3,
    "default_timeout_seconds": 1800,
    "max_concurrent_projects": 2,
    "log_retention_days": 30,
    "file_retention_days": 90,
    "enabled_environment_types": [
      "python-3.12",
      "node-22"
    ],
    "settings": {
      "destroy_runtime_after_completion": true
    },
    "is_active": true,
    "updated_by": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
    "updated_at": "2026-07-24T08:20:00Z"
  },
  "request_id": "57823979-8020-4ac6-91cf-c93606287ab0"
}
```

失败响应：`403 Forbidden`

```json
{
  "code": "ADMIN_REQUIRED",
  "message": "仅管理员可访问系统配置",
  "data": null,
  "request_id": "57823979-8020-4ac6-91cf-c93606287ab0"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `SYSTEM_CONFIG_OK` | 查询成功 |
| 401 | `AUTH_REQUIRED`、`SESSION_EXPIRED` | 未登录或会话过期 |
| 403 | `ADMIN_REQUIRED` | 非管理员 |
| 404 | `SYSTEM_CONFIG_NOT_FOUND` | 尚无生效配置 |

注意事项：

- `settings` 只返回允许前端展示的非敏感配置。
- 密钥、Token、证书、仓库凭证、容器内部细节不得通过该接口返回。

### 4.6 更新系统配置

接口名称：更新系统配置。

用途：以不可变版本方式创建并激活一版新配置。

请求方式：`PUT`

URL：`/api/v1/system/config`

认证方式：Cookie 会话认证，仅 `admin`。

请求头：`Content-Type`、`Cookie` 和 `X-CSRF-Token` 必填。

路径参数：无。

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `expected_version` | integer 或 null | 是 | 无 | 当前配置版本；首次创建配置时为 `null` |
| `default_timeout_seconds` | integer 或 null | 是 | 无 | 正整数；`null` 表示未配置 |
| `max_concurrent_projects` | integer 或 null | 是 | 无 | 正整数；`null` 表示未配置 |
| `log_retention_days` | integer 或 null | 是 | 无 | 正整数；`null` 表示未配置 |
| `file_retention_days` | integer 或 null | 是 | 无 | 正整数；`null` 表示未配置 |
| `enabled_environment_types` | array[string] | 是 | `[]` | 环境类型标识列表，不得重复 |
| `settings` | object | 否 | `{}` | 经白名单校验的非敏感扩展配置 |

请求示例：

```json
{
  "expected_version": 3,
  "default_timeout_seconds": 2400,
  "max_concurrent_projects": 3,
  "log_retention_days": 30,
  "file_retention_days": 90,
  "enabled_environment_types": [
    "python-3.12",
    "node-22"
  ],
  "settings": {
    "destroy_runtime_after_completion": true
  }
}
```

成功响应：`200 OK`

```json
{
  "code": "SYSTEM_CONFIG_UPDATED",
  "message": "系统配置已更新",
  "data": {
    "id": "2c24423e-a2ec-4176-a3b6-65322eb5efc7",
    "version": 4,
    "default_timeout_seconds": 2400,
    "max_concurrent_projects": 3,
    "log_retention_days": 30,
    "file_retention_days": 90,
    "enabled_environment_types": [
      "python-3.12",
      "node-22"
    ],
    "settings": {
      "destroy_runtime_after_completion": true
    },
    "is_active": true,
    "updated_by": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
    "updated_at": "2026-07-24T08:45:00Z"
  },
  "request_id": "35712d4e-e8f3-4a6f-b2ce-15574086b0c5"
}
```

失败响应：`409 Conflict`

```json
{
  "code": "CONFIG_VERSION_CONFLICT",
  "message": "配置已被其他管理员更新，请刷新后重试",
  "data": {
    "expected_version": 3,
    "current_version": 4
  },
  "request_id": "35712d4e-e8f3-4a6f-b2ce-15574086b0c5"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `SYSTEM_CONFIG_UPDATED` | 新版本已生效 |
| 401 | `AUTH_REQUIRED`、`SESSION_EXPIRED` | 未登录或会话过期 |
| 403 | `ADMIN_REQUIRED`、`CSRF_INVALID` | 非管理员或 CSRF 校验失败 |
| 409 | `CONFIG_VERSION_CONFLICT` | 乐观锁版本冲突 |
| 422 | `VALIDATION_ERROR` | 数值、数组或配置项不合法 |

注意事项：

- 新配置只影响后续启动的项目；运行中项目继续使用启动时快照。
- 服务端应在同一事务中取消旧版本并激活新版本。
- `settings` 使用字段白名单和递归敏感键过滤，不接受密钥类字段。

## 5. 项目管理接口

### 5.1 创建项目

接口名称：创建安全评估项目。

用途：登记源码来源、任务范围和隔离环境类型，创建 `created` 状态项目。

请求方式：`POST`

URL：`/api/v1/projects`

认证方式：Cookie 会话认证，`user` 和 `admin` 均可调用。

请求头：`Content-Type`、`Cookie` 和 `X-CSRF-Token` 必填。

路径参数：无。

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 约束与说明 |
| --- | --- | :---: | --- | --- |
| `project_name` | string | 是 | 无 | 1 至 128 个字符 |
| `source_type` | string | 是 | 无 | `local` 或 `repository` |
| `source_path` | string | 是 | 无 | `local` 时为授权根目录内相对路径；`repository` 时为不含内联凭证的 HTTPS/SSH 仓库地址 |
| `task_content` | string | 是 | 无 | 非空评估说明，描述范围和重点 |
| `environment_type` | string | 是 | 无 | 必须属于当前启用环境类型 |

请求示例：

```json
{
  "project_name": "商城支付服务安全评估",
  "source_type": "repository",
  "source_path": "https://git.example.com/security-demo/payment-service.git",
  "task_content": "评估支付回调、订单权限校验和数据库访问层，重点检查注入与越权风险。",
  "environment_type": "python-3.12"
}
```

成功响应：`201 Created`

```json
{
  "code": "PROJECT_CREATED",
  "message": "项目创建成功",
  "data": {
    "id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "project_name": "商城支付服务安全评估",
    "source_type": "repository",
    "source_path": "https://git.example.com/security-demo/payment-service.git",
    "task_content": "评估支付回调、订单权限校验和数据库访问层，重点检查注入与越权风险。",
    "environment_type": "python-3.12",
    "project_status": "created",
    "created_by": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
    "created_at": "2026-07-24T08:50:00Z",
    "updated_at": "2026-07-24T08:50:00Z"
  },
  "request_id": "3859caf3-c63e-4768-a77d-7bd52cb90316"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "SOURCE_PATH_INVALID",
  "message": "源码地址与源码类型不匹配",
  "data": {
    "source_type": "local",
    "reason": "本地源码必须使用授权根目录内的相对路径"
  },
  "request_id": "3859caf3-c63e-4768-a77d-7bd52cb90316"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 201 | `PROJECT_CREATED` | 创建成功 |
| 403 | `CSRF_INVALID` | CSRF 校验失败 |
| 409 | `ENVIRONMENT_TYPE_DISABLED` | 环境类型未启用 |
| 422 | `VALIDATION_ERROR`、`SOURCE_PATH_INVALID`、`SOURCE_CREDENTIAL_FORBIDDEN` | 字段、路径或仓库地址不合法 |

注意事项：

- 创建接口只登记项目，不同步拉取仓库或创建容器。
- 仓库地址进入数据库前必须移除内联用户名、密码和 Token；发现内联凭证时应直接拒绝请求。
- 私有仓库凭证通过受控密钥引用在启动阶段临时注入，不属于本接口请求体。

### 5.2 查询项目列表

接口名称：查询项目列表。

用途：分页查询当前用户可访问的项目及最近运行摘要。

请求方式：`GET`

URL：`/api/v1/projects`

认证方式：Cookie 会话认证。

请求头：使用受保护查询接口的通用请求头。

路径参数：无。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `page` | integer | 否 | `1` | 页码 |
| `page_size` | integer | 否 | `20` | 每页 1 至 100 条 |
| `project_status` | string | 否 | 无 | 按项目状态精确筛选 |
| `source_type` | string | 否 | 无 | `local` 或 `repository` |
| `keyword` | string | 否 | 无 | 按项目名称匹配，去除首尾空白 |
| `sort` | string | 否 | `created_at:desc` | `created_at:asc`、`created_at:desc`、`updated_at:asc` 或 `updated_at:desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_LIST_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
        "project_name": "商城支付服务安全评估",
        "source_type": "repository",
        "source_path": "https://git.example.com/security-demo/payment-service.git",
        "environment_type": "python-3.12",
        "project_status": "running",
        "last_started_at": "2026-07-24T09:00:00Z",
        "last_finished_at": null,
        "created_at": "2026-07-24T08:50:00Z",
        "updated_at": "2026-07-24T09:06:12Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false
  },
  "request_id": "d3a45e43-1d04-4cfe-b224-6919c1b14fbb"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "data": {
    "errors": [
      {
        "field": "query.page_size",
        "reason": "必须小于或等于 100"
      }
    ]
  },
  "request_id": "d3a45e43-1d04-4cfe-b224-6919c1b14fbb"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `PROJECT_LIST_OK` | 查询成功，允许空列表 |
| 401 | `AUTH_REQUIRED`、`SESSION_EXPIRED` | 未登录或会话过期 |
| 422 | `VALIDATION_ERROR` | 筛选、分页或排序值不合法 |

注意事项：

- 普通用户查询必须附加 `created_by = current_user_id` 数据权限条件。
- 列表不返回完整任务说明、错误详情或报告正文。

### 5.3 查询项目详情

接口名称：查询项目详情。

用途：返回项目基本信息、运行环境摘要、统计值和报告状态。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_DETAIL_OK",
  "message": "查询成功",
  "data": {
    "id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "project_name": "商城支付服务安全评估",
    "source_type": "repository",
    "source_path": "https://git.example.com/security-demo/payment-service.git",
    "task_content": "评估支付回调、订单权限校验和数据库访问层，重点检查注入与越权风险。",
    "environment_type": "python-3.12",
    "project_status": "running",
    "created_by": "095e6a11-52f0-424a-90a1-0d81bd8cc1d9",
    "stop_requested_at": null,
    "runtime": {
      "id": "ec2ffb3b-8bec-424f-a36c-b56fe94fe474",
      "runtime_identifier": "asa-a8c3f3e0-001",
      "container_status": "running",
      "started_at": "2026-07-24T09:00:00Z",
      "stopped_at": null,
      "error_message": null
    },
    "statistics": {
      "vulnerability_count": 4,
      "verified_vulnerability_count": 2,
      "attack_path_count": 1,
      "worker_task_count": 8
    },
    "report_status": "generating",
    "last_started_at": "2026-07-24T09:00:00Z",
    "last_finished_at": null,
    "created_at": "2026-07-24T08:50:00Z",
    "updated_at": "2026-07-24T09:06:12Z"
  },
  "request_id": "10c507ab-c43e-4fcb-aa08-a7056506a841"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "项目不存在",
  "data": null,
  "request_id": "10c507ab-c43e-4fcb-aa08-a7056506a841"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `PROJECT_DETAIL_OK` | 查询成功 |
| 403 | `PROJECT_ACCESS_DENIED` | 无项目访问权限 |
| 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 422 | `VALIDATION_ERROR` | `project_id` 不是有效 UUID |

注意事项：

- 统计值必须从权威持久化数据计算或由同一事务维护，不得依赖 WebSocket 客户端计数。
- `source_path` 必须为脱敏值。

### 5.4 启动项目

接口名称：启动项目评估。

用途：受理 `created` 项目的源码准备、隔离环境创建和评估任务。

请求方式：`POST`

URL：`/api/v1/projects/{project_id}/start`

认证方式：Cookie 会话认证和项目操作权限。

请求头：

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Content-Type` | string | 是 | 无 | `application/json` |
| `Cookie` | string | 是 | 无 | 登录会话 |
| `X-CSRF-Token` | string | 是 | 无 | CSRF Token |
| `Idempotency-Key` | string | 是 | 无 | 本次启动操作唯一键 |

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：无。

请求体：空 JSON 对象。

```json
{}
```

成功响应：`202 Accepted`

```json
{
  "code": "PROJECT_START_ACCEPTED",
  "message": "项目启动请求已受理",
  "data": {
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "project_status": "created",
    "operation": "start",
    "accepted_at": "2026-07-24T09:00:00Z"
  },
  "request_id": "16a2efad-6f67-4c13-9141-d43419969e39"
}
```

失败响应：`409 Conflict`

```json
{
  "code": "PROJECT_STATUS_CONFLICT",
  "message": "当前项目状态不允许启动",
  "data": {
    "project_status": "completed",
    "allowed_statuses": [
      "created"
    ]
  },
  "request_id": "16a2efad-6f67-4c13-9141-d43419969e39"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 202 | `PROJECT_START_ACCEPTED` | 首次或幂等重复受理 |
| 403 | `PROJECT_ACCESS_DENIED`、`CSRF_INVALID` | 无项目权限或 CSRF 失败 |
| 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 409 | `PROJECT_STATUS_CONFLICT` | 项目不是 `created` |
| 409 | `PROJECT_CAPACITY_EXCEEDED` | 已达到并发项目上限 |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Key 与原请求冲突 |
| 422 | `VALIDATION_ERROR` | 路径参数或请求头不合法 |
| 503 | `DEPENDENCY_UNAVAILABLE` | 队列或执行依赖无法受理 |

注意事项：

- API 不等待仓库拉取、容器创建或首个阶段执行。
- 项目只有在源码和环境准备成功后才转为 `running`；准备失败转为 `failed`。
- 同一项目同一时刻最多一个运行实例，MVP 不支持终态原地重跑。
- 受理事务应创建运行记录、5 个固定阶段、幂等记录和 Outbox 事件，再在提交后投递任务。

### 5.5 停止项目

接口名称：停止项目评估。

用途：对 `running` 项目发出协作取消请求，并阻止后续阶段和角色任务启动。

请求方式：`POST`

URL：`/api/v1/projects/{project_id}/stop`

认证方式：Cookie 会话认证和项目操作权限。

请求头：`Content-Type`、`Cookie`、`X-CSRF-Token`、`Idempotency-Key` 必填。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `reason` | string 或 null | 否 | `null` | 用户停止原因，最大 500 字符；写入前脱敏 |

请求示例：

```json
{
  "reason": "演示窗口结束，停止本次评估。"
}
```

成功响应：`202 Accepted`

```json
{
  "code": "PROJECT_STOP_ACCEPTED",
  "message": "项目停止请求已受理",
  "data": {
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "project_status": "running",
    "stop_requested_at": "2026-07-24T09:12:00Z",
    "operation": "stop"
  },
  "request_id": "029861b9-f925-4d36-8f96-7c7c6951e7c5"
}
```

失败响应：`409 Conflict`

```json
{
  "code": "PROJECT_NOT_RUNNING",
  "message": "只有运行中的项目可以停止",
  "data": {
    "project_status": "created"
  },
  "request_id": "029861b9-f925-4d36-8f96-7c7c6951e7c5"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 202 | `PROJECT_STOP_ACCEPTED` | 停止请求首次或重复受理 |
| 403 | `PROJECT_ACCESS_DENIED`、`CSRF_INVALID` | 无权限或 CSRF 失败 |
| 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 409 | `PROJECT_NOT_RUNNING` | 项目不处于 `running` |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Key 与原请求冲突 |

注意事项：

- 受理后先设置 `stop_requested_at`，项目最终收敛为 `stopped`。
- 已保存的漏洞、路径、日志、资源、消息和报告草稿继续保留。
- 阶段和角色任务仍只使用 `idle`、`running`、`success`、`failed`。

### 5.6 删除项目

接口名称：删除项目。

用途：受理非运行项目的业务数据、隔离环境和项目文件清理。

请求方式：`DELETE`

URL：`/api/v1/projects/{project_id}`

认证方式：Cookie 会话认证和项目操作权限。

请求头：`Content-Type`、`Cookie`、`X-CSRF-Token`、`Idempotency-Key` 必填。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：无。

请求体：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `confirm_project_name` | string | 是 | 无 | 必须与当前项目名称完全一致 |

请求示例：

```json
{
  "confirm_project_name": "商城支付服务安全评估"
}
```

成功响应：`202 Accepted`

```json
{
  "code": "PROJECT_DELETE_ACCEPTED",
  "message": "项目删除请求已受理",
  "data": {
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "operation": "delete",
    "accepted_at": "2026-07-24T10:15:00Z"
  },
  "request_id": "336b2144-c036-45ce-8fb6-547188a5c305"
}
```

失败响应：`409 Conflict`

```json
{
  "code": "PROJECT_DELETE_FORBIDDEN",
  "message": "运行中的项目不能删除，请先停止项目",
  "data": {
    "project_status": "running"
  },
  "request_id": "336b2144-c036-45ce-8fb6-547188a5c305"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 202 | `PROJECT_DELETE_ACCEPTED` | 删除请求首次或重复受理 |
| 403 | `PROJECT_ACCESS_DENIED`、`CSRF_INVALID` | 无权限或 CSRF 失败 |
| 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 409 | `PROJECT_DELETE_FORBIDDEN` | 项目仍在运行 |
| 409 | `PROJECT_NAME_CONFIRMATION_MISMATCH` | 确认名称不一致 |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Key 与原请求冲突 |

注意事项：

- 删除不可恢复，前端必须二次确认。
- 数据库外键只负责业务记录级联；报告、日志、工作目录和容器由幂等清理任务处理。
- 审计日志保留脱敏后的最小操作元数据，项目外键删除后置空。
- 物理清理失败不得伪造成功，必须记录失败项供管理员定位。

## 6. 过程监控接口

### 6.1 查询阶段状态

接口名称：查询项目阶段状态。

用途：按固定顺序返回当前运行实例的 5 个阶段。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/stages`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_STAGES_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "e0e6c4e1-f375-45ff-9472-ea7d4d3b675e",
        "stage_name": "environment_scan",
        "stage_order": 1,
        "stage_status": "success",
        "started_at": "2026-07-24T09:00:04Z",
        "finished_at": "2026-07-24T09:02:18Z",
        "error_message": null
      },
      {
        "id": "179a46a8-512d-4f0b-b563-2db1297876c0",
        "stage_name": "code_analysis",
        "stage_order": 2,
        "stage_status": "running",
        "started_at": "2026-07-24T09:02:19Z",
        "finished_at": null,
        "error_message": null
      }
    ]
  },
  "request_id": "7e5f942d-ea9d-491b-bda3-b4791a8ea70b"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "PROJECT_RUNTIME_NOT_FOUND",
  "message": "项目尚未启动",
  "data": null,
  "request_id": "7e5f942d-ea9d-491b-bda3-b4791a8ea70b"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | `PROJECT_STAGES_OK` | 查询成功 |
| 403 | `PROJECT_ACCESS_DENIED` | 无项目访问权限 |
| 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 404 | `PROJECT_RUNTIME_NOT_FOUND` | 项目从未启动 |

注意事项：返回项按 `stage_order` 升序排列；前端不得自行推断未返回阶段。

### 6.2 查询角色任务

接口名称：查询项目角色任务。

用途：分页返回六类执行角色的任务、状态、结果摘要和错误摘要。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/workers`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `page` | integer | 否 | `1` | 页码 |
| `page_size` | integer | 否 | `20` | 每页 1 至 100 条 |
| `stage_id` | string(uuid) | 否 | 无 | 按阶段筛选 |
| `worker_role` | string | 否 | 无 | 按执行角色筛选 |
| `task_status` | string | 否 | 无 | 按任务状态筛选 |
| `sort` | string | 否 | `created_at:asc` | `created_at:asc` 或 `created_at:desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_WORKERS_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "ff7d788f-b9b1-42a1-8fa1-6d15b932342c",
        "stage_id": "179a46a8-512d-4f0b-b563-2db1297876c0",
        "worker_role": "code_analyst",
        "task_content": "检查支付回调与订单查询入口的注入和越权风险。",
        "task_status": "running",
        "result_summary": null,
        "error_message": null,
        "attempt_count": 1,
        "started_at": "2026-07-24T09:02:20Z",
        "finished_at": null,
        "created_at": "2026-07-24T09:02:19Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false
  },
  "request_id": "89790865-2810-4d66-9e92-b41dfcf986a3"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "VALIDATION_ERROR",
  "message": "执行角色取值无效",
  "data": {
    "field": "query.worker_role"
  },
  "request_id": "89790865-2810-4d66-9e92-b41dfcf986a3"
}
```

状态码与错误码：成功为 `200 PROJECT_WORKERS_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目不存在为 `404 PROJECT_NOT_FOUND`；筛选值无效为 `422 VALIDATION_ERROR`。

注意事项：`task_content`、`result_summary` 和 `error_message` 必须经过敏感信息过滤；接口不返回模型完整提示词和密钥。

### 6.3 查询角色消息

接口名称：查询项目角色消息。

用途：回放角色协作消息，并在 WebSocket 断线后补齐历史。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/messages`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `cursor` | integer(int64) | 否 | 无 | 上一页 `next_cursor` |
| `limit` | integer | 否 | `100` | 取值 1 至 500 |
| `stage_id` | string(uuid) | 否 | 无 | 按阶段筛选 |
| `worker_role` | string | 否 | 无 | 按角色筛选 |
| `message_type` | string | 否 | 无 | 按消息协议类型筛选 |
| `start_at` | string(date-time) | 否 | 无 | UTC 起始时间，包含边界 |
| `end_at` | string(date-time) | 否 | 无 | UTC 结束时间，不包含边界 |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_MESSAGES_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": 1842,
        "stage_id": "179a46a8-512d-4f0b-b563-2db1297876c0",
        "worker_task_id": "ff7d788f-b9b1-42a1-8fa1-6d15b932342c",
        "worker_role": "code_analyst",
        "message_type": "analysis_progress",
        "message_text": "已完成支付回调入口检查，正在验证订单查询权限边界。",
        "created_at": "2026-07-24T09:05:31Z"
      }
    ],
    "next_cursor": 1842,
    "has_more": false
  },
  "request_id": "44c993a3-a8b1-4da9-a2a3-29c7926754f6"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "TIME_RANGE_INVALID",
  "message": "结束时间必须晚于开始时间",
  "data": null,
  "request_id": "44c993a3-a8b1-4da9-a2a3-29c7926754f6"
}
```

状态码与错误码：成功为 `200 PROJECT_MESSAGES_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目不存在为 `404 PROJECT_NOT_FOUND`；游标无效为 `422 CURSOR_INVALID`；时间范围无效为 `422 TIME_RANGE_INVALID`。

注意事项：默认按 `(created_at, id)` 升序返回，便于前端追加展示。

### 6.4 查询运行日志

接口名称：查询项目运行日志。

用途：按时间窗口、级别、阶段和任务读取已脱敏的结构化日志。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/logs`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `cursor` | integer(int64) | 否 | 无 | 上一页 `next_cursor` |
| `limit` | integer | 否 | `100` | 取值 1 至 500 |
| `start_at` | string(date-time) | 否 | 无 | UTC 起始时间，包含边界 |
| `end_at` | string(date-time) | 否 | 无 | UTC 结束时间，不包含边界 |
| `log_level` | array[string] | 否 | 无 | 可重复查询参数，如 `log_level=warning&log_level=error` |
| `stage_id` | string(uuid) | 否 | 无 | 按阶段筛选 |
| `worker_task_id` | string(uuid) | 否 | 无 | 按角色任务筛选 |
| `request_id` | string(uuid) | 否 | 无 | 按请求链路筛选 |
| `order` | string | 否 | `asc` | `asc` 或 `desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_LOGS_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": 90215,
        "stage_id": "179a46a8-512d-4f0b-b563-2db1297876c0",
        "worker_task_id": "ff7d788f-b9b1-42a1-8fa1-6d15b932342c",
        "request_id": "16a2efad-6f67-4c13-9141-d43419969e39",
        "log_level": "info",
        "log_content": "已扫描 186 个源码文件，发现 4 个待验证候选项。",
        "created_at": "2026-07-24T09:05:40Z"
      }
    ],
    "next_cursor": 90215,
    "has_more": true
  },
  "request_id": "9960d6dc-303c-4091-bc58-ac68bbb6038a"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "CURSOR_INVALID",
  "message": "日志游标无效",
  "data": null,
  "request_id": "9960d6dc-303c-4091-bc58-ac68bbb6038a"
}
```

状态码与错误码：成功为 `200 PROJECT_LOGS_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目不存在为 `404 PROJECT_NOT_FOUND`；参数错误为 `422 VALIDATION_ERROR`、`TIME_RANGE_INVALID` 或 `CURSOR_INVALID`。

注意事项：

- 大范围查询必须同时受服务端最大时间窗口和 `limit` 限制。
- 日志不得包含密码、Cookie、Token、证书、仓库凭证、完整模型密钥或宿主机敏感路径。
- 归档日志文件不通过本接口直接暴露。

### 6.5 查询资源消耗

接口名称：查询项目资源消耗。

用途：按时间窗口返回 CPU、内存和 Token 累计采样。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/resources`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `cursor` | integer(int64) | 否 | 无 | 上一页 `next_cursor` |
| `limit` | integer | 否 | `300` | 取值 1 至 1000 |
| `start_at` | string(date-time) | 否 | 无 | UTC 起始时间，包含边界 |
| `end_at` | string(date-time) | 否 | 无 | UTC 结束时间，不包含边界 |
| `order` | string | 否 | `asc` | `asc` 或 `desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_RESOURCES_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": 33105,
        "runtime_id": "ec2ffb3b-8bec-424f-a36c-b56fe94fe474",
        "cpu_usage": 132.45,
        "memory_usage": 786432000,
        "token_count": 28450,
        "recorded_at": "2026-07-24T09:06:00Z"
      }
    ],
    "next_cursor": 33105,
    "has_more": true,
    "units": {
      "cpu_usage": "percent",
      "memory_usage": "bytes",
      "token_count": "count"
    }
  },
  "request_id": "39dd90ae-a894-450d-807b-166fcbed2f62"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "TIME_RANGE_INVALID",
  "message": "资源查询时间范围无效",
  "data": null,
  "request_id": "39dd90ae-a894-450d-807b-166fcbed2f62"
}
```

状态码与错误码：成功为 `200 PROJECT_RESOURCES_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目或运行实例不存在为 `404 PROJECT_NOT_FOUND` 或 `PROJECT_RUNTIME_NOT_FOUND`；参数错误为 `422 VALIDATION_ERROR`、`TIME_RANGE_INVALID` 或 `CURSOR_INVALID`。

注意事项：

- `memory_usage` 为字节数，`token_count` 为采样时累计值。
- CPU 使用率允许超过 100，表示多核总使用率。
- 前端绘图应按返回时间顺序处理，较大窗口由服务端限制点数或降采样。

## 7. 评估结果接口

### 7.1 查询漏洞列表

接口名称：查询项目漏洞列表。

用途：分页查询漏洞摘要，并按风险等级和验证状态筛选。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/vulnerabilities`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `page` | integer | 否 | `1` | 页码 |
| `page_size` | integer | 否 | `20` | 每页 1 至 100 条 |
| `risk_level` | array[string] | 否 | 无 | 可指定多个风险等级 |
| `verify_status` | array[string] | 否 | 无 | 可指定多个验证状态 |
| `keyword` | string | 否 | 无 | 匹配漏洞编号或标题 |
| `file_path` | string | 否 | 无 | 按项目内相对路径前缀筛选 |
| `sort` | string | 否 | `risk_level:desc` | `risk_level:desc`、`created_at:asc` 或 `created_at:desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "VULNERABILITY_LIST_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "a18e7797-19bd-447d-8ab2-360922ca4e95",
        "vuln_code": "ASA-2026-0004",
        "vuln_title": "订单详情接口存在水平越权",
        "rule_type": "broken_object_level_authorization",
        "risk_level": "high",
        "file_path": "app/api/orders.py",
        "line_start": 84,
        "line_end": 96,
        "verify_status": "verified",
        "created_at": "2026-07-24T09:07:14Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 4,
    "has_next": false
  },
  "request_id": "aa9ac739-4482-4765-a25c-5ef32ec44037"
}
```

失败响应：`422 Unprocessable Entity`

```json
{
  "code": "VALIDATION_ERROR",
  "message": "风险等级取值无效",
  "data": {
    "field": "query.risk_level"
  },
  "request_id": "aa9ac739-4482-4765-a25c-5ef32ec44037"
}
```

状态码与错误码：成功为 `200 VULNERABILITY_LIST_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目不存在为 `404 PROJECT_NOT_FOUND`；筛选值无效为 `422 VALIDATION_ERROR`。

注意事项：风险排序固定为 `critical`、`high`、`medium`、`low`、`info`，同等级使用 `created_at` 和 `id` 保证稳定顺序。

### 7.2 查询漏洞详情

接口名称：查询漏洞详情。

用途：返回漏洞影响、触发条件、证据、复现步骤、验证代码和源码位置。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/vulnerabilities/{vulnerability_id}`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |
| `vulnerability_id` | string(uuid) | 是 | 无 | 漏洞标识，必须属于当前项目 |

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "VULNERABILITY_DETAIL_OK",
  "message": "查询成功",
  "data": {
    "id": "a18e7797-19bd-447d-8ab2-360922ca4e95",
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "vuln_code": "ASA-2026-0004",
    "vuln_title": "订单详情接口存在水平越权",
    "rule_type": "broken_object_level_authorization",
    "risk_level": "high",
    "file_path": "app/api/orders.py",
    "line_start": 84,
    "line_end": 96,
    "impact_text": "已登录用户可读取其他用户的订单金额、商品和收货信息。",
    "condition_text": "攻击者拥有普通账户，并能获取或猜测其他订单编号。",
    "evidence_text": "订单查询仅按 order_id 过滤，未同时校验 owner_id。",
    "verify_status": "verified",
    "reproduce_steps_text": "1. 使用用户 A 登录。\\n2. 请求用户 B 的订单编号。\\n3. 接口返回 200 及完整订单信息。",
    "verify_code_text": "response = client.get('/api/orders/ORD-10082', cookies=user_a_cookie)\\nassert response.status_code == 200",
    "discovered_by_task_id": "ff7d788f-b9b1-42a1-8fa1-6d15b932342c",
    "verified_by_task_id": "0c61ea5d-cad7-4cf0-b779-276847e2b3b6",
    "created_at": "2026-07-24T09:07:14Z",
    "updated_at": "2026-07-24T09:09:30Z"
  },
  "request_id": "a527d6ca-a42a-432f-b2af-b3a2e14d251f"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "VULNERABILITY_NOT_FOUND",
  "message": "漏洞不存在",
  "data": null,
  "request_id": "a527d6ca-a42a-432f-b2af-b3a2e14d251f"
}
```

状态码与错误码：成功为 `200 VULNERABILITY_DETAIL_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目或漏洞不存在为 `404 PROJECT_NOT_FOUND` 或 `VULNERABILITY_NOT_FOUND`；UUID 无效为 `422 VALIDATION_ERROR`。

注意事项：

- 证据、复现步骤和验证代码按纯文本返回；前端不得直接作为 HTML 执行。
- 接口不得返回 `evidence_fingerprint` 等内部去重实现字段。
- 服务端必须校验漏洞与路径中的 `project_id` 一致，禁止跨项目访问。

### 7.3 查询攻击路径列表

接口名称：查询项目攻击路径列表。

用途：分页返回攻击路径摘要、步骤数、关联漏洞和最终影响。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/attack-paths`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `page` | integer | 否 | `1` | 页码 |
| `page_size` | integer | 否 | `20` | 每页 1 至 100 条 |
| `keyword` | string | 否 | 无 | 匹配路径编号或标题 |
| `sort` | string | 否 | `created_at:desc` | `created_at:asc` 或 `created_at:desc` |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "ATTACK_PATH_LIST_OK",
  "message": "查询成功",
  "data": {
    "items": [
      {
        "id": "08092b23-262c-4855-bacf-4d2c1de079fe",
        "path_code": "PATH-2026-001",
        "path_title": "越权读取订单并伪造支付回调",
        "path_summary": "攻击者先读取他人订单信息，再利用未校验签名的回调接口修改订单状态。",
        "final_impact_text": "订单状态和资金结算数据可能被篡改。",
        "step_count": 2,
        "vulnerability_codes": [
          "ASA-2026-0004",
          "ASA-2026-0007"
        ],
        "created_at": "2026-07-24T09:11:42Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false
  },
  "request_id": "559cfc06-a5b3-46de-b770-58086850560b"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "项目不存在",
  "data": null,
  "request_id": "559cfc06-a5b3-46de-b770-58086850560b"
}
```

状态码与错误码：成功为 `200 ATTACK_PATH_LIST_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目不存在为 `404 PROJECT_NOT_FOUND`；分页或排序无效为 `422 VALIDATION_ERROR`。

注意事项：路径列表只返回摘要；完整步骤通过详情接口获取。

### 7.4 查询攻击路径详情

接口名称：查询攻击路径详情。

用途：按利用顺序返回路径步骤及同项目关联漏洞。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/attack-paths/{attack_path_id}`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |
| `attack_path_id` | string(uuid) | 是 | 无 | 攻击路径标识，必须属于当前项目 |

查询参数：无。

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "ATTACK_PATH_DETAIL_OK",
  "message": "查询成功",
  "data": {
    "id": "08092b23-262c-4855-bacf-4d2c1de079fe",
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "path_code": "PATH-2026-001",
    "path_title": "越权读取订单并伪造支付回调",
    "path_summary": "攻击者先读取他人订单信息，再利用未校验签名的回调接口修改订单状态。",
    "final_impact_text": "订单状态和资金结算数据可能被篡改。",
    "steps": [
      {
        "step_order": 1,
        "step_text": "利用水平越权读取目标订单编号、金额和当前状态。",
        "vulnerability": {
          "id": "a18e7797-19bd-447d-8ab2-360922ca4e95",
          "vuln_code": "ASA-2026-0004",
          "vuln_title": "订单详情接口存在水平越权",
          "risk_level": "high",
          "verify_status": "verified"
        }
      },
      {
        "step_order": 2,
        "step_text": "构造缺少有效签名的支付回调，将目标订单标记为已支付。",
        "vulnerability": {
          "id": "3d014a8b-d5df-4795-bc02-fb5f7fd38c79",
          "vuln_code": "ASA-2026-0007",
          "vuln_title": "支付回调未校验签名",
          "risk_level": "critical",
          "verify_status": "verified"
        }
      }
    ],
    "created_at": "2026-07-24T09:11:42Z"
  },
  "request_id": "9ea412a9-aedc-4080-a8de-20d5e1113d22"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "ATTACK_PATH_NOT_FOUND",
  "message": "攻击路径不存在",
  "data": null,
  "request_id": "9ea412a9-aedc-4080-a8de-20d5e1113d22"
}
```

状态码与错误码：成功为 `200 ATTACK_PATH_DETAIL_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目或路径不存在为 `404 PROJECT_NOT_FOUND` 或 `ATTACK_PATH_NOT_FOUND`；UUID 无效为 `422 VALIDATION_ERROR`。

注意事项：步骤必须按 `step_order` 从 1 连续升序返回，每个漏洞必须属于当前项目。

### 7.5 查询报告

接口名称：查询项目报告。

用途：查询最新或指定版本报告的状态，并在就绪后返回 Markdown 与已清理 HTML。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/report`

认证方式：Cookie 会话认证和项目访问权限。

请求头：使用受保护查询接口的通用请求头。

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `version` | integer | 否 | 最新版本 | 正整数报告版本 |

请求体：无。

成功响应：`200 OK`

```json
{
  "code": "PROJECT_REPORT_OK",
  "message": "查询成功",
  "data": {
    "id": "ea6dce37-f642-48ad-98d5-c0ee546469ff",
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "version": 1,
    "report_status": "ready",
    "report_markdown": "# 商城支付服务安全评估报告\\n\\n## 评估结论\\n\\n本次评估发现 1 个严重风险和 3 个高风险。",
    "report_html": "<h1>商城支付服务安全评估报告</h1><h2>评估结论</h2><p>本次评估发现 1 个严重风险和 3 个高风险。</p>",
    "download_available": true,
    "content_sha256": "45d3fce3ba431454b9f6c24e29f509340ec1dc82233a24ebd7f6c29d58547fc2",
    "error_message": null,
    "created_at": "2026-07-24T09:14:08Z",
    "updated_at": "2026-07-24T09:14:22Z"
  },
  "request_id": "6269fb20-28b7-4fe4-9e89-77ff0c64d300"
}
```

报告尚未完成时仍返回 `200`：

```json
{
  "code": "PROJECT_REPORT_OK",
  "message": "报告生成中",
  "data": {
    "id": "ea6dce37-f642-48ad-98d5-c0ee546469ff",
    "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
    "version": 1,
    "report_status": "generating",
    "report_markdown": null,
    "report_html": null,
    "download_available": false,
    "content_sha256": null,
    "error_message": null,
    "created_at": "2026-07-24T09:14:08Z",
    "updated_at": "2026-07-24T09:14:08Z"
  },
  "request_id": "6269fb20-28b7-4fe4-9e89-77ff0c64d300"
}
```

失败响应：`404 Not Found`

```json
{
  "code": "REPORT_NOT_FOUND",
  "message": "项目报告尚不存在",
  "data": null,
  "request_id": "6269fb20-28b7-4fe4-9e89-77ff0c64d300"
}
```

状态码与错误码：成功为 `200 PROJECT_REPORT_OK`；权限不足为 `403 PROJECT_ACCESS_DENIED`；项目或报告不存在为 `404 PROJECT_NOT_FOUND` 或 `REPORT_NOT_FOUND`；版本无效为 `422 VALIDATION_ERROR`。

注意事项：

- `report_html` 必须由后端执行 HTML 清理后返回，禁止脚本、事件属性和危险 URL。
- `report_file_path` 是内部逻辑键，不通过外部 API 返回。
- `report_status=failed` 时可返回脱敏后的 `error_message`，已保存的漏洞和攻击路径不受影响。

### 7.6 下载报告

接口名称：下载项目报告。

用途：下载最新或指定版本的已就绪报告文件。

请求方式：`GET`

URL：`/api/v1/projects/{project_id}/report/download`

认证方式：Cookie 会话认证和项目访问权限。

请求头：

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Cookie` | string | 是 | 无 | 登录会话 |
| `Accept` | string | 否 | `text/markdown` | 当前 MVP 支持 `text/markdown` 和 `text/html` |
| `X-Request-ID` | string(uuid) | 否 | 服务端生成 | 链路标识 |

路径参数：`project_id`，string(uuid)，必填，无默认值。

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `version` | integer | 否 | 最新版本 | 正整数报告版本 |
| `format` | string | 否 | `markdown` | `markdown` 或 `html` |

请求体：无。

成功响应：`200 OK`

```http
Content-Type: text/markdown; charset=utf-8
Content-Disposition: attachment; filename="asa-report-a8c3f3e0-v1.md"
Content-Length: 48216
Digest: sha-256=RdP847pDFDQ=
X-Request-ID: 49ca363a-8ad1-4b91-a31c-437e031276fd
```

响应体为报告文件字节流，不使用统一 JSON 包装。

失败响应：`409 Conflict`

```json
{
  "code": "REPORT_NOT_READY",
  "message": "报告尚未生成完成",
  "data": {
    "report_status": "generating"
  },
  "request_id": "49ca363a-8ad1-4b91-a31c-437e031276fd"
}
```

状态码与错误码：

| HTTP 状态 | 业务码 | 场景 |
| ---: | --- | --- |
| 200 | 文件字节流 | 下载成功 |
| 403 | `PROJECT_ACCESS_DENIED` | 无项目访问权限 |
| 404 | `PROJECT_NOT_FOUND`、`REPORT_NOT_FOUND`、`REPORT_FILE_NOT_FOUND` | 项目、版本或物理文件不存在 |
| 409 | `REPORT_NOT_READY` | 报告状态不是 `ready` |
| 422 | `VALIDATION_ERROR` | 版本或格式无效 |
| 500 | `REPORT_INTEGRITY_ERROR` | 文件摘要与元数据不一致 |

注意事项：

- 每次下载必须重新校验项目权限，不提供永久公开 URL。
- 文件名必须经过安全规范化，禁止响应头注入。
- 服务端读取的是受控逻辑键，不接受客户端传入文件路径。

## 8. WebSocket 实时接口

### 8.1 订阅项目实时事件

接口名称：订阅项目实时事件。

用途：实时接收项目状态、阶段、角色、消息、日志、资源、漏洞和报告事件。

请求方式：`WS`

URL：`/api/v1/projects/{project_id}/stream`

认证方式：WebSocket 握手时校验 `asa_session` Cookie 和项目访问权限。

请求头：

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `Cookie` | string | 是 | 无 | 浏览器会话 Cookie |
| `Sec-WebSocket-Protocol` | string | 否 | `asa.v1` | 客户端请求的协议版本 |
| `X-Request-ID` | string(uuid) | 否 | 服务端生成 | 非浏览器客户端可提供 |

路径参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |

查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `after_sequence` | integer(int64) | 否 | `0` | 仅推送项目内序号大于该值的事件，用于断线续传 |

请求体：WebSocket 握手无请求体。

握手成功：`101 Switching Protocols`

服务端事件包：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `event_id` | string(uuid) | 是 | 无 | 全局唯一事件标识 |
| `sequence` | integer(int64) | 是 | 无 | 项目内严格递增序号 |
| `event_type` | string | 是 | 无 | 事件类型 |
| `project_id` | string(uuid) | 是 | 无 | 项目标识 |
| `occurred_at` | string(date-time) | 是 | 无 | 事件实际发生时间 |
| `data` | object | 是 | `{}` | 对应事件载荷 |

事件示例：

```json
{
  "event_id": "e61adea9-5c4e-4c04-b51f-d4df70d8948d",
  "sequence": 1024,
  "event_type": "stage_status",
  "project_id": "a8c3f3e0-531f-4df6-9622-f0ca517ad681",
  "occurred_at": "2026-07-24T09:02:19Z",
  "data": {
    "stage_id": "179a46a8-512d-4f0b-b563-2db1297876c0",
    "stage_name": "code_analysis",
    "stage_status": "running"
  }
}
```

事件类型与最小载荷：

| `event_type` | `data` 必含字段 | 说明 |
| --- | --- | --- |
| `project_status` | `project_status`、`stop_requested_at` | 项目状态或停止意图变化 |
| `stage_status` | `stage_id`、`stage_name`、`stage_status` | 阶段状态变化 |
| `worker_status` | `worker_task_id`、`worker_role`、`task_status` | 角色任务变化 |
| `chat_message` | `message_id`、`worker_role`、`message_type`、`message_text` | 新角色消息 |
| `runtime_log` | `log_id`、`log_level`、`log_content` | 新运行日志 |
| `resource_usage` | `resource_usage_id`、`cpu_usage`、`memory_usage`、`token_count` | 新资源采样 |
| `vulnerability_found` | `vulnerability_id`、`vuln_code`、`vuln_title`、`risk_level` | 新漏洞摘要 |
| `report_ready` | `report_id`、`version`、`report_status` | 报告已就绪 |

客户端心跳请求：

```json
{
  "type": "ping",
  "sent_at": "2026-07-24T09:06:30Z"
}
```

服务端心跳响应：

```json
{
  "type": "pong",
  "server_time": "2026-07-24T09:06:30Z"
}
```

握手失败响应：`401 Unauthorized`

```json
{
  "code": "AUTH_REQUIRED",
  "message": "请先登录",
  "data": null,
  "request_id": "8fa91d05-1043-4ba6-9b84-b6acf2265583"
}
```

握手状态与关闭码：

| 阶段 | 状态或关闭码 | 业务码 | 场景 |
| --- | ---: | --- | --- |
| 握手 | 101 | 无 | 连接成功 |
| 握手 | 401 | `AUTH_REQUIRED` | 未登录或会话过期 |
| 握手 | 403 | `PROJECT_ACCESS_DENIED` | 无项目访问权限 |
| 握手 | 404 | `PROJECT_NOT_FOUND` | 项目不存在 |
| 握手 | 422 | `VALIDATION_ERROR` | UUID 或序号无效 |
| 连接后 | 4001 | `SESSION_EXPIRED` | 会话在连接期间过期 |
| 连接后 | 4003 | `PROJECT_ACCESS_DENIED` | 权限被撤销 |
| 连接后 | 4008 | `RATE_LIMITED` | 客户端消息或重连过于频繁 |
| 连接后 | 4009 | `EVENT_GAP_TOO_LARGE` | 请求序号超出实时流保留窗口 |
| 连接后 | 4010 | `CLIENT_TOO_SLOW` | 发送缓冲超过上限 |
| 连接后 | 1011 | `INTERNAL_ERROR` | 服务端内部错误 |

注意事项：

- 客户端使用 `event_id` 去重，并持久记录最后处理成功的 `sequence`。
- 收到 `EVENT_GAP_TOO_LARGE` 后，应调用项目详情、阶段、任务、消息、日志、资源和结果接口进行全量补偿，再以最新序号重连。
- WebSocket 仅用于加速展示，PostgreSQL 中的业务记录才是权威状态。
- 服务端应设置心跳、空闲超时、单连接发送缓冲和慢客户端断开策略。
- 日志高峰期间允许服务端合并资源事件，但不得改变项目状态和漏洞事件的语义。

## 9. 业务错误码汇总

### 9.1 系统与认证

| 错误码 | HTTP 状态 | 说明 |
| --- | ---: | --- |
| `SYSTEM_ALREADY_INITIALIZED` | 409 | 系统已初始化 |
| `SYSTEM_NOT_INITIALIZED` | 409 | 系统尚未初始化 |
| `INVALID_CREDENTIALS` | 401 | 用户名或密码错误 |
| `ADMIN_REQUIRED` | 403 | 仅管理员可执行 |
| `SYSTEM_CONFIG_NOT_FOUND` | 404 | 尚无生效配置 |
| `CONFIG_VERSION_CONFLICT` | 409 | 配置乐观锁版本冲突 |

### 9.2 项目

| 错误码 | HTTP 状态 | 说明 |
| --- | ---: | --- |
| `PROJECT_NOT_FOUND` | 404 | 项目不存在 |
| `PROJECT_ACCESS_DENIED` | 403 | 无项目访问或操作权限 |
| `PROJECT_STATUS_CONFLICT` | 409 | 当前状态不允许指定操作 |
| `PROJECT_NOT_RUNNING` | 409 | 停止目标不是运行状态 |
| `PROJECT_CAPACITY_EXCEEDED` | 409 | 达到并发项目上限 |
| `PROJECT_DELETE_FORBIDDEN` | 409 | 项目运行中，不能删除 |
| `PROJECT_NAME_CONFIRMATION_MISMATCH` | 409 | 删除确认名称不匹配 |
| `PROJECT_RUNTIME_NOT_FOUND` | 404 | 项目尚无运行实例 |
| `SOURCE_PATH_INVALID` | 422 | 源码路径或仓库地址格式不合法 |
| `SOURCE_CREDENTIAL_FORBIDDEN` | 422 | 仓库地址包含内联凭证 |
| `SOURCE_INACCESSIBLE` | 409 | 启动时源码不可访问 |
| `ENVIRONMENT_TYPE_DISABLED` | 409 | 隔离环境类型未启用 |

### 9.3 结果与文件

| 错误码 | HTTP 状态 | 说明 |
| --- | ---: | --- |
| `VULNERABILITY_NOT_FOUND` | 404 | 漏洞不存在或不属于当前项目 |
| `ATTACK_PATH_NOT_FOUND` | 404 | 攻击路径不存在或不属于当前项目 |
| `REPORT_NOT_FOUND` | 404 | 报告或指定版本不存在 |
| `REPORT_NOT_READY` | 409 | 报告尚未就绪 |
| `REPORT_FILE_NOT_FOUND` | 404 | 报告元数据存在但文件不存在 |
| `REPORT_INTEGRITY_ERROR` | 500 | 报告文件摘要校验失败 |

## 10. 安全与实现注意事项

### 10.1 输入校验

- 所有路径参数 UUID 必须在进入数据访问层前校验。
- 所有枚举值使用本文档规定的闭集，未知值返回 `422 VALIDATION_ERROR`。
- `source_path`、源码文件路径和制品逻辑键必须规范化，并校验真实访问范围仍位于授权项目目录。
- 仓库地址不得包含明文密码、Token 或其他内联凭证。
- 日志、消息、证据、报告和配置 JSON 在入库前执行字段白名单、长度限制和敏感信息过滤。
- 模型自由文本不得直接拼接为 Shell 命令。

### 10.2 输出安全

- 错误响应不得包含 Python 堆栈、SQL、宿主机绝对路径、容器 Socket、密钥或完整内部异常。
- 报告 HTML 必须经过允许列表清理；Markdown、日志、证据和验证代码默认按不可信文本处理。
- 下载文件名执行字符白名单处理，并设置安全的 `Content-Disposition`。
- 所有项目子资源查询必须同时校验资源 `project_id` 和当前用户权限。

### 10.3 缓存

- 认证、项目详情、过程状态和结果接口默认返回 `Cache-Control: no-store`。
- 报告下载可以使用与 `content_sha256` 对应的强 ETag，但命中缓存前仍需完成身份和项目权限校验。
- 浏览器或代理不得缓存登录与初始化请求体。

### 10.4 速率限制

登录、初始化、启动、停止、删除、配置更新和 WebSocket 重连必须限流。触发限制时返回：

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

```json
{
  "code": "RATE_LIMITED",
  "message": "请求过于频繁，请稍后重试",
  "data": {
    "retry_after_seconds": 30
  },
  "request_id": "c95f2a10-0ec8-4aa5-92af-a67f4f79bd49"
}
```

具体阈值由部署和安全评审确定，不在接口契约中写死。

### 10.5 一致性与审计

- 项目、阶段、任务和报告状态变更与 `domain_events` 写入必须位于同一数据库事务。
- WebSocket 或 Redis 投递失败不得回滚已提交业务状态。
- 初始化、登录成功与连续失败、越权、启动、停止、删除、配置更新和管理员访问敏感项目均写入脱敏审计日志。
- `request_id`、`project_id`、`stage_id` 和 `worker_task_id` 用于跨 API、任务、日志和事件关联。

## 11. 前端调用顺序

### 11.1 首次初始化

1. 调用 `GET /api/v1/system/status`。
2. 当 `initialized=false` 时调用 `POST /api/v1/system/init`。
3. 初始化成功后调用 `POST /api/v1/system/login`。
4. 登录成功后读取 `GET /api/v1/system/config` 或项目列表。

### 11.2 创建并启动项目

1. 管理员配置可用环境类型。
2. 用户调用 `POST /api/v1/projects` 创建项目。
3. 用户生成并保存一个 `Idempotency-Key`。
4. 调用 `POST /api/v1/projects/{project_id}/start`。
5. 建立 WebSocket，查询项目详情和阶段状态作为初始快照。
6. 使用事件增量更新页面；连接中断时使用 REST 接口补偿。

### 11.3 停止与删除

1. 对 `running` 项目调用停止接口，并保留原幂等键用于网络重试。
2. 等待项目通过 WebSocket 或详情接口收敛为 `stopped`。
3. 用户二次确认项目名称。
4. 使用新的幂等键调用删除接口。

## 12. 待确认事项

- 用户管理接口不在当前 MVP 需求中；除初始化管理员外，普通用户账户的创建、禁用和密码重置流程待确认。
- 私有仓库凭证托管方式和凭证引用字段尚未定义，本接口禁止直接接收或保存明文凭证。
- `environment_type` 的最终值域由部署镜像与管理员配置确定，本文示例值不构成生产默认值。
- 会话有效期、密码强度、登录失败锁定、速率限制阈值和最大查询时间窗口由安全与部署评审确定。
- 项目共享授权模型尚未定义；MVP 按创建者归属控制。
- 报告默认支持 Markdown 和 HTML；PDF 未确认，不进入当前接口值域。
- `chat_messages.message_type` 尚未形成闭集，当前作为非空协议标识处理。
- 异步删除失败项的管理员查询入口尚未定义；实现阶段需在不增加无依据业务表的前提下补充运维可观测方案。
- WebSocket 心跳周期、空闲超时、事件保留窗口和发送缓冲上限由容量测试确定。
