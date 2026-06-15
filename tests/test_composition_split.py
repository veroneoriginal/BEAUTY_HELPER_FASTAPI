# Тест разбивки состава на шаги по 10 ингредиентов (анализ состава).
# Мокаем run_all_task_steps — реальные запросы в OpenAI не выполняются,
# проверяется только нарезка состава на шаги.
#
# Поэлементный разбор делится на шаги по 10 ингредиентов, а итоговый вывод
# вынесен в отдельный финальный шаг с пустым составом (он помечен последним).

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


def test_25_ingredients_split_into_3_element_steps():
    """25 ингредиентов → 3 элементных шага размером 10/10/5 (+ шаг вывода)."""
    steps = split_into_steps(25)
    element_steps = steps[:-1]
    sizes = [len(s["Элементы состава для шага задачи"]) for s in element_steps]
    assert sizes == [10, 10, 5]


def test_conclusion_step_appended_last():
    """После элементных шагов добавляется отдельный шаг вывода с пустым составом."""
    steps = split_into_steps(25)
    conclusion = steps[-1]
    assert conclusion["Элементы состава для шага задачи"] == []
    assert conclusion["Шаг задачи последний или нет"] is True


def test_step_numbers_and_offsets():
    """Номера элементных шагов идут с 1, смещения нумерации — 1, 11, 21."""
    steps = split_into_steps(25)
    element_steps = steps[:-1]
    assert [s["Номер шага задачи"] for s in element_steps] == [1, 2, 3]
    assert [s["Смещение для нумерации"] for s in element_steps] == [1, 11, 21]


def test_only_conclusion_step_flagged_last():
    """Флаг «последний шаг» стоит только у шага вывода, не у элементных."""
    steps = split_into_steps(25)
    assert [s["Шаг задачи последний или нет"] for s in steps] == [
        False,
        False,
        False,
        True,
    ]


def test_step_contains_correct_ingredient_slice():
    """Каждый элементный шаг содержит свой срез ингредиентов исходного списка."""
    steps = split_into_steps(25)
    assert steps[0]["Элементы состава для шага задачи"] == list(range(0, 10))
    assert steps[1]["Элементы состава для шага задачи"] == list(range(10, 20))
    assert steps[2]["Элементы состава для шага задачи"] == list(range(20, 25))


def test_exactly_10_is_single_element_step_plus_conclusion():
    """Ровно 10 ингредиентов → 1 элементный шаг + отдельный шаг вывода."""
    steps = split_into_steps(10)
    assert len(steps) == 2
    assert steps[0]["Шаг задачи последний или нет"] is False
    assert steps[1]["Шаг задачи последний или нет"] is True


def test_divisible_count_no_trailing_element_step():
    """20 ингредиентов → ровно 2 элементных шага по 10 (+ шаг вывода)."""
    steps = split_into_steps(20)
    element_steps = steps[:-1]
    assert [len(s["Элементы состава для шага задачи"]) for s in element_steps] == [
        10,
        10,
    ]
