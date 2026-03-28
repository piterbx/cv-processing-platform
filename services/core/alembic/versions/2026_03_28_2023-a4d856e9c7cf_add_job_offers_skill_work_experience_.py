"""add job_offers skill work_experience and application tables

Revision ID: a4d856e9c7cf
Revises: 331eaf756256
Create Date: 2026-03-28 20:23:32.246796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4d856e9c7cf'
down_revision: Union[str, Sequence[str], None] = '331eaf756256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('candidates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('total_experience_years', sa.Integer(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_email'), 'candidates', ['email'], unique=True)
    op.create_table('job_offers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_name'), 'skills', ['name'], unique=True)
    op.create_table('candidate_skills',
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('candidate_id', 'skill_id')
    )
    op.create_table('work_experiences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('company', sa.String(length=255), nullable=False),
    sa.Column('position', sa.String(length=255), nullable=False),
    sa.Column('start_date', sa.String(length=50), nullable=True),
    sa.Column('end_date', sa.String(length=50), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('applications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('candidate_id', sa.Integer(), nullable=False),
    sa.Column('job_offer_id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('documents', sa.Column('candidate_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_documents_candidate_id', 'documents', 'candidates', ['candidate_id'], ['id'], ondelete='CASCADE')
    
    op.drop_index('ix_unique_content_hash', table_name='documents')
    op.create_index(
        'ix_unique_content_hash', 
        'documents', 
        ['content_hash'], 
        unique=True, 
        postgresql_where=sa.text("status IN ('PROCESSING', 'AWAITING_REVIEW', 'COMPLETED')")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_unique_content_hash', table_name='documents')
    op.create_index(
        'ix_unique_content_hash', 
        'documents', 
        ['content_hash'], 
        unique=True, 
        postgresql_where=sa.text("status IN ('PROCESSING', 'COMPLETED')")
    )

    op.drop_constraint('fk_documents_candidate_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'candidate_id')
    op.drop_table('applications')
    op.drop_table('work_experiences')
    op.drop_table('candidate_skills')
    op.drop_index(op.f('ix_skills_name'), table_name='skills')
    op.drop_table('skills')
    op.drop_table('job_offers')
    op.drop_index(op.f('ix_candidates_email'), table_name='candidates')
    op.drop_table('candidates')
