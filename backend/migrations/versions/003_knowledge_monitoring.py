"""漏洞、攻击路径、报告、监控、知识库表结构。

Revision ID: 003
Revises: 002
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── vulnerabilities ──
    op.create_table(
        "vulnerabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_vulnerabilities__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("vuln_code", sa.String(64), nullable=False),
        sa.Column("vuln_title", sa.String(256), nullable=False),
        sa.Column("rule_type", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("impact_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("condition_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("evidence_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("verify_status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("reproduce_steps_text", sa.Text()),
        sa.Column("verify_code_text", sa.Text()),
        sa.Column("discovered_by_task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("verified_by_task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("risk_level IN ('critical', 'high', 'medium', 'low', 'info')", name="risk_level"),
        sa.CheckConstraint("verify_status IN ('pending', 'verified', 'rejected')", name="verify_status"),
        sa.CheckConstraint("line_start > 0", name="line_start"),
        sa.CheckConstraint("line_end >= line_start", name="line_end"),
    )
    _create_updated_at_trigger("vulnerabilities")

    # ── attack_paths ──
    op.create_table(
        "attack_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_attack_paths__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("path_code", sa.String(64), nullable=False),
        sa.Column("path_title", sa.String(256), nullable=False),
        sa.Column("path_summary", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("final_impact_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("vulnerability_codes", postgresql.ARRAY(sa.String(64))),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── attack_path_steps ──
    op.create_table(
        "attack_path_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("path_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("attack_paths.id", name="fk_attack_path_steps__path_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("vuln_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("vulnerabilities.id", name="fk_attack_path_steps__vuln_id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("step_order >= 0", name="step_order"),
    )

    # ── reports ──
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_reports__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("report_status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("report_markdown", sa.Text()),
        sa.Column("report_html", sa.Text()),
        sa.Column("download_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("content_sha256", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("report_status IN ('pending', 'generating', 'ready', 'failed')", name="report_status"),
        sa.CheckConstraint("version > 0", name="version"),
    )
    _create_updated_at_trigger("reports")

    # ── chat_messages ──
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_chat_messages__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("worker_role", sa.String(64), nullable=False),
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── runtime_logs ──
    op.create_table(
        "runtime_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_runtime_logs__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True)),
        sa.Column("worker_task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("request_id", postgresql.UUID(as_uuid=True)),
        sa.Column("log_level", sa.String(16), nullable=False),
        sa.Column("log_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("log_level IN ('debug', 'info', 'warning', 'error')", name="log_level"),
    )

    # ── resource_samples ──
    op.create_table(
        "resource_samples",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_resource_samples__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("cpu_usage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("memory_usage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("token_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ── knowledge_entries ──
    op.create_table(
        "knowledge_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("knowledge_type", sa.String(64), nullable=False),
        sa.Column("language", sa.String(32)),
        sa.Column("framework", sa.String(64)),
        sa.Column("risk_level", sa.String(16)),
        sa.Column("tags", postgresql.ARRAY(sa.String(64)), nullable=False,
                  server_default=sa.text("ARRAY[]::varchar[]")),
        sa.Column("entry_status", sa.String(16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("source_type", sa.String(32), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("source_url", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", name="fk_knowledge_entries__created_by", ondelete="SET NULL")),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", name="fk_knowledge_entries__reviewed_by", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "knowledge_type IN "
            "('vulnerability_pattern', 'security_standard', 'remediation_advice', 'historical_assessment')",
            name="knowledge_type"),
        sa.CheckConstraint("entry_status IN ('active', 'disabled', 'draft')", name="entry_status"),
        sa.CheckConstraint("source_type IN ('manual', 'external_import', 'auto_curated')", name="source_type"),
        sa.CheckConstraint("version > 0", name="version"),
        sa.CheckConstraint("char_length(btrim(title)) > 0", name="title_nonempty"),
        sa.CheckConstraint("char_length(btrim(content_text)) > 0", name="content_nonempty"),
    )
    _create_updated_at_trigger("knowledge_entries")

    # ── knowledge_retrievals ──
    op.create_table(
        "knowledge_retrievals",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", name="fk_knowledge_retrievals__project_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True)),
        sa.Column("worker_task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("retrieval_type", sa.String(32), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("filter_language", sa.String(32)),
        sa.Column("filter_knowledge_types", postgresql.ARRAY(sa.String(64))),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("retrieved_entries", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("top_score", sa.Float()),
        sa.Column("avg_score", sa.Float()),
        sa.Column("retrieval_duration_ms", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("retrieval_type IN ('stage_pre', 'role_pre', 'tool_triggered')", name="retrieval_type"),
        sa.CheckConstraint("top_k > 0", name="top_k"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_retrievals")
    op.execute("DROP TRIGGER IF EXISTS trg_knowledge_entries__set_updated_at ON knowledge_entries")
    op.drop_table("knowledge_entries")
    op.drop_table("resource_samples")
    op.drop_table("runtime_logs")
    op.drop_table("chat_messages")
    op.execute("DROP TRIGGER IF EXISTS trg_reports__set_updated_at ON reports")
    op.drop_table("reports")
    op.drop_table("attack_path_steps")
    op.drop_table("attack_paths")
    op.execute("DROP TRIGGER IF EXISTS trg_vulnerabilities__set_updated_at ON vulnerabilities")
    op.drop_table("vulnerabilities")


def _create_updated_at_trigger(table_name: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}__set_updated_at
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
