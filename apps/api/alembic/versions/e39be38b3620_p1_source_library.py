"""p1 source library: source identity, transcript versions/raw files, keyword search, workflow runs

Revision ID: e39be38b3620
Revises: 5d669179817c
Create Date: 2026-10-01 19:10:54.566579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e39be38b3620'
down_revision: Union[str, Sequence[str], None] = '5d669179817c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('workflow_runs',
    sa.Column('kind', sa.String(length=64), nullable=False),
    sa.Column('subject_type', sa.String(length=32), nullable=False),
    sa.Column('subject_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('queued', 'running', 'succeeded', 'failed', 'interrupted', name='run_status', native_enum=False, length=32), nullable=False),
    sa.Column('attempt', sa.Integer(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('progress', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workflow_runs')),
    sa.UniqueConstraint('idempotency_key', name=op.f('uq_workflow_runs_idempotency_key'))
    )
    op.create_index(op.f('ix_workflow_runs_status'), 'workflow_runs', ['status'], unique=False)
    op.create_index('ix_workflow_runs_subject', 'workflow_runs', ['subject_type', 'subject_id'], unique=False)
    op.create_index('uq_workflow_runs_active', 'workflow_runs', ['kind', 'subject_id'], unique=True, postgresql_where=sa.text("status IN ('queued', 'running')"))
    # Existing rows are YouTube sources. The default only backfills; model defaults stay Python-side.
    op.add_column('source_videos', sa.Column('kind', sa.String(length=16), nullable=False, server_default='youtube'))
    op.alter_column('source_videos', 'kind', server_default=None)
    op.add_column('source_videos', sa.Column('fingerprint', sa.String(length=64), nullable=True))
    op.add_column('source_videos', sa.Column('thumbnail_url', sa.String(length=2048), nullable=True))
    op.alter_column('source_videos', 'url',
               existing_type=sa.VARCHAR(length=2048),
               nullable=True)
    op.create_index(op.f('ix_source_videos_fingerprint'), 'source_videos', ['fingerprint'], unique=False)
    op.add_column('transcript_chunks', sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('simple', text)", persisted=True), nullable=False))
    op.create_index('ix_transcript_chunks_search_vector', 'transcript_chunks', ['search_vector'], unique=False, postgresql_using='gin')
    # Every existing transcript becomes the current one (there was at most one per version).
    op.add_column('transcripts', sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column('transcripts', 'is_current', server_default=None)
    op.add_column('transcripts', sa.Column('raw_storage_key', sa.String(length=1024), nullable=True))
    op.add_column('transcripts', sa.Column('raw_sha256', sa.String(length=64), nullable=True))
    op.add_column('transcripts', sa.Column('normalizer_version', sa.String(length=16), nullable=True))
    op.create_index('uq_transcripts_current', 'transcripts', ['source_video_id'], unique=True, postgresql_where=sa.text('is_current'))


def downgrade() -> None:
    """Downgrade schema."""
    # NOTE: if several transcript versions exist per source, only the newest keeps is_current=true on
    # re-upgrade; downgrade drops the column and with it the "current" marker.
    op.drop_index('uq_transcripts_current', table_name='transcripts', postgresql_where=sa.text('is_current'))
    op.drop_column('transcripts', 'normalizer_version')
    op.drop_column('transcripts', 'raw_sha256')
    op.drop_column('transcripts', 'raw_storage_key')
    op.drop_column('transcripts', 'is_current')
    op.drop_index('ix_transcript_chunks_search_vector', table_name='transcript_chunks', postgresql_using='gin')
    op.drop_column('transcript_chunks', 'search_vector')
    op.drop_index(op.f('ix_source_videos_fingerprint'), table_name='source_videos')
    # Upload sources have no URL; keep their rows by giving them a placeholder before restoring NOT NULL.
    op.execute("UPDATE source_videos SET url = 'upload://' || external_id WHERE url IS NULL")
    op.alter_column('source_videos', 'url',
               existing_type=sa.VARCHAR(length=2048),
               nullable=False)
    op.drop_column('source_videos', 'thumbnail_url')
    op.drop_column('source_videos', 'fingerprint')
    op.drop_column('source_videos', 'kind')
    op.drop_index('uq_workflow_runs_active', table_name='workflow_runs', postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.drop_index('ix_workflow_runs_subject', table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_status'), table_name='workflow_runs')
    op.drop_table('workflow_runs')
