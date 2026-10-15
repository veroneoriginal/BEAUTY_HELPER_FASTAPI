# Тесты генерации подборки _create_selection_on_task без OpenAI, S3 и БД.
# TaskProcessing настоящий, подменён только запрос одного шага
# (run_task_step), цена и PDF: проверяем, что каждый шаг коммитится
# сразу, а повтор после сбоя не отправляет готовые шаги в OpenAI.

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.content_generation.openai.task_processing.main import TaskProcessing
from apps.selection.models import SelectionStatus, SelectionTaskType
from infrastructure.celery import tasks

# 25 ингредиентов → 3 шага по 10 + финальный шаг с выводом = 4 шага
INGREDIENTS = [f"ingredient_{i}" for i in range(25)]
ALL_STEPS = [1, 2, 3, 4]


@dataclass
class FakeProductData:
    """
    DTO продукта: задача делает из него dict через asdict.
    """

    title: str = "Крем"
    ingredients_list: list = field(default_factory=lambda: list(INGREDIENTS))


class FakeOpenAI:
    """
    Подмена TaskProcessing.run_task_step: вместо запроса в OpenAI
    запоминает номер шага и сохраняет фиктивный ответ.
    fail_on — номер шага, на котором «падает OpenAI».
    """

    def __init__(self, fail_on: int | None = None):
        self.fail_on = fail_on
        self.steps = []

    def __call__(self, processing: TaskProcessing, step_collection_data: dict):
        step_number = step_collection_data["Номер шага задачи"]
        if step_number == self.fail_on:
            raise RuntimeError(f"Task step {step_number} failed")
        self.steps.append(step_number)
        processing.save_step_result(
            step_number=step_number,
            request_details={"step": step_number},
            answer_openai_to_final={"result": f"answer {step_number}"},
        )


def _selection(**saved):
    """
    Подборка с продуктом; saved — поля, сохранённые прошлой попыткой.
    """
    product = SimpleNamespace(get_data_about_product=lambda: FakeProductData())
    fields = {
        "id": 1,
        "product": product,
        "task_type": SelectionTaskType.COMPOSITION_ANALYSIS,
        "request_details": None,
        "final_analysis": None,
        "analysis_last_step": None,
        "price": None,
        "pdf_url": None,
        "selection_status": SelectionStatus.PROCESS,
    }
    fields.update(saved)
    return SimpleNamespace(**fields)


def _saved(selection) -> dict:
    """
    То, что прошлая попытка успела закоммитить в подборку.
    """
    return {
        "request_details": selection.request_details,
        "final_analysis": selection.final_analysis,
        "analysis_last_step": selection.analysis_last_step,
    }


def _run(selection, openai, session=None, generate_pdf=None, redis_client=None):
    """
    Запускает генерацию с подменённым OpenAI, ценой и PDF.
    """
    session = session or MagicMock()
    generate_pdf = generate_pdf or (lambda **_: "https://s3/selection.pdf")
    with (
        # функция, а не сам объект: так Python передаст ей self — TaskProcessing
        patch.object(
            TaskProcessing,
            "run_task_step",
            lambda processing, step_collection_data: openai(
                processing, step_collection_data
            ),
        ),
        patch.object(tasks, "calculate_price_full_request", lambda **_: {"usd": 1}),
        patch.object(tasks, "convert_analysis_to_pdf_data", lambda **_: []),
        patch.object(tasks, "generate_selection_pdf", generate_pdf),
        patch.object(tasks, "redis_client", redis_client or MagicMock()),
    ):
        tasks._create_selection_on_task(session=session, selection=selection)


def _answers(selection) -> list[int]:
    return [
        answer["step_number"]
        for answer in tasks.convert_json_openai_to_list(selection.final_analysis)
    ]


def test_each_step_committed_before_pdf():
    """
    Все шаги идут в OpenAI, каждый коммитится сразу; цена — до PDF.
    """
    session = MagicMock()
    selection = _selection()
    openai = FakeOpenAI()

    def generate_pdf(**_):
        # к моменту PDF закоммичены 4 шага и цена
        assert session.commit.call_count == len(ALL_STEPS) + 1
        return "https://s3/selection.pdf"

    _run(selection, openai, session, generate_pdf)

    assert openai.steps == ALL_STEPS
    assert selection.analysis_last_step == 4
    assert _answers(selection) == ALL_STEPS
    assert selection.price == {"usd": 1}
    assert selection.selection_status == SelectionStatus.DONE


def test_retry_after_failed_step_continues_from_it():
    """
    Шаг 3 упал: шаги 1–2 сохранены. Повтор отправляет в OpenAI
    только 3 и 4, в анализе — все четыре по порядку.
    """
    first = _selection()
    with pytest.raises(RuntimeError, match="Task step 3"):
        _run(first, FakeOpenAI(fail_on=3))

    assert first.analysis_last_step == 2
    assert _answers(first) == [1, 2]
    assert first.price is None

    retried = _selection(**_saved(first))
    openai = FakeOpenAI()
    _run(retried, openai)

    assert openai.steps == [3, 4]
    assert retried.analysis_last_step == 4
    assert _answers(retried) == ALL_STEPS
    assert retried.selection_status == SelectionStatus.DONE


def test_retry_after_pdf_error_skips_openai():
    """
    Анализ готов, упал PDF. Повтор не зовёт OpenAI, сразу PDF.
    """
    first = _selection()
    with pytest.raises(RuntimeError, match="S3 упал"):
        _run(
            first,
            FakeOpenAI(),
            generate_pdf=MagicMock(side_effect=RuntimeError("S3 упал")),
        )
    assert first.analysis_last_step == 4

    retried = _selection(**_saved(first))
    openai = FakeOpenAI()
    _run(retried, openai)

    assert openai.steps == []
    assert _answers(retried) == ALL_STEPS
    assert retried.pdf_url == "https://s3/selection.pdf"


def test_lock_extended_after_each_step():
    """
    После каждого шага lock генерации продлевается на SELECTION_LOCK_SECONDS.
    """
    redis_client = MagicMock()
    _run(_selection(), FakeOpenAI(), redis_client=redis_client)

    assert redis_client.expire.call_count == len(ALL_STEPS)
    redis_client.expire.assert_called_with(
        "selection_lock:1", tasks.SELECTION_LOCK_SECONDS
    )
