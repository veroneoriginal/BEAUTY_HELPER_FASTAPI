"""selection analysis_last_step

Номер последнего готового шага анализа OpenAI: ответы сохраняются
после каждого шага, и повтор задачи продолжает со следующего,
а не платит заново за уже готовые.

Revision ID: d4e5f6a7b8c9
Revises: 229c40bccd34
Create Date: 2026-10-15

"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "229c40bccd34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "selections",
        sa.Column(
            "analysis_last_step",
            sa.Integer(),
            nullable=True,
            comment="Номер последнего готового шага анализа OpenAI",
        ),
    )


def downgrade() -> None:
    op.drop_column("selections", "analysis_last_step")
