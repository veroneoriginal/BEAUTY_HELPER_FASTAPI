"""rename ga fields

link_ga → product_link, article_ga → article: парсер умеет
несколько сайтов (паттерн «Стратегия»), поля больше не про ЗЯ.
Данные не копируются — колонки только переименовываются.

Revision ID: 229c40bccd34
Revises: c3d4e5f6a7b8
Create Date: 2026-10-12

"""

import sqlalchemy as sa
from alembic import op

revision = "229c40bccd34"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

# Уникальное ограничение создано в initial без имени —
# Postgres назвал его сам: <таблица>_<колонка>_key
OLD_UNIQUE = "products_link_ga_key"
NEW_UNIQUE = "products_product_link_key"


def upgrade() -> None:
    op.alter_column(
        "products",
        "link_ga",
        new_column_name="product_link",
        existing_type=sa.String(length=2083),
        existing_nullable=False,
        comment="Уникальная ссылка на карточку товара на сайте",
        existing_comment="Уникальная ссылка на карточку товара в Золотом Яблоке",
    )
    op.alter_column(
        "products",
        "article_ga",
        new_column_name="article",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        comment="Артикул товара на сайте",
        existing_comment="Артикул в Золотом Яблоке",
    )
    op.execute(f"ALTER TABLE products RENAME CONSTRAINT {OLD_UNIQUE} TO {NEW_UNIQUE}")


def downgrade() -> None:
    op.execute(f"ALTER TABLE products RENAME CONSTRAINT {NEW_UNIQUE} TO {OLD_UNIQUE}")
    op.alter_column(
        "products",
        "article",
        new_column_name="article_ga",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        comment="Артикул в Золотом Яблоке",
        existing_comment="Артикул товара на сайте",
    )
    op.alter_column(
        "products",
        "product_link",
        new_column_name="link_ga",
        existing_type=sa.String(length=2083),
        existing_nullable=False,
        comment="Уникальная ссылка на карточку товара в Золотом Яблоке",
        existing_comment="Уникальная ссылка на карточку товара на сайте",
    )
