"""add reservation status and idempotency constraint

Revision ID: 1e59ffcb49e3
Revises: 0001
Create Date: 2026-10-11 18:08:42.187577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e59ffcb49e3'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="confirmed",
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_reservations_user_request",
        "reservations",
        ["user_id", "request_id"],
    )
    op.create_index(
        "ix_reservations_slot_status",
        "reservations",
        ["slot_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reservations_slot_status",
        table_name="reservations",
    )
    op.drop_constraint(
        "uq_reservations_user_request",
        "reservations",
        type_="unique",
    )
    op.drop_column("reservations", "status")
