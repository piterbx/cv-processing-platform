"""use enums for status fields

Revision ID: 8057392d86cf
Revises: 03718c7b3328
Create Date: 2026-04-03 01:42:20.569457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8057392d86cf'
down_revision: Union[str, Sequence[str], None] = '03718c7b3328'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index('ix_unique_content_hash', table_name='documents')

    application_status_enum = postgresql.ENUM('NEW', 'SCREENING', 'CONTACTED', 'INTERVIEW', 'TECHNICAL_TEST', 'OFFER_SENT', 'HIRED', 'REJECTED', 'WITHDRAWN', 'GHOSTED', name='applicationstatus')
    application_status_enum.create(op.get_bind())

    document_status_enum = postgresql.ENUM('PENDING', 'UPLOADED', 'PROCESSING', 'DUPLICATE', 'FAILED', 'AWAITING_REVIEW', 'REQUIRES_MANUAL_REVIEW', 'REJECTED', 'APPROVED', 'INDEXING', 'COMPLETED', name='documentstatus')
    document_status_enum.create(op.get_bind())


    op.alter_column('applications', 'status',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.Enum('NEW', 'SCREENING', 'CONTACTED', 'INTERVIEW', 'TECHNICAL_TEST', 'OFFER_SENT', 'HIRED', 'REJECTED', 'WITHDRAWN', 'GHOSTED', name='applicationstatus'),
               postgresql_using='status::applicationstatus',
               nullable=False)
               
    op.alter_column('documents', 'status',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('PENDING', 'UPLOADED', 'PROCESSING', 'DUPLICATE', 'FAILED', 'AWAITING_REVIEW', 'REQUIRES_MANUAL_REVIEW', 'REJECTED', 'APPROVED', 'INDEXING', 'COMPLETED', name='documentstatus'),
               postgresql_using='status::documentstatus',
               nullable=False)

    op.create_index(
        'ix_unique_content_hash',
        'documents',
        ['content_hash'],
        unique=True,
        postgresql_where=sa.text("status IN ('PROCESSING', 'AWAITING_REVIEW', 'APPROVED', 'INDEXING', 'COMPLETED')")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_unique_content_hash', table_name='documents')

    op.alter_column('documents', 'status',
               existing_type=sa.Enum('PENDING', 'UPLOADED', 'PROCESSING', 'DUPLICATE', 'FAILED', 'AWAITING_REVIEW', 'REQUIRES_MANUAL_REVIEW', 'REJECTED', 'APPROVED', 'INDEXING', 'COMPLETED', name='documentstatus'),
               type_=sa.VARCHAR(),
               nullable=True)
               
    op.alter_column('applications', 'status',
               existing_type=sa.Enum('NEW', 'SCREENING', 'CONTACTED', 'INTERVIEW', 'TECHNICAL_TEST', 'OFFER_SENT', 'HIRED', 'REJECTED', 'WITHDRAWN', 'GHOSTED', name='applicationstatus'),
               type_=sa.VARCHAR(length=50),
               nullable=True)

    application_status_enum = postgresql.ENUM('NEW', 'SCREENING', 'CONTACTED', 'INTERVIEW', 'TECHNICAL_TEST', 'OFFER_SENT', 'HIRED', 'REJECTED', 'WITHDRAWN', 'GHOSTED', name='applicationstatus')
    application_status_enum.drop(op.get_bind())

    document_status_enum = postgresql.ENUM('PENDING', 'UPLOADED', 'PROCESSING', 'DUPLICATE', 'FAILED', 'AWAITING_REVIEW', 'REQUIRES_MANUAL_REVIEW', 'REJECTED', 'APPROVED', 'INDEXING', 'COMPLETED', name='documentstatus')
    document_status_enum.drop(op.get_bind())

    op.create_index(
        'ix_unique_content_hash',
        'documents',
        ['content_hash'],
        unique=True,
        postgresql_where=sa.text("status IN ('PROCESSING', 'AWAITING_REVIEW', 'APPROVED', 'INDEXING', 'COMPLETED')")
    )
