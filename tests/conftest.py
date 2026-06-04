# Общая настройка тестов.
# Импортируем все модели, чтобы они зарегистрировались в mapper registry
# (как это делает main.py). Иначе relationship по строковым именам, например
# UserBalance.user -> "User", не резолвятся и инициализация маппера падает.

import apps.balance.models  # noqa: F401
import apps.package.models  # noqa: F401
import apps.products.models  # noqa: F401
import apps.selection.models  # noqa: F401
import apps.users.models  # noqa: F401
import apps.waiting.models  # noqa: F401
