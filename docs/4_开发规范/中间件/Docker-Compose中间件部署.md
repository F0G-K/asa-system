本文档约8000字,阅读本文档越16分钟。

# 自动化安全评估系统 Docker Compose 中间件部署

## 1. 文档说明

### 1.1 目的

本文档根据 PRD、概要设计、数据库设计和接口契约，明确自动化安全评估系统（ASA System）MVP 的中间件边界，并提供一份可直接保存为 `compose.yaml` 的完整 Docker Compose 配置。

本文档只定义中间件与基础设施，不包含尚未实现的 `web`、`api`、`worker`、`event-relay` 和 `executor` 应用镜像。

### 1.2 适用范围

- 单台 Linux 服务器上的 MVP 开发、联调和演示环境。
- Docker Engine 与 Docker Compose V2。
- PostgreSQL 业务数据、Redis 短期消息与控制数据、Prometheus 指标、Grafana 仪表盘和可选 Nginx 网关。
- `amd64` 与 `arm64` 主机。

### 1.3 执行状态

本文档中的 Compose 配置和命令仅完成静态设计与语法校验。编写本文档时未执行镜像拉取、容器创建、容器启动、数据库初始化或数据卷变更。

## 2. 中间件边界

### 2.1 纳入 Compose 的服务

| 服务 | 镜像 | 是否默认启动 | 核心职责 | 是否保存权威业务数据 |
| --- | --- | :---: | --- | :---: |
| PostgreSQL | `postgres:16.14-alpine` | 是 | 保存用户、项目、任务、漏洞、路径、报告、日志、资源、审计和 Outbox 事件 | 是 |
| Redis | `redis:7.4.9-alpine` | 是 | Celery Broker、Redis Stream、取消标记、限流计数和分布式锁 | 否 |
| Prometheus | `prom/prometheus:v3.12.0` | 是 | 采集 API、Worker、执行网关和中间件运行指标 | 否 |
| Grafana | `grafana/grafana:13.0.2` | 是 | 展示 Prometheus 指标和系统级可观测性看板 | 否 |
| Nginx | `nginx:1.28.3-alpine` | 否 | HTTPS 终止、静态资源、REST 与 WebSocket 反向代理、基础限流 | 否 |

Nginx 使用 `gateway` profile。默认执行 `docker compose up -d` 时不会启动；应用服务具备可用镜像后，可使用 `docker compose --profile gateway up -d` 启动。即使 `api` 和 `web` 尚未加入网络，Nginx 仍能启动并响应 `/healthz`，其他代理请求返回 `502`。

### 2.2 不作为独立中间件容器的组件

| 组件 | 处理方式 | 原因 |
| --- | --- | --- |
| Docker Engine | 宿主机前置依赖 | 只有 `executor` 可访问 Docker Engine；API 不得挂载 `/var/run/docker.sock` |
| Celery | 集成在 `worker` 应用镜像 | Celery 是任务执行框架，使用 Redis 作为 Broker，不需要独立 Celery Server |
| Event Relay | 独立应用进程 | 从 PostgreSQL `domain_events` 读取 Outbox，再投递 Redis Stream |
| WebSocket | 集成在 API 或独立应用进程 | Redis 只负责短期事件传输，WebSocket 不保存权威状态 |
| 项目文件存储 | 宿主机受控目录或独立数据卷 | MVP 保存 `repositories`、`workspace`、`runtime_logs` 和 `reports` |

### 2.3 本期不引入的中间件

- 不引入 Kafka。只有事件吞吐和保留需求超过 Redis Stream 能力后再评估。
- 不引入 Elasticsearch。MVP 的日志查询使用 PostgreSQL 索引和归档文件。
- 不引入 Kubernetes。MVP 使用单机 Docker Compose。
- 不引入 MinIO 或其他 S3 服务。MVP 使用受控宿主机数据卷；多节点阶段再迁移到 S3 兼容存储。
- 不引入独立向量数据库（Qdrant、Milvus、Weaviate 等）。MVP 使用 PostgreSQL pgvector 扩展承载安全知识向量存储和 ANN 检索。
- 不引入独立任务结果数据库。项目、阶段和任务状态以 PostgreSQL 为准。

## 3. 账号、端口与数据

### 3.1 固定账号

按本次要求，支持账号认证的中间件统一使用以下凭证：

| 服务 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| PostgreSQL | `root` | `kkkcm520` | 数据库 `asa_system` 的初始化超级用户和所有者 |
| Redis | `root` | `kkkcm520` | Redis ACL 用户；默认用户关闭 |
| Grafana | `root` | `kkkcm520` | 首次初始化的 Grafana 管理员 |
| Prometheus | 无 | 无 | 不提供内置登录，端口仅绑定宿主机回环地址 |
| Nginx | 无 | 无 | 本文不配置 HTTP Basic Auth |

这里的 `root` 是服务登录账号，不是容器内 Linux 进程用户。不得通过 `user: "0"` 强制所有容器以操作系统 root 身份运行。

固定弱密码和明文 Compose 配置不适用于生产环境。生产部署必须改用 Docker Secrets、外部密钥系统或受控环境变量，并同步轮换应用连接串。本文按明确要求保留固定值，不创建或修改项目 `.env`。

### 3.2 宿主机端口

| 服务 | 容器端口 | 宿主机地址 | 用途 |
| --- | ---: | --- | --- |
| PostgreSQL | `5432` | `127.0.0.1:5432` | 本机数据库迁移、调试和备份 |
| Redis | `6379` | `127.0.0.1:6379` | 本机 Redis 调试 |
| Prometheus | `9090` | `127.0.0.1:9090` | 指标查询与目标状态 |
| Grafana | `3000` | `127.0.0.1:3000` | 仪表盘访问 |
| Nginx | `80` | `127.0.0.1:8080` | 网关联调和健康检查 |

所有端口只绑定 `127.0.0.1`，不对宿主机公网网卡开放。生产环境应只公开 Nginx 的 HTTPS 入口，PostgreSQL、Redis、Prometheus、Grafana、执行网关和 Docker Engine 不得直接暴露到公网。

### 3.3 持久化卷

| 数据卷 | 挂载点 | 数据性质 | 备份要求 |
| --- | --- | --- | --- |
| `postgres_data` | `/var/lib/postgresql/data` | 权威业务数据 | 必须定期备份并验证恢复 |
| `redis_data` | `/data` | 可重建队列、Stream 和控制数据 | 可选备份，不作为业务恢复依据 |
| `prometheus_data` | `/prometheus` | 时序指标 | 按监控保留策略处理 |
| `grafana_data` | `/var/lib/grafana` | Grafana 用户、仪表盘和配置 | 需要保留或使用声明式配置重建 |

执行 `docker compose down` 不删除命名数据卷。不得在未完成备份和明确确认的情况下执行 `docker compose down -v` 或手工删除这些数据卷。

## 4. 完整 Compose 配置

### 4.1 兼容性

- 最低 Docker Compose 版本为 `2.23.1`，因为配置使用顶层 `configs.content` 内联 Redis ACL、Prometheus、Grafana 和 Nginx 配置。
- 推荐使用当前稳定的 Docker Engine 和 Docker Compose V2。
- 配置不使用旧版 `version` 字段。
- 镜像使用明确补丁版本，不使用 `latest`。

### 4.2 `compose.yaml`

将以下完整代码保存为 `compose.yaml` 后即可进行静态校验或启动：

```yaml
name: asa-middleware

services:
  postgres:
    image: postgres:16.14-alpine
    container_name: asa-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: asa_system
      POSTGRES_USER: root
      POSTGRES_PASSWORD: kkkcm520
      POSTGRES_INITDB_ARGS: --auth-host=scram-sha-256
      PGDATA: /var/lib/postgresql/data/pgdata
      PGTZ: UTC
      TZ: UTC
    command:
      - postgres
      - -c
      - timezone=UTC
      - -c
      - password_encryption=scram-sha-256
    ports:
      - name: postgres
        target: 5432
        host_ip: 127.0.0.1
        published: "5432"
        protocol: tcp
        app_protocol: postgresql
        mode: host
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -h 127.0.0.1 -p 5432 -U root -d asa_system
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s
    stop_grace_period: 60s

  redis:
    image: redis:7.4.9-alpine
    container_name: asa-redis
    restart: unless-stopped
    command:
      - redis-server
      - --aclfile
      - /usr/local/etc/redis/users.acl
      - --appendonly
      - "yes"
      - --appendfsync
      - everysec
      - --save
      - "60"
      - "1000"
      - --loglevel
      - warning
    configs:
      - source: redis_acl
        target: /usr/local/etc/redis/users.acl
        mode: 0444
    ports:
      - name: redis
        target: 6379
        host_ip: 127.0.0.1
        published: "6379"
        protocol: tcp
        app_protocol: redis
        mode: host
    volumes:
      - redis_data:/data
    networks:
      - app
    healthcheck:
      test:
        - CMD
        - redis-cli
        - --user
        - root
        - --pass
        - kkkcm520
        - --no-auth-warning
        - ping
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 10s
    stop_grace_period: 30s

  prometheus:
    image: prom/prometheus:v3.12.0
    container_name: asa-prometheus
    restart: unless-stopped
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.wal-compression
    configs:
      - source: prometheus_config
        target: /etc/prometheus/prometheus.yml
        mode: 0444
    ports:
      - name: prometheus
        target: 9090
        host_ip: 127.0.0.1
        published: "9090"
        protocol: tcp
        app_protocol: http
        mode: host
    volumes:
      - prometheus_data:/prometheus
    networks:
      - app
    healthcheck:
      test:
        - CMD-SHELL
        - wget --quiet --spider http://127.0.0.1:9090/-/ready
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 20s
    stop_grace_period: 30s

  grafana:
    image: grafana/grafana:13.0.2
    container_name: asa-grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_USER: root
      GF_SECURITY_ADMIN_PASSWORD: kkkcm520
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_LOG_MODE: console
      TZ: UTC
    configs:
      - source: grafana_datasource
        target: /etc/grafana/provisioning/datasources/prometheus.yml
        mode: 0444
    ports:
      - name: grafana
        target: 3000
        host_ip: 127.0.0.1
        published: "3000"
        protocol: tcp
        app_protocol: http
        mode: host
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - app
    depends_on:
      prometheus:
        condition: service_healthy
    healthcheck:
      test:
        - CMD-SHELL
        - wget --quiet --spider http://127.0.0.1:3000/api/health
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 30s
    stop_grace_period: 30s

  nginx:
    image: nginx:1.28.3-alpine
    container_name: asa-nginx
    restart: unless-stopped
    profiles:
      - gateway
    configs:
      - source: nginx_default
        target: /etc/nginx/conf.d/default.conf
        mode: 0444
    ports:
      - name: gateway
        target: 80
        host_ip: 127.0.0.1
        published: "8080"
        protocol: tcp
        app_protocol: http
        mode: host
    networks:
      - public
      - app
    healthcheck:
      test:
        - CMD-SHELL
        - wget --quiet --spider http://127.0.0.1/healthz
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 10s
    stop_grace_period: 30s

configs:
  redis_acl:
    content: |
      user default off
      user root on >kkkcm520 ~* &* +@all

  prometheus_config:
    content: |
      global:
        scrape_interval: 15s
        evaluation_interval: 15s

      scrape_configs:
        - job_name: prometheus
          static_configs:
            - targets:
                - prometheus:9090

  grafana_datasource:
    content: |
      apiVersion: 1

      datasources:
        - name: Prometheus
          uid: asa-prometheus
          type: prometheus
          access: proxy
          url: http://prometheus:9090
          isDefault: true
          editable: false

  nginx_default:
    content: |
      map $$http_upgrade $$connection_upgrade {
          default upgrade;
          '' close;
      }

      server {
          listen 80;
          server_name _;
          client_max_body_size 20m;

          location = /healthz {
              access_log off;
              default_type text/plain;
              return 200 'ok\n';
          }

          location /api/ {
              resolver 127.0.0.11 ipv6=off valid=10s;
              set $$api_upstream http://api:8000;
              proxy_pass $$api_upstream;
              proxy_http_version 1.1;
              proxy_set_header Host $$host;
              proxy_set_header X-Real-IP $$remote_addr;
              proxy_set_header X-Forwarded-For $$proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $$scheme;
              proxy_set_header Upgrade $$http_upgrade;
              proxy_set_header Connection $$connection_upgrade;
              proxy_connect_timeout 5s;
              proxy_read_timeout 300s;
              proxy_send_timeout 300s;
          }

          location / {
              resolver 127.0.0.11 ipv6=off valid=10s;
              set $$web_upstream http://web:80;
              proxy_pass $$web_upstream;
              proxy_http_version 1.1;
              proxy_set_header Host $$host;
              proxy_set_header X-Real-IP $$remote_addr;
              proxy_set_header X-Forwarded-For $$proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $$scheme;
              proxy_connect_timeout 5s;
              proxy_read_timeout 60s;
              proxy_send_timeout 60s;
          }
      }

networks:
  public:
    name: asa-public
    driver: bridge

  app:
    name: asa-app
    driver: bridge
    internal: true

volumes:
  postgres_data:
    name: asa-postgres-data

  redis_data:
    name: asa-redis-data

  prometheus_data:
    name: asa-prometheus-data

  grafana_data:
    name: asa-grafana-data
```

### 4.3 配置说明

- PostgreSQL 使用 `scram-sha-256` 进行主机连接密码认证，数据库时区为 UTC。
- PostgreSQL 版本满足数据库设计要求的 PostgreSQL 15 及以上，并支持 `pgcrypto`、`pgvector`、复合外键、部分索引和约束触发器。
- `pgvector` 扩展在数据库初始化 SQL 中通过 `CREATE EXTENSION IF NOT EXISTS vector` 启用，与 `pgcrypto` 在同一事务中创建。Docker Hub 的 `postgres:16.14-alpine` 镜像内置了 `pgvector` 扩展，无需额外构建。
- Redis 关闭无密码的 `default` 用户，仅启用 `root` ACL 用户。
- Redis AOF 用于降低短期队列和 Stream 在异常重启时的丢失量，但 Redis 数据仍不作为业务事实源。
- Prometheus 当前只抓取自身。`api`、`worker`、`event-relay` 和 `executor` 的 `/metrics` 端口确定后，再加入 `scrape_configs`。
- Grafana 启动时自动配置 Prometheus 数据源。管理员账号只在空 `grafana_data` 卷首次初始化时生效。
- Nginx 通过 Docker 内置 DNS 延迟解析 `api` 和 `web`，因此应用容器尚不存在时也能启动。
- Nginx 内联配置中的 `$$` 是 Compose 的字面量美元符号转义，运行时写入配置文件的是 Nginx 所需的单个 `$`。
- Nginx 当前仅提供 HTTP 联调入口。生产环境必须补充 HTTPS 证书、TLS 配置和适合实际流量的限流规则。
- `app` 网络设置为内部网络，中间件之间通过服务名访问；`public` 网络仅供 Nginx 接入。

## 5. 应用连接配置

### 5.1 容器内连接地址

后续应用服务加入 `asa-app` 网络后，使用服务名而不是固定 IP。

| 用途 | 配置名 | 值 |
| --- | --- | --- |
| SQLAlchemy 异步连接 | `DATABASE_URL` | `postgresql+asyncpg://root:kkkcm520@postgres:5432/asa_system` |
| Alembic 同步连接 | `ALEMBIC_DATABASE_URL` | `postgresql+psycopg://root:kkkcm520@postgres:5432/asa_system` |
| Celery Broker | `CELERY_BROKER_URL` | `redis://root:kkkcm520@redis:6379/0` |
| 实时事件与 Redis Stream | `REDIS_EVENT_URL` | `redis://root:kkkcm520@redis:6379/1` |
| 取消标记、限流和分布式锁 | `REDIS_CONTROL_URL` | `redis://root:kkkcm520@redis:6379/2` |
| Prometheus | `PROMETHEUS_URL` | `http://prometheus:9090` |

Celery 的业务结果不依赖 Redis Result Backend。任务执行结果、项目状态和阶段状态必须写入 PostgreSQL。

### 5.2 宿主机连接地址

| 服务 | 地址 |
| --- | --- |
| PostgreSQL | `postgresql://root:kkkcm520@127.0.0.1:5432/asa_system` |
| Redis | `redis://root:kkkcm520@127.0.0.1:6379/0` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |
| Nginx 健康检查 | `http://127.0.0.1:8080/healthz` |

## 6. 执行步骤

以下命令为后续执行说明，本文档生成过程中未执行。

### 6.1 前置检查

```bash
docker --version
docker compose version
```

Docker Compose 版本必须不低于 `2.23.1`。

### 6.2 静态校验

```bash
docker compose -f compose.yaml config --quiet
```

该命令只解析和校验 Compose 配置，不创建容器。

### 6.3 启动默认中间件

```bash
docker compose -f compose.yaml up -d
```

默认启动 PostgreSQL、Redis、Prometheus 和 Grafana。

### 6.4 启动可选 Nginx

```bash
docker compose -f compose.yaml --profile gateway up -d
```

应用容器未启动时，只有 `/healthz` 正常，`/api/` 和 `/` 返回 `502` 属于预期行为。

### 6.5 查看状态

```bash
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs --tail=100 postgres redis prometheus grafana
```

所有默认服务应进入 `healthy`。

### 6.6 连通性检查

PostgreSQL：

```bash
docker compose -f compose.yaml exec postgres \
  psql -U root -d asa_system -c "SELECT current_user, current_database(), current_setting('TimeZone');"
```

Redis：

```bash
docker compose -f compose.yaml exec redis \
  redis-cli --user root --pass kkkcm520 --no-auth-warning PING
```

Prometheus：

```bash
curl --fail http://127.0.0.1:9090/-/ready
```

Grafana：

```bash
curl --fail http://127.0.0.1:3000/api/health
```

Nginx：

```bash
curl --fail http://127.0.0.1:8080/healthz
```

### 6.7 初始化数据库结构

数据库容器首次启动只创建空的 `asa_system` 数据库，不自动执行 Markdown 中的 SQL。应从 `docs/4_开发规范/数据库/初始化sql.md` 提取完整 SQL 代码块，评审后再执行：

```bash
docker compose -f compose.yaml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U root -d asa_system < init.sql
```

初始化 SQL 自带 `BEGIN`、`COMMIT`、`pgcrypto`、`pgvector`、18 张表、索引、触发器和验证查询。不得在应用启动时隐式建表或改表。

### 6.8 安全停止

```bash
docker compose -f compose.yaml stop
```

需要移除容器和网络但保留命名数据卷时：

```bash
docker compose -f compose.yaml down
```

## 7. 应用服务接入要求

### 7.1 网络

- `web`、`api`、`worker` 和 `event-relay` 接入 `asa-app` 网络。
- Nginx 同时接入 `asa-public` 和 `asa-app` 网络。
- `executor` 和 `worker` 还需接入独立 `execution` 网络，后续完整应用 Compose 中定义。
- 项目隔离容器不得接入 `public` 网络。
- 应用连接中间件必须使用服务名 `postgres`、`redis`、`prometheus`，不得固定容器 IP。

### 7.2 启动依赖

- `api`、`worker` 和 `event-relay` 应等待 PostgreSQL 与 Redis 健康。
- 应用健康检查区分进程存活与依赖就绪。
- Worker 只有在业务事务提交后领取任务。
- Redis 不可用时，不得伪造 PostgreSQL 业务状态。
- WebSocket 或事件投递失败不得回滚已经提交的业务事务。

### 7.3 Docker Engine

- API 服务不得挂载 `/var/run/docker.sock`。
- 只有隔离执行网关可以访问 Docker Engine。
- 执行网关仅提供预定义的容器生命周期、文件读取、目录遍历、搜索和受控命令接口。
- 项目容器使用非 root 用户、只读根文件系统、独立工作目录、最小 Linux Capabilities、`no-new-privileges`、Seccomp 和资源限制。
- 源码目录只读挂载，生成文件只能写入 `workspace/{project_id}/`。

## 8. 备份与恢复

### 8.1 PostgreSQL

建议使用自定义格式备份：

```bash
docker compose -f compose.yaml exec -T postgres \
  pg_dump -U root -d asa_system --format=custom > asa_system.dump
```

恢复前必须在独立环境验证备份文件、PostgreSQL 主版本和 Alembic 版本。业务数据库与 `reports`、`runtime_logs`、`workspace`、`repositories` 文件数据需要按同一项目边界协调备份。

### 8.2 Redis

Redis 只保存可重建数据。恢复 PostgreSQL 后，系统应从 `domain_events` Outbox 和持久化任务状态恢复投递与查询，不得将 Redis 快照当作项目最终状态。

### 8.3 Prometheus 与 Grafana

- Prometheus 数据卷按监控保留策略处理，不参与业务数据恢复。
- Grafana 仪表盘应逐步转为声明式 provisioning 文件，降低对本地 SQLite 数据卷的依赖。
- 生产环境升级镜像前，应备份 Grafana 数据卷并验证仪表盘和数据源兼容性。

## 9. 安全与生产化调整

### 9.1 必须调整的内容

- 将固定密码 `kkkcm520` 替换为高强度随机值。
- 将 PostgreSQL、Redis 和 Grafana 密码迁移到 Docker Secrets 或外部密钥系统。
- 移除 PostgreSQL、Redis 和 Prometheus 的宿主机端口映射，或继续限制为受控管理网络。
- 为 Nginx 配置受信任证书、TLS 1.2 及以上、HSTS 和安全响应头。
- 为 Redis ACL 拆分最小权限用户，避免应用账号长期保留 `+@all`。
- 为数据库创建独立 DDL 迁移账号和运行时 DML 账号，避免应用使用超级用户。
- 为镜像记录多架构 digest，并通过受控升级流程更新。
- 配置数据卷备份、恢复演练、容量告警和磁盘空间告警。

### 9.2 明确风险

本次固定的 `root` 和 `kkkcm520` 不符合最小权限和强凭证原则，只适合受控开发或验收环境。配置中的 `root` 不应成为生产应用长期使用的数据库超级用户或 Redis 全权限用户。

Redis 协议默认未启用 TLS，认证信息在容器网络中传输。生产环境若跨主机部署，必须启用 Redis TLS 或使用受保护的私有网络。

## 10. 验收检查清单

- [ ] `compose.yaml` 能通过 `docker compose config --quiet`。
- [ ] Compose 版本不低于 `2.23.1`。
- [ ] 默认启动服务为 PostgreSQL、Redis、Prometheus 和 Grafana。
- [ ] Nginx 仅在启用 `gateway` profile 时启动。
- [ ] 所有镜像使用明确补丁版本，不使用 `latest`。
- [ ] PostgreSQL 数据库名为 `asa_system`，账号为 `root`。
- [ ] Redis 关闭 `default` 用户，仅启用 `root` ACL 用户。
- [ ] Grafana 管理员账号为 `root`。
- [ ] 所有要求账号的服务密码均为 `kkkcm520`。
- [ ] PostgreSQL 和 Redis 健康检查包含认证信息。
- [ ] 所有宿主机端口只绑定 `127.0.0.1`。
- [ ] PostgreSQL、Redis、Prometheus 和 Grafana 使用命名数据卷。
- [ ] PostgreSQL 时区为 UTC，主机认证使用 SCRAM-SHA-256。
- [ ] Redis 启用 AOF，但不被当作权威业务数据源。
- [ ] Prometheus 数据源已自动配置到 Grafana。
- [ ] API 不挂载 Docker Socket。
- [ ] 未引入 Kafka、Elasticsearch、Kubernetes、MinIO、独立向量数据库或额外数据库。
- [ ] PostgreSQL 已启用 `pgvector` 扩展（`CREATE EXTENSION IF NOT EXISTS vector`）。
- [ ] 未自动执行数据库初始化 SQL。
- [ ] 未执行 `docker compose up`、镜像拉取或数据卷变更。

## 11. 官方参考

- [Docker Compose 文件参考](https://docs.docker.com/reference/compose-file/)
- [Docker Compose configs 参考](https://docs.docker.com/reference/compose-file/configs/)
- [Docker Compose 变量插值参考](https://docs.docker.com/reference/compose-file/interpolation/)
- [Docker Compose 网络参考](https://docs.docker.com/reference/compose-file/networks/)
- [PostgreSQL Docker 官方镜像](https://hub.docker.com/_/postgres)
- [Redis Docker 官方镜像](https://hub.docker.com/_/redis)
- [Redis ACL 官方文档](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/)
- [Prometheus Docker 安装文档](https://prometheus.io/docs/prometheus/latest/installation/)
- [Grafana Docker 安装文档](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/)
- [Nginx Docker 官方镜像](https://hub.docker.com/_/nginx)
