# apps/content_generation/openai/task_processing/main.py
import logging
import math
from copy import deepcopy

from apps.content_generation.openai.json_constructor.main import (
    get_json_scheme,
)
from apps.content_generation.openai.main_openai import (
    OpenAIClient,
)
from apps.content_generation.openai.prompt_constructor.main import (
    get_prompts,
)
from apps.content_generation.openai.task_processing.utils import (
    create_request_details,
    formation_context,
)
from apps.selection.models import (
    Selection,
    SelectionTaskType,
)

logger = logging.getLogger(__name__)

class TaskProcessing:
    """
    Класс для выполнения задач по разборам средств
    """

    def __init__(
            self,
            collection_data: dict,
            selection: Selection,
            task_type: SelectionTaskType,
    ):
        """
        :param collection_data: инфо из dataclass-а продукта
        :param selection: Объект Selection (подборки), связанный с текущей задачей
        :param task_type: Тип задачи, по которой создается подборка
        """
        self.collection_data = collection_data
        self.selection = selection
        self.task_type = task_type
        self.request_data = []  # здесь будут все request_details
        self.response_data = []  # здесь будут ответы от OPENAI

        self.method_for_task_code = {
            # код задачи - Подробный анализ каждого элемента состава
            SelectionTaskType.COMPOSITION_ANALYSIS: self.detailed_analysis_composition,
        }

    def detailed_analysis_composition(self):
        """
        Выполнение задачи 'Подробный анализ каждого элемента состава'
        """

        # Максимальное количество элементов в составе средства для одного шага в задаче
        MAX_ELEMENTS_IN_STEP = 10

        # Получаем список самих ингредиентов состава
        full_ingredients_list = self.collection_data['ingredients_list']

        # Получаем количество элементов состава
        total_count = len(self.collection_data['ingredients_list'])

        # Вычисляем, сколько шагов нужно, чтобы обработать весь состав
        task_steps_count = math.ceil(total_count / MAX_ELEMENTS_IN_STEP)

        # Список, в который мы будем добавлять все шаги задачи
        task_steps = []

        # Проходим по каждому шагу (шаг = подмножество состава)
        for step_number in range(task_steps_count):
            # Начальный индекс для среза списка ингредиентов
            start_index = step_number * MAX_ELEMENTS_IN_STEP

            # Конечный индекс для среза списка ингредиентов
            end_index = start_index + MAX_ELEMENTS_IN_STEP

            # Получаем срез ингредиентов, относящийся к текущему шагу
            step_ingredients = full_ingredients_list[start_index:end_index]

            # Копируем оригинальный словарь collection_data для текущего шага
            step_data = deepcopy(self.collection_data)

            # Добавляем в словарь ингредиенты для текущего шага
            step_data['Элементы состава для шага задачи'] = step_ingredients

            # Добавляем номер текущего шага (начиная с 1)
            step_data['Номер шага задачи'] = step_number + 1

            # Добавляем булевый флаг, последний ли это шаг
            step_data['Шаг задачи последний или нет'] = step_number == task_steps_count - 1

            # Добавляем смещение для нумерации элементов
            step_data['Смещение для нумерации'] = start_index + 1

            # Добавляем подготовленный шаг в общий список всех шагов
            task_steps.append(step_data)

        # Запускаем выполнение всех шагов задачи
        self.run_all_task_steps(task_steps)

    def run_task_step(
            self,
            step_collection_data: dict,
    ) -> None:
        """
        Выполнение одного шага задачи.

        В один шаг входит:
        1) Подготовка json-схемы и промпта
        2) Отправка запроса в OpenAI
        3) Сохранение результата в базу данных

        :param step_collection_data: словарь необходимый для генерации одного шага задачи
        :return: None
        """

        # полный словарь включая шаг из средств внутри step_collection_data
        # apps/content_generation/openai/task_processing/example_data.py

        task_step_number = step_collection_data['Номер шага задачи']

        # 1. # Определяю json-схему
        json_scheme = get_json_scheme(
            data_collection=step_collection_data,
            task_type=self.task_type,
        )

        # 2. Генерация промпта
        dict_with_prompts = get_prompts(
            data_collection=step_collection_data,
            task_type=self.task_type,
        )

        # 3. Формирование context-а для отправки в OpenAi
        context_for_request = formation_context(dict_with_prompts=dict_with_prompts)

        # 4. Формирование словаря с информацией о запросе для его передачи в OPENAI
        request_details = create_request_details(
            json_scheme=json_scheme,
            context=context_for_request,
        )

        # 5. Передаю контекст и отправляю запрос в OpenAI
        openai_client = OpenAIClient()
        answer_openai = openai_client.main_request(request_details=request_details)

        # Проверяем, что вернулось от OpeanAI,
        # чтобы в случае ошибки первого шага, код не шел дальше
        if answer_openai.get("error") is True:
            raise RuntimeError(
                f"Task step {task_step_number} failed: {answer_openai.get('message')}"
            )

        # 6. Сохраняем ответ во временную переменную (список)
        self.save_step_result(
            step_number=task_step_number,
            request_details=request_details,
            answer_openai_to_final=answer_openai,
        )

    def save_step_result(
            self,
            step_number: int,
            request_details: dict,
            answer_openai_to_final: dict,
    ) -> None:
        """
        Метод для сохранения данных одного шага в два отдельных списка:
        - request_details (все запросы в OpenAI)
        - answer_openai_to_final (все ответы от OpenAI)
        """
        self.request_data.append({
            "step_number": step_number,
            "request_details": request_details,
        })

        self.response_data.append({
            "step_number": step_number,
            "answer_openai_to_final": answer_openai_to_final,
        })

    def run_all_task_steps(
            self,
            all_task_steps: list,
    ) -> None:
        """
        Выполнение всех шагов задачи.

        :param all_task_steps: Список со всеми шагами задачи
        :return: None
        """

        for step_data in all_task_steps:
            self.run_task_step(step_collection_data=step_data)

    def run_task_processing(
            self,
    ) -> None:
        """
        Главный метод класса, внутри которого определяется с какой
        задачей работаем и запускаем процесс выполнения этой задачи.
        """

        self.method_for_task_code[self.task_type]()
