"""product parser fields

Строка Product создаётся сразу по ссылке, до парсинга, поэтому
поля карточки становятся необязательными. Плюс статус INCOMPLETE
и поле last_error с причиной падения парсинга.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23

"""

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

# Поля, которые парсер может не найти на сайте: (имя, тип)
NULLABLE_COLUMNS = [
    ("name", sa.String(length=255)),
    ("article_ga", sa.String(length=100)),
    ("product_type", sa.String(length=255)),
    ("product_type_detailed", sa.String(length=255)),
    ("measure_type", sa.String(length=20)),
    ("measure_unit", sa.String(length=20)),
    ("price_rub", sa.Numeric(precision=10, scale=2)),
    ("brand", sa.String(length=255)),
]


def upgrade() -> None:
    for column, column_type in NULLABLE_COLUMNS:
        op.alter_column(
            "products",
            column,
            existing_type=column_type,
            nullable=True,
        )

    # SQLAlchemy хранит в enum имена членов (EMPTY, DONE...), а не значения
    op.execute("ALTER TYPE product_fill_status ADD VALUE IF NOT EXISTS 'INCOMPLETE'")

    op.add_column(
        "products",
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
            comment="Причина последнего падения парсинга",
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "last_error")

    # Из enum в PostgreSQL нельзя удалить значение — пересоздаём тип.
    # INCOMPLETE-товары при откате становятся FAILED.
    op.execute(
        "UPDATE products SET fill_status = 'FAILED' WHERE fill_status = 'INCOMPLETE'"
    )
    op.execute("ALTER TYPE product_fill_status RENAME TO product_fill_status_old")
    op.execute(
        "CREATE TYPE product_fill_status AS ENUM "
        "('EMPTY', 'IN_PROGRESS', 'DONE', 'FAILED')"
    )
    op.execute(
        "ALTER TABLE products ALTER COLUMN fill_status TYPE product_fill_status "
        "USING fill_status::text::product_fill_status"
    )
    op.execute("DROP TYPE product_fill_status_old")

    # Упадёт, если в таблице есть строки с пустыми полями —
    # перед откатом их нужно дозаполнить или удалить.
    for column, column_type in NULLABLE_COLUMNS:
        op.alter_column(
            "products",
            column,
            existing_type=column_type,
            nullable=False,
        )
