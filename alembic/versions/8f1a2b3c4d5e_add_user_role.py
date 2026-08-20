"""Add role to users.

Revision ID: 8f1a2b3c4d5e
Revises: 6c623ec5737e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8f1a2b3c4d5e"
down_revision: Union[str, None] = "6c623ec5737e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the default user role to existing installations."""
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
    )


def downgrade() -> None:
    """Remove the user role column."""
    op.drop_column("users", "role")
