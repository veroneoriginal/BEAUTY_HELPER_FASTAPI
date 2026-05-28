# scripts/create_tables.py
# Создаёт все таблицы через синхронный движок.
# Запускается из entrypoint.sh до import_products.py.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Импортируем все модели, чтобы Base.metadata знал о них
from apps.balance.models import BalanceOperation, UserBalance  # noqa: F401
from apps.package.models import Package, UserPackage  # noqa: F401
from apps.products.models import Product  # noqa: F401
from apps.selection.models import Selection, selection_users  # noqa: F401
from apps.users.models import User  # noqa: F401
from apps.waiting.models import Waiting  # noqa: F401
from core.database import Base, sync_engine

Base.metadata.create_all(sync_engine)
print("✅ Tables created.")
