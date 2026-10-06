"""selection status parsing

Подборка создаётся вместе с Product до парсинга и ждёт его в статусе PARSING.
Жизненный цикл: PARSING → QUEUE → PROCESS → DONE (или FAILED).

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-10-05

"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy хранит в enum имена членов (QUEUE, DONE...), а не значения
    op.execute("ALTER TYPE selection_status ADD VALUE IF NOT EXISTS 'PARSING'")


def downgrade() -> None:
    # Из enum в PostgreSQL нельзя удалить значение — пересоздаём тип.
    # PARSING-подборки при откате становятся FAILED.
    op.execute(
        "UPDATE selections SET selection_status = 'FAILED' "
        "WHERE selection_status = 'PARSING'"
    )
    op.execute("ALTER TYPE selection_status RENAME TO selection_status_old")
    op.execute(
        "CREATE TYPE selection_status AS ENUM ('QUEUE', 'PROCESS', 'DONE', 'FAILED')"
    )
    op.execute(
        "ALTER TABLE selections ALTER COLUMN selection_status TYPE selection_status "
        "USING selection_status::text::selection_status"
    )
    op.execute("DROP TYPE selection_status_old")
