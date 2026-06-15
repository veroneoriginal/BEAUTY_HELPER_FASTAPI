# apps/content_generation/openai/json_constructor/json_creator.py

from apps.selection.models import (
    SelectionTaskType,
)


class JsonCreator:
    """
    Класс для динамического создания JSON-схемы для structured output OpenAI.
    Схема формируется в зависимости от типа задачи и состава продукта.

    :param data_collection: словарь с данными текущего шага подборки
    :param product_categories: словарь с категориями продуктов
    """

    def __init__(
        self,
        data_collection: dict,
        product_categories: dict,
    ):
        self.data_collection = data_collection
        self.product_categories = product_categories

        self.method_for_task_code = {
            # Подробный анализ каждого элемента состава
            SelectionTaskType.COMPOSITION_ANALYSIS: self.create_js_detailed_analysis_each_element_of_composition,
            # "Общий анализ элементов состава": self.create_json_scheme_detailed_analysis_composition,
            # "Аналог": self.create_json_scheme_for_analogue_product,
        }

    def get_json_scheme_for_current_task(self):
        """
        Определяет и вызывает метод создания JSON-схемы в зависимости от типа задачи.
        :return: JSON-схема для текущей задачи
        """

        task = self.data_collection["task_type"]
        return self.method_for_task_code[task]()

    def create_js_detailed_analysis_each_element_of_composition(self) -> dict:
        """
        Динамически формирует JSON-схему для задачи COMPOSITION_ANALYSIS.
        Для каждого ингредиента создаёт объект с полями:
        element_title, what_is_element_used_for, element_danger_text,
        is_element_danger, element_stop_in_country.
        Для последнего шага добавляет поле result с итоговым выводом.

        :return: JSON-схема для отправки в OpenAI
        """

        schema = {
            "name": "detailed_analysis_composition",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        }

        result = {
            "type": "string",
            "description": (
                "Итоговый вывод по средству на основе ПОЛНОГО состава, "
                "2-4 связных предложения. Дай чёткую оценку: безопасно ли "
                "средство в целом и кому оно подходит или не подходит, есть ли "
                "опасные, аллергенные или запрещённые компоненты и какие "
                "предостережения учесть. Обязательно заполни поле связным "
                "текстом, не оставляй его пустым."
            ),
        }

        # Получаем название продукта
        name_product = self.data_collection["name"]

        # Получаем артикул
        article_ga = self.data_collection["article_ga"]

        product = {
            "origin_product": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": name_product,
                    },
                    "article": {
                        "type": "string",
                        "description": article_ga,
                    },
                },
                "required": ["title", "article"],
                "additionalProperties": False,
            },
        }

        # Добавляем продукт в свойства схемы
        schema["schema"]["properties"].update(product)

        # Добавляем продукт в список `required`
        schema["schema"]["required"].extend(product.keys())

        # Получаем элементы, входящие в состав средства
        ingredients = self.data_collection["Элементы состава для шага задачи"]

        # Идем по списку элементов состава и добавляем в словарь
        elements = {}
        for element in ingredients:
            # Формирую ключи для средств
            element_key = f"element_{element.replace(' ', '_')}"

            elements[element_key] = {
                "type": "object",
                "properties": {
                    "element_title": {
                        "type": "string",
                        "description": f"Название элемента - {element}",
                    },
                    "what_is_element_used_for": {
                        "type": "string",
                        "description": f"Что такое элемент {element} и для чего он "
                        f"используется в составе средства.",
                    },
                    "element_danger_text": {
                        "type": "string",
                        "description": f"Является ли элемент {element} канцерогеном или "
                        f"опасным веществом? Если элемент опасен,"
                        f" то скажи, чем конкретно.",
                    },
                    "is_element_danger": {
                        "type": "boolean",
                        "description": f"Если элемент {element} вызывает аллергию,"
                        f" является канцерогеном или опасен по другой причине -"
                        f" поставь True, иначе - False",
                    },
                    "element_stop_in_country": {
                        "type": "string",
                        "description": f"Если элемент {element} запрещён в каких-то "
                        f"странах (или регулируется) - сообщи "
                        f"об этом, если нет - просто напиши 'Не запрещён.' ",
                    },
                },
                "required": [
                    "element_title",
                    "what_is_element_used_for",
                    "element_danger_text",
                    "is_element_danger",
                    "element_stop_in_country",
                ],
                "additionalProperties": False,
            }

        # Добавляем элементы в свойства схемы
        schema["schema"]["properties"].update(elements)

        # Добавляем продукты в список `required`
        schema["schema"]["required"].extend(elements.keys())

        # Добавляем result ТОЛЬКО если шаг последний
        if self.data_collection.get("Шаг задачи последний или нет"):
            schema["schema"]["properties"]["result"] = result
            schema["schema"]["required"].append("result")

        return schema
