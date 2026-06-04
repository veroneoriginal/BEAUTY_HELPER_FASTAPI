# Тест разбивки состава на шаги по 10 ингредиентов (анализ состава).
# Мокаем run_all_task_steps — реальные запросы в OpenAI не выполняются,
# проверяется только нарезка состава на шаги.

from unittest.mock import MagicMock

from apps.content_generation.openai.task_processing.main import TaskProcessing
from apps.selection.models import SelectionTaskType


def split_into_steps(ingredient_count):
    """Возвращает список шагов, на которые TaskProcessing делит состав заданного размера."""
    tp = TaskProcessing(
        collection_data={"ingredients_list": list(range(ingredient_count))},
        task_type=SelectionTaskType.COMPOSITION_ANALYSIS,
    )
    tp.run_all_task_steps = MagicMock()
    tp.detailed_analysis_composition()
    return tp.run_all_task_steps.call_args.args[0]


def test_25_ingredients_split_into_3_steps():
    """25 ингредиентов → 3 шага размером 10/10/5."""
    steps = split_into_steps(25)
    sizes = [len(s["Элементы состава для шага задачи"]) for s in steps]
    assert sizes == [10, 10, 5]


def test_step_numbers_and_offsets():
    """Номера шагов идут с 1, смещения нумерации — 1, 11, 21."""
    steps = split_into_steps(25)
    assert [s["Номер шага задачи"] for s in steps] == [1, 2, 3]
    assert [s["Смещение для нумерации"] for s in steps] == [1, 11, 21]


def test_only_last_step_flagged():
    """Флаг «последний шаг» стоит только у последнего шага."""
    steps = split_into_steps(25)
    assert [s["Шаг задачи последний или нет"] for s in steps] == [False, False, True]


def test_step_contains_correct_ingredient_slice():
    """Каждый шаг содержит свой срез ингредиентов исходного списка."""
    steps = split_into_steps(25)
    assert steps[0]["Элементы состава для шага задачи"] == list(range(0, 10))
    assert steps[1]["Элементы состава для шага задачи"] == list(range(10, 20))
    assert steps[2]["Элементы состава для шага задачи"] == list(range(20, 25))


def test_exactly_10_is_single_step():
    """Ровно 10 ингредиентов укладываются в один шаг, помеченный последним."""
    steps = split_into_steps(10)
    assert len(steps) == 1
    assert steps[0]["Шаг задачи последний или нет"] is True


def test_divisible_count_no_trailing_step():
    """20 ингредиентов → ровно 2 шага по 10, без «хвостового» шага."""
    steps = split_into_steps(20)
    assert [len(s["Элементы состава для шага задачи"]) for s in steps] == [10, 10]
