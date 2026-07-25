# ASA System API 接口清单

> 用于前端验收测试，逐一验证每个接口是否正常工作。
>
> **Base URL**: `http://127.0.0.1:8000/api/v1`
>
> **认证方式**: Cookie（`asa_session` HttpOnly + `asa_csrf`），写操作需带 `X-CSRF-Token` 请求头。
>
> **统一响应格式**:
> ```json
> { "code": "BUSINESS_CODE", "message": "中文提示", "data": {...}, "request_id": "uuid" }
> ```

## 验收结果总览

> 📅 测试时间: 2026-07-24 | 🟢 后端服务 + PostgreSQL + Redis 均正常

| 模块 | 接口数 | 通过 | 状态 |
|---|---|---|---|
| 系统与认证 | 4 | 4 | ✅ 全部通过 |
| 账号管理 | 7 | 7 | ✅ 全部通过 |
| 项目管理 | 6 | 6 | ✅ 全部通过 |
| 调度与 AI 角色 | 2 | 2 | ✅ 全部通过 |
| **已实现合计** | **19** | **19** | ✅ |
| 漏洞/攻击路径/报告/监控/知识库/配置 | 18 | 0 | ⚠️ 后端未实现 |

---

## 一、系统与认证 `/api/v1/system`

### 1.1 查询系统初始化状态

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/system/status` |
| **认证** | 不需要 |
| **请求体** | 无 |
| **Query 参数** | 无 |
| **成功码** | `SYSTEM_STATUS_OK` |
| **data** | `{ "initialized": true }` |

```bash
curl http://127.0.0.1:8000/api/v1/system/status | python -m json.tool
```

---

### 1.2 初始化管理员账户

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/system/init` |
| **认证** | 不需要（仅未初始化时可用） |
| **请求体** | `{ "username": "admin", "password": "your-password" }` |
| **成功码** | `SYSTEM_INITIALIZED` (201) |
| **data** | `{ "admin": { "id": "...", "username": "...", "role": "admin", "status": "active" } }` |
| **说明** | 幂等，已有管理员时返回 409 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/init \
  -H "Content-Type: application/json" \
  -d '{"username": "admin2", "password": "Test-12345678"}'
```

---

### 1.3 用户登录

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/system/login` |
| **认证** | 不需要 |
| **请求体** | `{ "username": "admin", "password": "your-password" }` |
| **成功码** | `LOGIN_SUCCESS` |
| **data** | `{ "user": { "id": "...", "username": "...", "role": "admin", "status": "active" }, "expires_at": "ISO8601" }` |
| **Cookie** | 响应设置 `asa_session` (HttpOnly) + `asa_csrf` |

```bash
curl -v -X POST http://127.0.0.1:8000/api/v1/system/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  -c /tmp/cookies.txt
```

> 💡 后续需要认证的请求加上 `-b /tmp/cookies.txt`

---

### 1.4 退出登录

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/system/logout` |
| **认证** | 需要（Cookie） |
| **请求体** | 无 |
| **成功码** | `LOGOUT_SUCCESS` |
| **data** | `null` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/system/logout -b /tmp/cookies.txt
```

---

## 二、账号管理 `/api/v1/users`

> 以下接口除标注外，均需要**管理员**权限。

### 2.1 获取当前用户信息

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/users/me` |
| **认证** | 需要（任意已登录用户） |
| **请求体** | 无 |
| **成功码** | `USER_DETAIL_OK` |
| **data** | `{ "id": "...", "username": "...", "role": "admin", "status": "active", "created_at": "ISO8601", "updated_at": "ISO8601" }` |

```bash
curl http://127.0.0.1:8000/api/v1/users/me -b /tmp/cookies.txt | python -m json.tool
```

---

### 2.2 修改自己的密码

| 项目 | 内容 |
|---|---|
| **方法** | `PUT` |
| **路径** | `/api/v1/users/me/password` |
| **认证** | 需要（任意已登录用户） |
| **请求体** | `{ "old_password": "current", "new_password": "new-pass-8chars+" }` |
| **成功码** | `PASSWORD_CHANGED` |
| **data** | `null` |

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/users/me/password \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{"old_password": "old", "new_password": "New-pass-123"}'
```

---

### 2.3 管理员 - 用户列表（分页）

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/users` |
| **认证** | 管理员 |
| **Query 参数** | `page` (≥1, 默认1), `page_size` (1-100, 默认20), `role` (user\|admin), `status` (active\|disabled), `keyword` (≤64字符) |
| **成功码** | `USER_LIST_OK` |
| **data** | `{ "items": [...], "page": 1, "page_size": 20, "total": 1, "has_next": false }` |

```bash
curl "http://127.0.0.1:8000/api/v1/users?page=1&page_size=10" \
  -b /tmp/cookies.txt | python -m json.tool
```

---

### 2.4 管理员 - 创建用户

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/users` |
| **认证** | 管理员 |
| **请求体** | `{ "username": "newuser" (1-64字符), "password": "pass1234" (8-128字符), "role": "user"\|"admin" }` |
| **成功码** | `USER_CREATED` (201) |
| **data** | `{ "id": "...", "username": "...", "role": "user", "status": "active", "created_at": "ISO8601", "updated_at": "ISO8601" }` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{"username": "testuser", "password": "Test-12345678", "role": "user"}'
```

---

### 2.5 管理员 - 查看用户详情

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/users/{user_id}` |
| **认证** | 管理员 |
| **成功码** | `USER_DETAIL_OK` |
| **data** | `{ "id": "...", "username": "...", "role": "user", "status": "active", "created_at": "ISO8601", "updated_at": "ISO8601" }` |

```bash
curl http://127.0.0.1:8000/api/v1/users/<user-uuid> -b /tmp/cookies.txt | python -m json.tool
```

---

### 2.6 管理员 - 更新用户（角色/状态）

| 项目 | 内容 |
|---|---|
| **方法** | `PUT` |
| **路径** | `/api/v1/users/{user_id}` |
| **认证** | 管理员 |
| **请求体** | `{ "role": "user"\|"admin" }` 和/或 `{ "status": "active"\|"disabled" }`（至少一个） |
| **成功码** | `USER_UPDATED` |
| **data** | 更新后的用户详情 |

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/users/<user-uuid> \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{"status": "disabled"}'
```

---

### 2.7 管理员 - 重置用户密码

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/users/{user_id}/reset-password` |
| **认证** | 管理员 |
| **请求体** | `{ "new_password": "new-pass" (8-128字符) }` |
| **成功码** | `PASSWORD_RESET` |
| **data** | `{ "user_id": "..." }` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users/<user-uuid>/reset-password \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{"new_password": "New-Pass-1234"}'
```

---

## 三、项目管理 `/api/v1/projects`

> 所有接口需要登录认证。
> 写操作（start/stop/delete）需要 `Idempotency-Key` 请求头（8-128 字符）。

### 3.1 创建项目

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/projects` |
| **认证** | 需要 |
| **请求体** | `{ "project_name" (1-128), "source_type" ("local"\|"repository"), "source_path" (1-2048), "task_content" (1-20000), "environment_type" (1-64, 正则 ^[a-z][a-z0-9_-]{0,63}$) }` |
| **成功码** | `PROJECT_CREATED` (201) |
| **data** | 项目完整信息 |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -d '{
    "project_name": "测试项目",
    "source_type": "local",
    "source_path": "test-project",
    "task_content": "全面安全评估",
    "environment_type": "python312"
  }'
```

---

### 3.2 项目列表（分页）

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/projects` |
| **认证** | 需要 |
| **Query 参数** | `page` (≥1), `page_size` (1-100), `project_status` (created\|running\|completed\|failed\|stopped), `source_type` (local\|repository), `keyword` (≤128), `sort` (created_at:desc\|created_at:asc\|updated_at:desc\|updated_at:asc) |
| **成功码** | `PROJECT_LIST_OK` |
| **data** | `{ "items": [...], "page": 1, "page_size": 20, "total": 1, "has_next": false }` |

```bash
curl "http://127.0.0.1:8000/api/v1/projects?page=1&page_size=10&sort=created_at:desc" \
  -b /tmp/cookies.txt | python -m json.tool
```

---

### 3.3 项目详情

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/projects/{project_id}` |
| **认证** | 需要（本人或管理员） |
| **成功码** | `PROJECT_DETAIL_OK` |
| **data** | 项目完整详情，含 `runtime`（容器状态）、`statistics`（漏洞/攻击路径/任务统计）、`report_status` |

```bash
curl http://127.0.0.1:8000/api/v1/projects/<project-uuid> -b /tmp/cookies.txt | python -m json.tool
```

---

### 3.4 启动项目

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/projects/{project_id}/start` |
| **认证** | 需要 |
| **请求头** | `Idempotency-Key: unique-key-here-123` (8-128字符) |
| **请求体** | `{}`（空对象） |
| **成功码** | `PROJECT_START_ACCEPTED` (202) |
| **data** | `{ "project_id": "...", "operation": "start", "project_status": "running", "accepted_at": "ISO8601" }` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/<project-uuid>/start \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: start-test-$(date +%s)" \
  -b /tmp/cookies.txt \
  -d '{}'
```

---

### 3.5 停止项目

| 项目 | 内容 |
|---|---|
| **方法** | `POST` |
| **路径** | `/api/v1/projects/{project_id}/stop` |
| **认证** | 需要 |
| **请求头** | `Idempotency-Key: unique-key` |
| **请求体** | `{ "reason": "测试停止" }` (可选，≤500字符) |
| **成功码** | `PROJECT_STOP_ACCEPTED` (202) |
| **data** | `{ "project_id": "...", "operation": "stop", "project_status": "...", "stop_requested_at": "ISO8601" }` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/<project-uuid>/stop \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: stop-test-$(date +%s)" \
  -b /tmp/cookies.txt \
  -d '{"reason": "手动停止测试"}'
```

---

### 3.6 删除项目

| 项目 | 内容 |
|---|---|
| **方法** | `DELETE` |
| **路径** | `/api/v1/projects/{project_id}` |
| **认证** | 需要 |
| **请求头** | `Idempotency-Key: unique-key` |
| **请求体** | `{ "confirm_project_name": "测试项目" }`（必须与当前项目名完全一致） |
| **成功码** | `PROJECT_DELETE_ACCEPTED` (202) |
| **说明** | 仅非 running 状态可删除 |

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/projects/<project-uuid> \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: delete-test-$(date +%s)" \
  -b /tmp/cookies.txt \
  -d '{"confirm_project_name": "测试项目"}'
```

---

## 四、调度与 AI 角色 `/api/v1/projects/{project_id}/...`

> 实时查看分析进度、AI 角色任务、对话消息和运行日志。

### 4.1 查看运行阶段

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/projects/{project_id}/stages` |
| **认证** | 需要 |
| **成功码** | `PROJECT_STAGES_OK` |
| **data** | `{ "items": [{ "id": "...", "stage_name": "environment_scan", "stage_order": 1, "stage_status": "idle\|running\|success\|failed", "started_at": "ISO8601\|null", "finished_at": "ISO8601\|null", "error_message": "..." }] }` |

**5 个固定阶段顺序**:
1. `environment_scan` — 环境扫描
2. `code_analysis` — 代码分析
3. `vulnerability_verify` — 漏洞验证
4. `report_generate` — 报告生成
5. `done` — 完成

```bash
curl http://127.0.0.1:8000/api/v1/projects/<project-uuid>/stages \
  -b /tmp/cookies.txt | python -m json.tool
```

---

### 4.2 查看 Worker 任务（分页）

| 项目 | 内容 |
|---|---|
| **方法** | `GET` |
| **路径** | `/api/v1/projects/{project_id}/workers` |
| **认证** | 需要 |
| **Query 参数** | `page` (≥1), `page_size` (1-100), `stage_id` (uuid), `worker_role` (general\|environment_inspector\|code_analyst\|vulnerability_verifier\|report_editor\|operations_assistant), `task_status` (idle\|running\|success\|failed), `sort` (created_at:asc\|created_at:desc) |
| **成功码** | `PROJECT_WORKERS_OK` |
| **data** | 分页任务列表，含 `task_content`（已脱敏）、`result_summary`、`attempt_count` 等 |

```bash
curl "http://127.0.0.1:8000/api/v1/projects/<project-uuid>/workers?page=1&page_size=10" \
  -b /tmp/cookies.txt | python -m json.tool
```

---

## 五、前端已调用但后端未实现的接口

> ⚠️ 以下接口前端代码中有调用，但后端路由**尚未实现**。点击对应页面会报 404 或网络错误。

### 5.1 漏洞管理

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/vulnerabilities` | 漏洞列表（分页） | VulnerabilityListPage |
| `GET` | `/api/v1/projects/{project_id}/vulnerabilities/{vuln_id}` | 漏洞详情 | VulnerabilityDetailPage |

### 5.2 攻击路径

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/attack-paths` | 攻击路径列表（分页） | AttackPathListPage |
| `GET` | `/api/v1/projects/{project_id}/attack-paths/{path_id}` | 攻击路径详情 | AttackPathDetailPage |

### 5.3 报告

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/report` | 获取报告内容 | ReportPage |
| `GET` | `/api/v1/projects/{project_id}/report/download` | 下载报告文件 (blob) | ReportPage |

### 5.4 实时监控

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/messages` | AI 对话消息（游标分页） | MonitorPage |
| `GET` | `/api/v1/projects/{project_id}/logs` | 运行日志（游标分页） | MonitorPage |
| `GET` | `/api/v1/projects/{project_id}/resources` | 资源消耗（游标分页） | MonitorPage |

### 5.5 知识库

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/knowledge/entries` | 知识条目列表 | KnowledgePage |
| `POST` | `/api/v1/knowledge/entries` | 创建知识条目 | KnowledgePage |
| `GET` | `/api/v1/knowledge/entries/{entry_id}` | 知识条目详情 | KnowledgePage |
| `PUT` | `/api/v1/knowledge/entries/{entry_id}` | 更新知识条目 | KnowledgePage |
| `DELETE` | `/api/v1/knowledge/entries/{entry_id}` | 删除知识条目 | KnowledgePage |
| `POST` | `/api/v1/knowledge/search` | 语义检索 | KnowledgePage |
| `GET` | `/api/v1/projects/{project_id}/knowledge/retrievals` | 检索历史 | KnowledgePage |

### 5.6 系统配置

| 方法 | 路径 | 用途 | 前端页面 |
|---|---|---|---|
| `GET` | `/api/v1/system/config` | 获取系统配置 | SystemConfigPage |
| `PUT` | `/api/v1/system/config` | 更新系统配置 | SystemConfigPage |

---

## 验收测试流程

推荐按以下顺序逐一验证：

```
1. GET  /system/status          → 确认系统已初始化
2. POST /system/login           → 登录获取 Cookie
3. GET  /users/me               → 确认认证生效
4. GET  /users                  → 管理员查看用户列表
5. POST /users                  → 创建普通用户
6. GET  /users/{id}             → 查看用户详情
7. PUT  /users/{id}             → 更新用户状态/角色
8. POST /users/{id}/reset-password → 重置密码
9. PUT  /users/me/password      → 修改自己密码
10. POST /projects              → 创建项目
11. GET  /projects              → 项目列表
12. GET  /projects/{id}         → 项目详情
13. POST /projects/{id}/start   → 启动项目（需 Idempotency-Key）
14. GET  /projects/{id}/stages  → 查看运行阶段
15. GET  /projects/{id}/workers → 查看 Worker 任务
16. POST /projects/{id}/stop    → 停止项目
17. DELETE /projects/{id}       → 删除项目
18. POST /system/logout         → 退出登录
```

---

## 一键验收脚本

```bash
#!/bin/bash
BASE="http://127.0.0.1:8000/api/v1"
COOKIE=/tmp/asa-test-cookies.txt
PASS=0; FAIL=0

check() {
  local label="$1" method="$2" url="$3" data="$4" extra_headers="$5"
  local code
  if [ -z "$data" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" -b $COOKIE $extra_headers)
  else
    code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" -b $COOKIE $extra_headers -H "Content-Type: application/json" -d "$data")
  fi
  if [ "$code" -ge 200 ] && [ "$code" -lt 300 ]; then
    echo "✅ $label (HTTP $code)"
    PASS=$((PASS+1))
  else
    echo "❌ $label (HTTP $code)"
    FAIL=$((FAIL+1))
  fi
}

rm -f $COOKIE

# 1. System
check "系统状态"      GET  "$BASE/system/status"
check "登录"          POST "$BASE/system/login" '{"username":"admin","password":"Sas-Admin-2026!"}'

# 2. Users
check "当前用户"       GET  "$BASE/users/me"
check "用户列表"       GET  "$BASE/users?page=1&page_size=5"
check "创建用户"       POST "$BASE/users" '{"username":"testuser1","password":"Test-1234","role":"user"}'

USER_ID=$(curl -s "$BASE/users?keyword=testuser1" -b $COOKIE | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['items'][0]['id'])" 2>/dev/null)
if [ -n "$USER_ID" ]; then
  check "用户详情"     GET  "$BASE/users/$USER_ID"
  check "更新用户"     PUT  "$BASE/users/$USER_ID" '{"status":"disabled"}'
  check "重置密码"     POST "$BASE/users/$USER_ID/reset-password" '{"new_password":"New-Pass-999"}'
fi
check "修改自己密码"   PUT  "$BASE/users/me/password" '{"old_password":"Sas-Admin-2026!","new_password":"Sas-Admin-2026!"}'

# 3. Projects
PROJ_ID=$(curl -s -X POST "$BASE/projects" -b $COOKIE -H "Content-Type: application/json" \
  -d '{"project_name":"验收测试","source_type":"local","source_path":"demo","task_content":"测试","environment_type":"python312"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
echo "创建项目 ID: $PROJ_ID"

if [ -n "$PROJ_ID" ]; then
  check "项目列表"     GET  "$BASE/projects?page=1"
  check "项目详情"     GET  "$BASE/projects/$PROJ_ID"
  IK="test-$(date +%s)"
  check "启动项目"     POST "$BASE/projects/$PROJ_ID/start" '{}' "-H 'Idempotency-Key: $IK-start'"
  check "查看阶段"     GET  "$BASE/projects/$PROJ_ID/stages"
  check "Worker任务"   GET  "$BASE/projects/$PROJ_ID/workers"
  check "停止项目"     POST "$BASE/projects/$PROJ_ID/stop" '{"reason":"验收"}' "-H 'Idempotency-Key: $IK-stop'"
  check "删除项目"     DELETE "$BASE/projects/$PROJ_ID" '{"confirm_project_name":"验收测试"}' "-H 'Idempotency-Key: $IK-delete'"
fi

# 4. Logout
check "退出登录"       POST "$BASE/system/logout"

echo ""
echo "--- 结果: $PASS 通过, $FAIL 失败 ---"
```
