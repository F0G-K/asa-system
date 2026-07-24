BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TABLE users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username varchar(64) NOT NULL,
    password_hash varchar(255) NOT NULL,
    role varchar(32) NOT NULL,
    status varchar(32) DEFAULT 'active' NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users__username UNIQUE (username),
    CONSTRAINT ck_users__username_normalized
        CHECK (
            username = lower(btrim(username))
            AND char_length(username) BETWEEN 3 AND 64
            AND username !~ '[[:space:]]'
        ),
    CONSTRAINT ck_users__password_hash_nonempty
        CHECK (char_length(btrim(password_hash)) >= 20),
    CONSTRAINT ck_users__role
        CHECK (role IN ('user', 'admin')),
    CONSTRAINT ck_users__status
        CHECK (status IN ('active', 'disabled'))
);

CREATE TABLE projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_name varchar(128) NOT NULL,
    source_type varchar(32) NOT NULL,
    source_path text NOT NULL,
    task_content text NOT NULL,
    environment_type varchar(64) NOT NULL,
    project_status varchar(32) DEFAULT 'created' NOT NULL,
    created_by uuid NOT NULL,
    stop_requested_at timestamptz,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_projects PRIMARY KEY (id),
    CONSTRAINT fk_projects__created_by__users
        FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT ck_projects__project_name_nonempty
        CHECK (char_length(btrim(project_name)) BETWEEN 1 AND 128),
    CONSTRAINT ck_projects__source_type
        CHECK (source_type IN ('local', 'repository')),
    CONSTRAINT ck_projects__source_path_nonempty
        CHECK (char_length(btrim(source_path)) > 0),
    CONSTRAINT ck_projects__local_source_path
        CHECK (
            source_type <> 'local'
            OR (
                source_path !~ '^/'
                AND source_path !~ '(^|/)\.\.(/|$)'
            )
        ),
    CONSTRAINT ck_projects__repository_has_no_inline_password
        CHECK (
            source_type <> 'repository'
            OR source_path !~ '^[a-zA-Z][a-zA-Z0-9+.-]*://[^/@[:space:]]+:[^/@[:space:]]+@'
        ),
    CONSTRAINT ck_projects__task_content_nonempty
        CHECK (char_length(btrim(task_content)) > 0),
    CONSTRAINT ck_projects__environment_type
        CHECK (environment_type ~ '^[a-z][a-z0-9_-]{0,63}$'),
    CONSTRAINT ck_projects__project_status
        CHECK (project_status IN ('created', 'running', 'completed', 'failed', 'stopped'))
);

CREATE TABLE project_runtimes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    runtime_identifier varchar(128),
    container_status varchar(32) DEFAULT 'pending' NOT NULL,
    workspace_key text,
    repository_key text,
    environment_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    started_at timestamptz,
    stopped_at timestamptz,
    destroyed_at timestamptz,
    error_message text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_project_runtimes PRIMARY KEY (id),
    CONSTRAINT uq_project_runtimes__project_id UNIQUE (project_id),
    CONSTRAINT uq_project_runtimes__id_project_id UNIQUE (id, project_id),
    CONSTRAINT fk_project_runtimes__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT ck_project_runtimes__runtime_identifier_nonempty
        CHECK (
            runtime_identifier IS NULL
            OR char_length(btrim(runtime_identifier)) > 0
        ),
    CONSTRAINT ck_project_runtimes__container_status
        CHECK (
            container_status IN (
                'pending',
                'starting',
                'running',
                'stopping',
                'stopped',
                'destroyed',
                'failed'
            )
        ),
    CONSTRAINT ck_project_runtimes__workspace_key_safe
        CHECK (
            workspace_key IS NULL
            OR (
                char_length(btrim(workspace_key)) > 0
                AND workspace_key !~ '^/'
                AND workspace_key !~ '(^|/)\.\.(/|$)'
            )
        ),
    CONSTRAINT ck_project_runtimes__repository_key_safe
        CHECK (
            repository_key IS NULL
            OR (
                char_length(btrim(repository_key)) > 0
                AND repository_key !~ '^/'
                AND repository_key !~ '(^|/)\.\.(/|$)'
            )
        ),
    CONSTRAINT ck_project_runtimes__environment_snapshot_object
        CHECK (jsonb_typeof(environment_snapshot) = 'object'),
    CONSTRAINT ck_project_runtimes__time_order
        CHECK (
            (stopped_at IS NULL OR started_at IS NULL OR stopped_at >= started_at)
            AND (destroyed_at IS NULL OR stopped_at IS NULL OR destroyed_at >= stopped_at)
        ),
    CONSTRAINT ck_project_runtimes__failed_error
        CHECK (container_status <> 'failed' OR error_message IS NOT NULL)
);

CREATE TABLE runtime_stages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    runtime_id uuid NOT NULL,
    stage_name varchar(64) NOT NULL,
    stage_order smallint NOT NULL,
    stage_status varchar(32) DEFAULT 'idle' NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    error_message text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_runtime_stages PRIMARY KEY (id),
    CONSTRAINT uq_runtime_stages__id_project_id UNIQUE (id, project_id),
    CONSTRAINT uq_runtime_stages__runtime_id_stage_name UNIQUE (runtime_id, stage_name),
    CONSTRAINT uq_runtime_stages__runtime_id_stage_order UNIQUE (runtime_id, stage_order),
    CONSTRAINT fk_runtime_stages__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_runtime_stages__runtime_scope__project_runtimes
        FOREIGN KEY (runtime_id, project_id)
        REFERENCES project_runtimes (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_runtime_stages__stage_name_order
        CHECK (
            (stage_name = 'environment_scan' AND stage_order = 1)
            OR (stage_name = 'code_analysis' AND stage_order = 2)
            OR (stage_name = 'vulnerability_verify' AND stage_order = 3)
            OR (stage_name = 'report_generate' AND stage_order = 4)
            OR (stage_name = 'done' AND stage_order = 5)
        ),
    CONSTRAINT ck_runtime_stages__stage_status
        CHECK (stage_status IN ('idle', 'running', 'success', 'failed')),
    CONSTRAINT ck_runtime_stages__status_times
        CHECK (
            (stage_status = 'idle' AND started_at IS NULL AND finished_at IS NULL)
            OR (stage_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL)
            OR (
                stage_status IN ('success', 'failed')
                AND started_at IS NOT NULL
                AND finished_at IS NOT NULL
                AND finished_at >= started_at
            )
        ),
    CONSTRAINT ck_runtime_stages__failed_error
        CHECK (stage_status <> 'failed' OR error_message IS NOT NULL)
);

CREATE TABLE worker_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    stage_id uuid NOT NULL,
    worker_role varchar(64) NOT NULL,
    task_content text NOT NULL,
    task_status varchar(32) DEFAULT 'idle' NOT NULL,
    result_summary text,
    error_message text,
    request_id uuid NOT NULL,
    idempotency_key varchar(128),
    attempt_count integer DEFAULT 0 NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_worker_tasks PRIMARY KEY (id),
    CONSTRAINT uq_worker_tasks__id_project_id UNIQUE (id, project_id),
    CONSTRAINT uq_worker_tasks__id_project_id_stage_id UNIQUE (id, project_id, stage_id),
    CONSTRAINT fk_worker_tasks__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_worker_tasks__stage_scope__runtime_stages
        FOREIGN KEY (stage_id, project_id)
        REFERENCES runtime_stages (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_worker_tasks__worker_role
        CHECK (
            worker_role IN (
                'general',
                'environment_inspector',
                'code_analyst',
                'vulnerability_verifier',
                'report_editor',
                'operations_assistant'
            )
        ),
    CONSTRAINT ck_worker_tasks__task_content_nonempty
        CHECK (char_length(btrim(task_content)) > 0),
    CONSTRAINT ck_worker_tasks__task_status
        CHECK (task_status IN ('idle', 'running', 'success', 'failed')),
    CONSTRAINT ck_worker_tasks__attempt_count
        CHECK (attempt_count >= 0),
    CONSTRAINT ck_worker_tasks__idempotency_key_nonempty
        CHECK (
            idempotency_key IS NULL
            OR char_length(btrim(idempotency_key)) > 0
        ),
    CONSTRAINT ck_worker_tasks__status_times
        CHECK (
            (task_status = 'idle' AND started_at IS NULL AND finished_at IS NULL)
            OR (task_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL)
            OR (
                task_status IN ('success', 'failed')
                AND started_at IS NOT NULL
                AND finished_at IS NOT NULL
                AND finished_at >= started_at
            )
        ),
    CONSTRAINT ck_worker_tasks__failed_error
        CHECK (task_status <> 'failed' OR error_message IS NOT NULL)
);

CREATE TABLE vulnerabilities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    discovered_by_task_id uuid,
    verified_by_task_id uuid,
    vuln_code varchar(64) NOT NULL,
    vuln_title varchar(255) NOT NULL,
    rule_type varchar(128) NOT NULL,
    risk_level varchar(16) NOT NULL,
    file_path text NOT NULL,
    line_start integer,
    line_end integer,
    impact_text text NOT NULL,
    condition_text text NOT NULL,
    evidence_text text NOT NULL,
    evidence_fingerprint char(64) NOT NULL,
    verify_status varchar(32) DEFAULT 'pending' NOT NULL,
    reproduce_steps_text text,
    verify_code_text text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_vulnerabilities PRIMARY KEY (id),
    CONSTRAINT uq_vulnerabilities__id_project_id UNIQUE (id, project_id),
    CONSTRAINT uq_vulnerabilities__project_id_vuln_code UNIQUE (project_id, vuln_code),
    CONSTRAINT uq_vulnerabilities__project_id_fingerprint
        UNIQUE (project_id, evidence_fingerprint),
    CONSTRAINT fk_vulnerabilities__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_vulnerabilities__discovered_task_scope__worker_tasks
        FOREIGN KEY (discovered_by_task_id, project_id)
        REFERENCES worker_tasks (id, project_id)
        ON DELETE NO ACTION,
    CONSTRAINT fk_vulnerabilities__verified_task_scope__worker_tasks
        FOREIGN KEY (verified_by_task_id, project_id)
        REFERENCES worker_tasks (id, project_id)
        ON DELETE NO ACTION,
    CONSTRAINT ck_vulnerabilities__vuln_code_nonempty
        CHECK (char_length(btrim(vuln_code)) > 0),
    CONSTRAINT ck_vulnerabilities__vuln_title_nonempty
        CHECK (char_length(btrim(vuln_title)) > 0),
    CONSTRAINT ck_vulnerabilities__rule_type_nonempty
        CHECK (char_length(btrim(rule_type)) > 0),
    CONSTRAINT ck_vulnerabilities__risk_level
        CHECK (risk_level IN ('critical', 'high', 'medium', 'low', 'info')),
    CONSTRAINT ck_vulnerabilities__file_path_safe
        CHECK (
            char_length(btrim(file_path)) > 0
            AND file_path !~ '^/'
            AND file_path !~ '(^|/)\.\.(/|$)'
        ),
    CONSTRAINT ck_vulnerabilities__line_range
        CHECK (
            (line_start IS NULL AND line_end IS NULL)
            OR (
                line_start IS NOT NULL
                AND line_start > 0
                AND (line_end IS NULL OR line_end >= line_start)
            )
        ),
    CONSTRAINT ck_vulnerabilities__required_text
        CHECK (
            char_length(btrim(impact_text)) > 0
            AND char_length(btrim(condition_text)) > 0
            AND char_length(btrim(evidence_text)) > 0
        ),
    CONSTRAINT ck_vulnerabilities__evidence_fingerprint
        CHECK (evidence_fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_vulnerabilities__verify_status
        CHECK (verify_status IN ('pending', 'verified', 'rejected'))
);

CREATE TABLE attack_paths (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    created_by_task_id uuid,
    path_code varchar(64) NOT NULL,
    path_title varchar(255) NOT NULL,
    path_summary text NOT NULL,
    final_impact_text text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_attack_paths PRIMARY KEY (id),
    CONSTRAINT uq_attack_paths__id_project_id UNIQUE (id, project_id),
    CONSTRAINT uq_attack_paths__project_id_path_code UNIQUE (project_id, path_code),
    CONSTRAINT fk_attack_paths__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_attack_paths__created_task_scope__worker_tasks
        FOREIGN KEY (created_by_task_id, project_id)
        REFERENCES worker_tasks (id, project_id)
        ON DELETE NO ACTION,
    CONSTRAINT ck_attack_paths__path_code_nonempty
        CHECK (char_length(btrim(path_code)) > 0),
    CONSTRAINT ck_attack_paths__path_title_nonempty
        CHECK (char_length(btrim(path_title)) > 0),
    CONSTRAINT ck_attack_paths__required_text
        CHECK (
            char_length(btrim(path_summary)) > 0
            AND char_length(btrim(final_impact_text)) > 0
        )
);

CREATE TABLE attack_path_items (
    id bigint GENERATED ALWAYS AS IDENTITY,
    project_id uuid NOT NULL,
    path_id uuid NOT NULL,
    vuln_id uuid NOT NULL,
    step_order integer NOT NULL,
    step_text text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_attack_path_items PRIMARY KEY (id),
    CONSTRAINT uq_attack_path_items__path_id_step_order
        UNIQUE (path_id, step_order)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT uq_attack_path_items__path_id_vuln_id UNIQUE (path_id, vuln_id),
    CONSTRAINT fk_attack_path_items__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_attack_path_items__path_scope__attack_paths
        FOREIGN KEY (path_id, project_id)
        REFERENCES attack_paths (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_attack_path_items__vuln_scope__vulnerabilities
        FOREIGN KEY (vuln_id, project_id)
        REFERENCES vulnerabilities (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_attack_path_items__step_order
        CHECK (step_order > 0),
    CONSTRAINT ck_attack_path_items__step_text_nonempty
        CHECK (char_length(btrim(step_text)) > 0)
);

CREATE TABLE chat_messages (
    id bigint GENERATED ALWAYS AS IDENTITY,
    project_id uuid NOT NULL,
    stage_id uuid,
    worker_task_id uuid,
    worker_role varchar(64),
    message_type varchar(64) NOT NULL,
    message_text text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_chat_messages PRIMARY KEY (id),
    CONSTRAINT fk_chat_messages__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages__stage_scope__runtime_stages
        FOREIGN KEY (stage_id, project_id)
        REFERENCES runtime_stages (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages__worker_scope__worker_tasks
        FOREIGN KEY (worker_task_id, project_id, stage_id)
        REFERENCES worker_tasks (id, project_id, stage_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_chat_messages__worker_requires_stage
        CHECK (worker_task_id IS NULL OR stage_id IS NOT NULL),
    CONSTRAINT ck_chat_messages__worker_role
        CHECK (
            worker_role IS NULL
            OR worker_role IN (
                'general',
                'environment_inspector',
                'code_analyst',
                'vulnerability_verifier',
                'report_editor',
                'operations_assistant'
            )
        ),
    CONSTRAINT ck_chat_messages__message_type_nonempty
        CHECK (char_length(btrim(message_type)) > 0),
    CONSTRAINT ck_chat_messages__message_text_nonempty
        CHECK (char_length(btrim(message_text)) > 0)
);

CREATE TABLE runtime_logs (
    id bigint GENERATED ALWAYS AS IDENTITY,
    project_id uuid NOT NULL,
    stage_id uuid,
    worker_task_id uuid,
    request_id uuid,
    log_level varchar(16) NOT NULL,
    log_content text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_runtime_logs PRIMARY KEY (id),
    CONSTRAINT fk_runtime_logs__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_runtime_logs__stage_scope__runtime_stages
        FOREIGN KEY (stage_id, project_id)
        REFERENCES runtime_stages (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_runtime_logs__worker_scope__worker_tasks
        FOREIGN KEY (worker_task_id, project_id, stage_id)
        REFERENCES worker_tasks (id, project_id, stage_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_runtime_logs__worker_requires_stage
        CHECK (worker_task_id IS NULL OR stage_id IS NOT NULL),
    CONSTRAINT ck_runtime_logs__log_level
        CHECK (log_level IN ('debug', 'info', 'warning', 'error')),
    CONSTRAINT ck_runtime_logs__log_content_nonempty
        CHECK (char_length(btrim(log_content)) > 0)
);

CREATE TABLE resource_usages (
    id bigint GENERATED ALWAYS AS IDENTITY,
    project_id uuid NOT NULL,
    runtime_id uuid NOT NULL,
    cpu_usage numeric(9, 3) NOT NULL,
    memory_usage bigint NOT NULL,
    token_count bigint NOT NULL,
    recorded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_resource_usages PRIMARY KEY (id),
    CONSTRAINT fk_resource_usages__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_resource_usages__runtime_scope__project_runtimes
        FOREIGN KEY (runtime_id, project_id)
        REFERENCES project_runtimes (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT ck_resource_usages__cpu_usage
        CHECK (cpu_usage >= 0),
    CONSTRAINT ck_resource_usages__memory_usage
        CHECK (memory_usage >= 0),
    CONSTRAINT ck_resource_usages__token_count
        CHECK (token_count >= 0)
);

CREATE TABLE reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    generated_by_task_id uuid,
    version integer DEFAULT 1 NOT NULL,
    report_status varchar(32) DEFAULT 'pending' NOT NULL,
    report_markdown text,
    report_html text,
    report_file_path text,
    content_sha256 char(64),
    error_message text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_reports PRIMARY KEY (id),
    CONSTRAINT uq_reports__id_project_id UNIQUE (id, project_id),
    CONSTRAINT uq_reports__project_id_version UNIQUE (project_id, version),
    CONSTRAINT fk_reports__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_reports__generated_task_scope__worker_tasks
        FOREIGN KEY (generated_by_task_id, project_id)
        REFERENCES worker_tasks (id, project_id)
        ON DELETE NO ACTION,
    CONSTRAINT ck_reports__version
        CHECK (version > 0),
    CONSTRAINT ck_reports__report_status
        CHECK (report_status IN ('pending', 'generating', 'ready', 'failed')),
    CONSTRAINT ck_reports__report_file_path_safe
        CHECK (
            report_file_path IS NULL
            OR (
                char_length(btrim(report_file_path)) > 0
                AND report_file_path !~ '^/'
                AND report_file_path !~ '(^|/)\.\.(/|$)'
            )
        ),
    CONSTRAINT ck_reports__content_sha256
        CHECK (
            content_sha256 IS NULL
            OR content_sha256 ~ '^[0-9a-f]{64}$'
        ),
    CONSTRAINT ck_reports__status_content
        CHECK (
            (
                report_status IN ('pending', 'generating')
                AND error_message IS NULL
            )
            OR (
                report_status = 'ready'
                AND report_markdown IS NOT NULL
                AND report_html IS NOT NULL
                AND report_file_path IS NOT NULL
                AND content_sha256 IS NOT NULL
                AND error_message IS NULL
            )
            OR (
                report_status = 'failed'
                AND error_message IS NOT NULL
            )
        )
);

CREATE TABLE system_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    version integer NOT NULL,
    default_timeout_seconds integer,
    max_concurrent_projects integer,
    log_retention_days integer,
    file_retention_days integer,
    enabled_environment_types varchar(64)[] DEFAULT ARRAY[]::varchar[] NOT NULL,
    settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    updated_by uuid NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_system_configs PRIMARY KEY (id),
    CONSTRAINT uq_system_configs__version UNIQUE (version),
    CONSTRAINT fk_system_configs__updated_by__users
        FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT ck_system_configs__version
        CHECK (version > 0),
    CONSTRAINT ck_system_configs__default_timeout_seconds
        CHECK (default_timeout_seconds IS NULL OR default_timeout_seconds > 0),
    CONSTRAINT ck_system_configs__max_concurrent_projects
        CHECK (max_concurrent_projects IS NULL OR max_concurrent_projects > 0),
    CONSTRAINT ck_system_configs__log_retention_days
        CHECK (log_retention_days IS NULL OR log_retention_days > 0),
    CONSTRAINT ck_system_configs__file_retention_days
        CHECK (file_retention_days IS NULL OR file_retention_days > 0),
    CONSTRAINT ck_system_configs__environment_types_no_null
        CHECK (array_position(enabled_environment_types, NULL) IS NULL),
    CONSTRAINT ck_system_configs__settings_object
        CHECK (jsonb_typeof(settings) = 'object')
);

CREATE TABLE audit_logs (
    id bigint GENERATED ALWAYS AS IDENTITY,
    actor_user_id uuid,
    project_id uuid,
    request_id uuid NOT NULL,
    action varchar(64) NOT NULL,
    object_type varchar(64) NOT NULL,
    object_id varchar(128),
    result_status varchar(16) NOT NULL,
    client_ip inet,
    idempotency_key varchar(128),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_audit_logs PRIMARY KEY (id),
    CONSTRAINT fk_audit_logs__actor_user_id__users
        FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_audit_logs__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL,
    CONSTRAINT ck_audit_logs__action_nonempty
        CHECK (char_length(btrim(action)) > 0),
    CONSTRAINT ck_audit_logs__object_type_nonempty
        CHECK (char_length(btrim(object_type)) > 0),
    CONSTRAINT ck_audit_logs__object_id_nonempty
        CHECK (object_id IS NULL OR char_length(btrim(object_id)) > 0),
    CONSTRAINT ck_audit_logs__result_status
        CHECK (result_status IN ('success', 'failure', 'denied')),
    CONSTRAINT ck_audit_logs__idempotency_key_nonempty
        CHECK (
            idempotency_key IS NULL
            OR char_length(btrim(idempotency_key)) > 0
        ),
    CONSTRAINT ck_audit_logs__metadata_object
        CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE TABLE domain_events (
    id bigint GENERATED ALWAYS AS IDENTITY,
    event_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    sequence bigint NOT NULL,
    event_type varchar(64) NOT NULL,
    aggregate_type varchar(64) NOT NULL,
    aggregate_id varchar(128) NOT NULL,
    payload jsonb NOT NULL,
    publish_status varchar(16) DEFAULT 'pending' NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    next_retry_at timestamptz,
    occurred_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    published_at timestamptz,
    last_error text,
    CONSTRAINT pk_domain_events PRIMARY KEY (id),
    CONSTRAINT uq_domain_events__event_id UNIQUE (event_id),
    CONSTRAINT uq_domain_events__project_id_sequence UNIQUE (project_id, sequence),
    CONSTRAINT fk_domain_events__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT ck_domain_events__sequence
        CHECK (sequence > 0),
    CONSTRAINT ck_domain_events__event_type
        CHECK (
            event_type IN (
                'project_status',
                'stage_status',
                'worker_status',
                'chat_message',
                'runtime_log',
                'resource_usage',
                'vulnerability_found',
                'report_ready'
            )
        ),
    CONSTRAINT ck_domain_events__aggregate_type_nonempty
        CHECK (char_length(btrim(aggregate_type)) > 0),
    CONSTRAINT ck_domain_events__aggregate_id_nonempty
        CHECK (char_length(btrim(aggregate_id)) > 0),
    CONSTRAINT ck_domain_events__payload_object
        CHECK (jsonb_typeof(payload) = 'object'),
    CONSTRAINT ck_domain_events__publish_status
        CHECK (publish_status IN ('pending', 'published', 'failed')),
    CONSTRAINT ck_domain_events__retry_count
        CHECK (retry_count >= 0),
    CONSTRAINT ck_domain_events__publish_state
        CHECK (
            (
                publish_status = 'pending'
                AND published_at IS NULL
                AND last_error IS NULL
            )
            OR (
                publish_status = 'published'
                AND published_at IS NOT NULL
                AND last_error IS NULL
            )
            OR (
                publish_status = 'failed'
                AND published_at IS NULL
                AND last_error IS NOT NULL
            )
        )
);

CREATE TABLE file_artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    report_id uuid,
    vulnerability_id uuid,
    created_by_task_id uuid,
    artifact_type varchar(32) NOT NULL,
    logical_key text NOT NULL,
    content_sha256 char(64) NOT NULL,
    size_bytes bigint NOT NULL,
    media_type varchar(127) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT pk_file_artifacts PRIMARY KEY (id),
    CONSTRAINT uq_file_artifacts__logical_key UNIQUE (logical_key),
    CONSTRAINT fk_file_artifacts__project_id__projects
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_file_artifacts__report_scope__reports
        FOREIGN KEY (report_id, project_id)
        REFERENCES reports (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_file_artifacts__vuln_scope__vulnerabilities
        FOREIGN KEY (vulnerability_id, project_id)
        REFERENCES vulnerabilities (id, project_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_file_artifacts__task_scope__worker_tasks
        FOREIGN KEY (created_by_task_id, project_id)
        REFERENCES worker_tasks (id, project_id)
        ON DELETE NO ACTION,
    CONSTRAINT ck_file_artifacts__artifact_type
        CHECK (
            artifact_type IN (
                'report',
                'evidence',
                'archived_log',
                'workspace_output'
            )
        ),
    CONSTRAINT ck_file_artifacts__logical_key_safe
        CHECK (
            char_length(btrim(logical_key)) > 0
            AND logical_key !~ '^/'
            AND logical_key !~ '(^|/)\.\.(/|$)'
        ),
    CONSTRAINT ck_file_artifacts__content_sha256
        CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_file_artifacts__size_bytes
        CHECK (size_bytes >= 0),
    CONSTRAINT ck_file_artifacts__media_type_nonempty
        CHECK (char_length(btrim(media_type)) > 0),
    CONSTRAINT ck_file_artifacts__owner
        CHECK (
            (
                artifact_type = 'report'
                AND report_id IS NOT NULL
                AND vulnerability_id IS NULL
            )
            OR (
                artifact_type = 'evidence'
                AND report_id IS NULL
                AND vulnerability_id IS NOT NULL
            )
            OR (
                artifact_type IN ('archived_log', 'workspace_output')
                AND report_id IS NULL
                AND vulnerability_id IS NULL
            )
        )
);

CREATE UNIQUE INDEX uq_project_runtimes__runtime_identifier
    ON project_runtimes (runtime_identifier)
    WHERE runtime_identifier IS NOT NULL;

CREATE INDEX ix_projects__created_by_created_at
    ON projects (created_by, created_at DESC);

CREATE INDEX ix_projects__project_status_updated_at
    ON projects (project_status, updated_at DESC);

CREATE INDEX ix_runtime_stages__project_id_stage_order
    ON runtime_stages (project_id, stage_order);

CREATE INDEX ix_worker_tasks__project_id_created_at
    ON worker_tasks (project_id, created_at DESC);

CREATE INDEX ix_worker_tasks__stage_id_task_status
    ON worker_tasks (stage_id, task_status);

CREATE UNIQUE INDEX uq_worker_tasks__project_id_idempotency_key
    ON worker_tasks (project_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX ix_vulnerabilities__project_id_risk_verify
    ON vulnerabilities (project_id, risk_level, verify_status, created_at DESC);

CREATE INDEX ix_vulnerabilities__discovered_by_task_id
    ON vulnerabilities (discovered_by_task_id)
    WHERE discovered_by_task_id IS NOT NULL;

CREATE INDEX ix_vulnerabilities__verified_by_task_id
    ON vulnerabilities (verified_by_task_id)
    WHERE verified_by_task_id IS NOT NULL;

CREATE INDEX ix_attack_paths__project_id_created_at
    ON attack_paths (project_id, created_at DESC);

CREATE INDEX ix_attack_paths__created_by_task_id
    ON attack_paths (created_by_task_id)
    WHERE created_by_task_id IS NOT NULL;

CREATE INDEX ix_attack_path_items__project_id
    ON attack_path_items (project_id);

CREATE INDEX ix_attack_path_items__vuln_id
    ON attack_path_items (vuln_id);

CREATE INDEX ix_chat_messages__project_id_created_at
    ON chat_messages (project_id, created_at DESC, id DESC);

CREATE INDEX ix_chat_messages__stage_id_created_at
    ON chat_messages (stage_id, created_at DESC)
    WHERE stage_id IS NOT NULL;

CREATE INDEX ix_chat_messages__worker_task_id
    ON chat_messages (worker_task_id)
    WHERE worker_task_id IS NOT NULL;

CREATE INDEX ix_runtime_logs__project_id_created_at
    ON runtime_logs (project_id, created_at DESC, id DESC);

CREATE INDEX ix_runtime_logs__stage_id_created_at
    ON runtime_logs (stage_id, created_at DESC)
    WHERE stage_id IS NOT NULL;

CREATE INDEX ix_runtime_logs__worker_task_id_created_at
    ON runtime_logs (worker_task_id, created_at DESC)
    WHERE worker_task_id IS NOT NULL;

CREATE INDEX ix_runtime_logs__request_id
    ON runtime_logs (request_id)
    WHERE request_id IS NOT NULL;

CREATE INDEX ix_resource_usages__project_id_recorded_at
    ON resource_usages (project_id, recorded_at DESC, id DESC);

CREATE INDEX ix_resource_usages__runtime_id_recorded_at
    ON resource_usages (runtime_id, recorded_at DESC);

CREATE INDEX ix_reports__project_id_status_created_at
    ON reports (project_id, report_status, created_at DESC);

CREATE UNIQUE INDEX uq_system_configs__one_active
    ON system_configs (is_active)
    WHERE is_active;

CREATE INDEX ix_system_configs__updated_by_created_at
    ON system_configs (updated_by, created_at DESC);

CREATE INDEX ix_audit_logs__actor_user_id_created_at
    ON audit_logs (actor_user_id, created_at DESC, id DESC)
    WHERE actor_user_id IS NOT NULL;

CREATE INDEX ix_audit_logs__project_id_created_at
    ON audit_logs (project_id, created_at DESC, id DESC)
    WHERE project_id IS NOT NULL;

CREATE INDEX ix_audit_logs__action_created_at
    ON audit_logs (action, created_at DESC);

CREATE INDEX ix_audit_logs__request_id
    ON audit_logs (request_id);

CREATE INDEX ix_domain_events__relay_pending
    ON domain_events (publish_status, next_retry_at, id)
    WHERE publish_status IN ('pending', 'failed');

CREATE INDEX ix_domain_events__project_id_occurred_at
    ON domain_events (project_id, occurred_at DESC);

CREATE UNIQUE INDEX uq_file_artifacts__report_id_report
    ON file_artifacts (report_id)
    WHERE artifact_type = 'report';

CREATE INDEX ix_file_artifacts__project_id_type_created_at
    ON file_artifacts (project_id, artifact_type, created_at DESC);

CREATE INDEX ix_file_artifacts__vulnerability_id
    ON file_artifacts (vulnerability_id)
    WHERE vulnerability_id IS NOT NULL;

CREATE INDEX ix_file_artifacts__created_by_task_id
    ON file_artifacts (created_by_task_id)
    WHERE created_by_task_id IS NOT NULL;

CREATE FUNCTION enforce_attack_path_step_order()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    affected_path_id uuid;
    row_count bigint;
    min_step integer;
    max_step integer;
BEGIN
    FOR affected_path_id IN
        SELECT DISTINCT path_id
        FROM (
            SELECT CASE WHEN TG_OP <> 'DELETE' THEN NEW.path_id END AS path_id
            UNION ALL
            SELECT CASE WHEN TG_OP <> 'INSERT' THEN OLD.path_id END AS path_id
        ) AS affected
        WHERE path_id IS NOT NULL
    LOOP
        IF EXISTS (SELECT 1 FROM attack_paths WHERE id = affected_path_id) THEN
            SELECT count(*), min(step_order), max(step_order)
            INTO row_count, min_step, max_step
            FROM attack_path_items
            WHERE path_id = affected_path_id;

            IF row_count = 0 OR min_step <> 1 OR max_step <> row_count THEN
                RAISE EXCEPTION
                    'attack path % step_order must be continuous from 1',
                    affected_path_id
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END LOOP;

    RETURN NULL;
END;
$$;

CREATE FUNCTION enforce_attack_path_has_items()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM attack_paths WHERE id = NEW.id)
       AND NOT EXISTS (
           SELECT 1
           FROM attack_path_items
           WHERE path_id = NEW.id
       ) THEN
        RAISE EXCEPTION
            'attack path % must contain at least one item',
            NEW.id
            USING ERRCODE = '23514';
    END IF;

    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER ck_attack_path_items__continuous_step_order
AFTER INSERT OR UPDATE OR DELETE ON attack_path_items
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_attack_path_step_order();

CREATE CONSTRAINT TRIGGER ck_attack_paths__has_items
AFTER INSERT OR UPDATE ON attack_paths
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_attack_path_has_items();

CREATE TRIGGER trg_users__set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_projects__set_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_project_runtimes__set_updated_at
BEFORE UPDATE ON project_runtimes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_runtime_stages__set_updated_at
BEFORE UPDATE ON runtime_stages
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_worker_tasks__set_updated_at
BEFORE UPDATE ON worker_tasks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_vulnerabilities__set_updated_at
BEFORE UPDATE ON vulnerabilities
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_attack_paths__set_updated_at
BEFORE UPDATE ON attack_paths
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_reports__set_updated_at
BEFORE UPDATE ON reports
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_system_configs__set_updated_at
BEFORE UPDATE ON system_configs
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON FUNCTION set_updated_at() IS '统一维护业务表 updated_at';
COMMENT ON FUNCTION enforce_attack_path_step_order() IS '事务提交前校验攻击路径步骤从 1 连续编号';
COMMENT ON FUNCTION enforce_attack_path_has_items() IS '事务提交前校验攻击路径至少包含一个步骤';

COMMENT ON TABLE users IS '系统用户及管理员账户';
COMMENT ON COLUMN users.id IS '用户 UUID';
COMMENT ON COLUMN users.username IS '规范化为小写的登录名';
COMMENT ON COLUMN users.password_hash IS 'Argon2id 密码哈希';
COMMENT ON COLUMN users.role IS '角色：user 或 admin';
COMMENT ON COLUMN users.status IS '账户状态：active 或 disabled';
COMMENT ON COLUMN users.created_at IS '创建时间，UTC';
COMMENT ON COLUMN users.updated_at IS '更新时间，UTC';

COMMENT ON TABLE projects IS '源码安全评估项目';
COMMENT ON COLUMN projects.id IS '项目 UUID';
COMMENT ON COLUMN projects.project_name IS '项目名称';
COMMENT ON COLUMN projects.source_type IS '源码类型：local 或 repository';
COMMENT ON COLUMN projects.source_path IS '受控根目录内相对路径或已脱敏仓库地址';
COMMENT ON COLUMN projects.task_content IS '本次评估任务说明';
COMMENT ON COLUMN projects.environment_type IS '管理员启用的隔离环境类型';
COMMENT ON COLUMN projects.project_status IS '项目状态';
COMMENT ON COLUMN projects.created_by IS '项目创建用户';
COMMENT ON COLUMN projects.stop_requested_at IS '项目级协作取消请求时间';
COMMENT ON COLUMN projects.created_at IS '创建时间，UTC';
COMMENT ON COLUMN projects.updated_at IS '更新时间，UTC';

COMMENT ON TABLE project_runtimes IS '项目隔离运行实例和环境快照';
COMMENT ON COLUMN project_runtimes.id IS '运行实例 UUID';
COMMENT ON COLUMN project_runtimes.project_id IS '所属项目；MVP 唯一';
COMMENT ON COLUMN project_runtimes.runtime_identifier IS '执行网关返回的独立环境编号';
COMMENT ON COLUMN project_runtimes.container_status IS '隔离容器生命周期状态';
COMMENT ON COLUMN project_runtimes.workspace_key IS '项目工作目录逻辑键';
COMMENT ON COLUMN project_runtimes.repository_key IS '拉取后源码目录逻辑键';
COMMENT ON COLUMN project_runtimes.environment_snapshot IS '启动时环境与运行配置快照，不含密钥';
COMMENT ON COLUMN project_runtimes.started_at IS '运行实例启动完成时间';
COMMENT ON COLUMN project_runtimes.stopped_at IS '运行实例停止时间';
COMMENT ON COLUMN project_runtimes.destroyed_at IS '运行实例销毁时间';
COMMENT ON COLUMN project_runtimes.error_message IS '环境生命周期错误摘要';
COMMENT ON COLUMN project_runtimes.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN project_runtimes.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE runtime_stages IS '项目运行阶段状态';
COMMENT ON COLUMN runtime_stages.id IS '阶段 UUID';
COMMENT ON COLUMN runtime_stages.project_id IS '所属项目';
COMMENT ON COLUMN runtime_stages.runtime_id IS '所属运行实例';
COMMENT ON COLUMN runtime_stages.stage_name IS '固定阶段名称';
COMMENT ON COLUMN runtime_stages.stage_order IS '阶段顺序 1 至 5';
COMMENT ON COLUMN runtime_stages.stage_status IS '阶段状态';
COMMENT ON COLUMN runtime_stages.started_at IS '阶段开始时间';
COMMENT ON COLUMN runtime_stages.finished_at IS '阶段结束时间';
COMMENT ON COLUMN runtime_stages.error_message IS '阶段失败原因';
COMMENT ON COLUMN runtime_stages.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN runtime_stages.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE worker_tasks IS 'AI 角色及运维角色的独立执行任务';
COMMENT ON COLUMN worker_tasks.id IS '角色任务 UUID';
COMMENT ON COLUMN worker_tasks.project_id IS '所属项目';
COMMENT ON COLUMN worker_tasks.stage_id IS '所属阶段';
COMMENT ON COLUMN worker_tasks.worker_role IS '六类执行角色之一';
COMMENT ON COLUMN worker_tasks.task_content IS '分发给角色的任务内容';
COMMENT ON COLUMN worker_tasks.task_status IS '角色任务状态';
COMMENT ON COLUMN worker_tasks.result_summary IS '结构化结果的可读摘要';
COMMENT ON COLUMN worker_tasks.error_message IS '任务失败原因';
COMMENT ON COLUMN worker_tasks.request_id IS '全链路请求 UUID';
COMMENT ON COLUMN worker_tasks.idempotency_key IS '项目内任务幂等键';
COMMENT ON COLUMN worker_tasks.attempt_count IS '已执行尝试次数';
COMMENT ON COLUMN worker_tasks.started_at IS '任务开始时间';
COMMENT ON COLUMN worker_tasks.finished_at IS '任务结束时间';
COMMENT ON COLUMN worker_tasks.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN worker_tasks.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE vulnerabilities IS '候选及验证后的漏洞记录';
COMMENT ON COLUMN vulnerabilities.id IS '漏洞 UUID';
COMMENT ON COLUMN vulnerabilities.project_id IS '所属项目';
COMMENT ON COLUMN vulnerabilities.discovered_by_task_id IS '发现漏洞的角色任务';
COMMENT ON COLUMN vulnerabilities.verified_by_task_id IS '验证漏洞的角色任务';
COMMENT ON COLUMN vulnerabilities.vuln_code IS '项目内唯一漏洞编号';
COMMENT ON COLUMN vulnerabilities.vuln_title IS '漏洞标题';
COMMENT ON COLUMN vulnerabilities.rule_type IS '漏洞规则或类别';
COMMENT ON COLUMN vulnerabilities.risk_level IS '风险等级';
COMMENT ON COLUMN vulnerabilities.file_path IS '项目源码内相对路径';
COMMENT ON COLUMN vulnerabilities.line_start IS '起始行号';
COMMENT ON COLUMN vulnerabilities.line_end IS '结束行号';
COMMENT ON COLUMN vulnerabilities.impact_text IS '漏洞影响';
COMMENT ON COLUMN vulnerabilities.condition_text IS '触发条件';
COMMENT ON COLUMN vulnerabilities.evidence_text IS '漏洞证据';
COMMENT ON COLUMN vulnerabilities.evidence_fingerprint IS '规则、位置和证据组合的 SHA-256 指纹';
COMMENT ON COLUMN vulnerabilities.verify_status IS '验证状态';
COMMENT ON COLUMN vulnerabilities.reproduce_steps_text IS '复现步骤';
COMMENT ON COLUMN vulnerabilities.verify_code_text IS '验证代码';
COMMENT ON COLUMN vulnerabilities.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN vulnerabilities.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE attack_paths IS '同项目漏洞组成的攻击路径';
COMMENT ON COLUMN attack_paths.id IS '攻击路径 UUID';
COMMENT ON COLUMN attack_paths.project_id IS '所属项目';
COMMENT ON COLUMN attack_paths.created_by_task_id IS '生成攻击路径的角色任务';
COMMENT ON COLUMN attack_paths.path_code IS '项目内唯一攻击路径编号';
COMMENT ON COLUMN attack_paths.path_title IS '攻击路径标题';
COMMENT ON COLUMN attack_paths.path_summary IS '攻击路径摘要';
COMMENT ON COLUMN attack_paths.final_impact_text IS '最终影响';
COMMENT ON COLUMN attack_paths.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN attack_paths.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE attack_path_items IS '攻击路径中的有序漏洞步骤';
COMMENT ON COLUMN attack_path_items.id IS '内部自增主键';
COMMENT ON COLUMN attack_path_items.project_id IS '所属项目，用于跨项目一致性约束';
COMMENT ON COLUMN attack_path_items.path_id IS '所属攻击路径';
COMMENT ON COLUMN attack_path_items.vuln_id IS '关联漏洞';
COMMENT ON COLUMN attack_path_items.step_order IS '从 1 开始的连续步骤序号';
COMMENT ON COLUMN attack_path_items.step_text IS '该步利用说明';
COMMENT ON COLUMN attack_path_items.created_at IS '记录创建时间，UTC';

COMMENT ON TABLE chat_messages IS '项目执行过程中的角色协作消息';
COMMENT ON COLUMN chat_messages.id IS '内部自增主键';
COMMENT ON COLUMN chat_messages.project_id IS '所属项目';
COMMENT ON COLUMN chat_messages.stage_id IS '可选所属阶段';
COMMENT ON COLUMN chat_messages.worker_task_id IS '可选所属角色任务';
COMMENT ON COLUMN chat_messages.worker_role IS '可选消息发送角色';
COMMENT ON COLUMN chat_messages.message_type IS '消息类型，具体值待角色协议确认';
COMMENT ON COLUMN chat_messages.message_text IS '消息正文';
COMMENT ON COLUMN chat_messages.created_at IS '消息创建时间，UTC';

COMMENT ON TABLE runtime_logs IS '可查询的项目结构化运行日志';
COMMENT ON COLUMN runtime_logs.id IS '内部自增主键';
COMMENT ON COLUMN runtime_logs.project_id IS '所属项目';
COMMENT ON COLUMN runtime_logs.stage_id IS '可选所属阶段';
COMMENT ON COLUMN runtime_logs.worker_task_id IS '可选所属角色任务';
COMMENT ON COLUMN runtime_logs.request_id IS '可选全链路请求 UUID';
COMMENT ON COLUMN runtime_logs.log_level IS '日志级别';
COMMENT ON COLUMN runtime_logs.log_content IS '脱敏后的日志正文';
COMMENT ON COLUMN runtime_logs.created_at IS '日志时间，UTC';

COMMENT ON TABLE resource_usages IS '项目运行实例资源采样';
COMMENT ON COLUMN resource_usages.id IS '内部自增主键';
COMMENT ON COLUMN resource_usages.project_id IS '所属项目';
COMMENT ON COLUMN resource_usages.runtime_id IS '所属运行实例';
COMMENT ON COLUMN resource_usages.cpu_usage IS '容器 CPU 使用率百分值，可超过 100';
COMMENT ON COLUMN resource_usages.memory_usage IS '内存使用字节数';
COMMENT ON COLUMN resource_usages.token_count IS '采样时累计模型 token 数';
COMMENT ON COLUMN resource_usages.recorded_at IS '采样时间，UTC';

COMMENT ON TABLE reports IS '项目安全评估报告内容和下载逻辑键';
COMMENT ON COLUMN reports.id IS '报告 UUID';
COMMENT ON COLUMN reports.project_id IS '所属项目';
COMMENT ON COLUMN reports.generated_by_task_id IS '生成报告的角色任务';
COMMENT ON COLUMN reports.version IS '项目内报告版本号';
COMMENT ON COLUMN reports.report_status IS '报告生成状态';
COMMENT ON COLUMN reports.report_markdown IS 'Markdown 报告正文';
COMMENT ON COLUMN reports.report_html IS '清理后的 HTML 报告正文';
COMMENT ON COLUMN reports.report_file_path IS '可下载报告的逻辑文件键';
COMMENT ON COLUMN reports.content_sha256 IS '报告文件 SHA-256';
COMMENT ON COLUMN reports.error_message IS '报告生成失败原因';
COMMENT ON COLUMN reports.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN reports.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE system_configs IS '版本化系统运行配置';
COMMENT ON COLUMN system_configs.id IS '配置版本 UUID';
COMMENT ON COLUMN system_configs.version IS '单调递增配置版本';
COMMENT ON COLUMN system_configs.default_timeout_seconds IS '默认任务超时秒数，未确认时为空';
COMMENT ON COLUMN system_configs.max_concurrent_projects IS '最大并发项目数，未确认时为空';
COMMENT ON COLUMN system_configs.log_retention_days IS '数据库及归档日志保留天数，未确认时为空';
COMMENT ON COLUMN system_configs.file_retention_days IS '报告和工作文件保留天数，未确认时为空';
COMMENT ON COLUMN system_configs.enabled_environment_types IS '启用的隔离环境类型标识集合';
COMMENT ON COLUMN system_configs.settings IS '不含密钥的扩展配置对象';
COMMENT ON COLUMN system_configs.is_active IS '是否为当前生效版本';
COMMENT ON COLUMN system_configs.updated_by IS '创建或激活该配置的管理员';
COMMENT ON COLUMN system_configs.created_at IS '记录创建时间，UTC';
COMMENT ON COLUMN system_configs.updated_at IS '记录更新时间，UTC';

COMMENT ON TABLE audit_logs IS '关键用户操作和管理操作审计';
COMMENT ON COLUMN audit_logs.id IS '内部自增主键';
COMMENT ON COLUMN audit_logs.actor_user_id IS '操作者；用户删除后可为空';
COMMENT ON COLUMN audit_logs.project_id IS '关联项目；项目删除后置空';
COMMENT ON COLUMN audit_logs.request_id IS '全链路请求 UUID';
COMMENT ON COLUMN audit_logs.action IS '操作标识';
COMMENT ON COLUMN audit_logs.object_type IS '操作对象类型';
COMMENT ON COLUMN audit_logs.object_id IS '脱敏后的对象标识快照';
COMMENT ON COLUMN audit_logs.result_status IS '操作结果';
COMMENT ON COLUMN audit_logs.client_ip IS '客户端 IP';
COMMENT ON COLUMN audit_logs.idempotency_key IS '写操作幂等键';
COMMENT ON COLUMN audit_logs.metadata IS '脱敏后的审计扩展信息';
COMMENT ON COLUMN audit_logs.created_at IS '审计发生时间，UTC';

COMMENT ON TABLE domain_events IS '事务性 Outbox 领域事件';
COMMENT ON COLUMN domain_events.id IS '内部自增主键';
COMMENT ON COLUMN domain_events.event_id IS '全局唯一事件 UUID';
COMMENT ON COLUMN domain_events.project_id IS '所属项目';
COMMENT ON COLUMN domain_events.sequence IS '项目内单调递增事件序号';
COMMENT ON COLUMN domain_events.event_type IS 'WebSocket 事件类型';
COMMENT ON COLUMN domain_events.aggregate_type IS '事件聚合根类型';
COMMENT ON COLUMN domain_events.aggregate_id IS '聚合根标识字符串';
COMMENT ON COLUMN domain_events.payload IS '不含密钥的事件载荷对象';
COMMENT ON COLUMN domain_events.publish_status IS 'Outbox 投递状态';
COMMENT ON COLUMN domain_events.retry_count IS '投递重试次数';
COMMENT ON COLUMN domain_events.next_retry_at IS '下次允许重试时间';
COMMENT ON COLUMN domain_events.occurred_at IS '领域事件发生时间，UTC';
COMMENT ON COLUMN domain_events.published_at IS '成功投递时间，UTC';
COMMENT ON COLUMN domain_events.last_error IS '最近一次投递错误摘要';

COMMENT ON TABLE file_artifacts IS '报告、证据、归档日志和工作输出的文件元数据';
COMMENT ON COLUMN file_artifacts.id IS '文件制品 UUID';
COMMENT ON COLUMN file_artifacts.project_id IS '所属项目';
COMMENT ON COLUMN file_artifacts.report_id IS '报告制品对应的报告';
COMMENT ON COLUMN file_artifacts.vulnerability_id IS '证据制品对应的漏洞';
COMMENT ON COLUMN file_artifacts.created_by_task_id IS '生成文件的角色任务';
COMMENT ON COLUMN file_artifacts.artifact_type IS '文件制品类型';
COMMENT ON COLUMN file_artifacts.logical_key IS 'ArtifactStorage 逻辑键或项目内相对路径';
COMMENT ON COLUMN file_artifacts.content_sha256 IS '文件内容 SHA-256';
COMMENT ON COLUMN file_artifacts.size_bytes IS '文件大小，单位字节';
COMMENT ON COLUMN file_artifacts.media_type IS 'IANA 媒体类型';
COMMENT ON COLUMN file_artifacts.created_at IS '记录创建时间，UTC';

COMMIT;