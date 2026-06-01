"""balance check constraints

Revision ID: a1b2c3d4e5f6
Revises: 08de60d68ca7
Create Date: 2026-06-02

"""
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "08de60d68ca7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_user_balances_spins_non_negative",
        "user_balances",
        "spins >= 0",
    )
    op.create_check_constraint(
        "ck_user_balances_reserved_spins_non_negative",
        "user_balances",
        "reserved_spins >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_balances_spins_non_negative",
        "user_balances",
        type_="check",
    )
    op.drop_constraint(
        "ck_user_balances_reserved_spins_non_negative",
        "user_balances",
        type_="check",
    )