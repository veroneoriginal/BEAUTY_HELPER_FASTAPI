# apps/orchestrator/encoders.py

import decimal
import json
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
    """
    Кастомный JSON-энкодер.
    Преобразует decimal.Decimal → float для корректной сериализации
    данных содержащих цены и стоимости запросов к OpenAI.
    """

    def default(self, o: Any) -> Any:
        """
        Переопределяет сериализацию нестандартных объектов.

        :param o: объект который не может быть сериализован стандартным способом
        :return: сериализуемый объект
        """
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)
