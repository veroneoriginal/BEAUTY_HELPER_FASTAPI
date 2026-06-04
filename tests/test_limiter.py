# Тест выбора аккаунта лимитером по RPM/TPM/IPM — без Redis.
# Limiter создаём через __new__ (минуя __init__ с подключением к Redis),
# а запись счётчиков (_saving_to_database) мокаем.

from unittest.mock import MagicMock

from apps.content_generation.openai.limiter.main import Limiter
from apps.content_generation.openai.settings import (
    ACCOUNT_LIMITS,
    OPENAI_ACCOUNT_1,
    OPENAI_ACCOUNT_2,
)

# Лимит RPM у обоих аккаунтов (см. settings.ACCOUNT_LIMITS)
RPM_LIMIT = ACCOUNT_LIMITS[OPENAI_ACCOUNT_1]["RPM"]


def make_limiter():
    """Limiter без подключения к Redis: создаём через __new__, запись в Redis мокаем."""
    lim = Limiter.__new__(Limiter)
    lim.accounts_limits = ACCOUNT_LIMITS
    lim._saving_to_database = MagicMock()
    return lim


def counters(a1_rpm=0, a2_rpm=0):
    """Шаблон счётчиков из Redis с заданным текущим RPM по каждому аккаунту."""
    return {
        OPENAI_ACCOUNT_1: {"RPM": a1_rpm, "TPM": 0, "IPM": 0},
        OPENAI_ACCOUNT_2: {"RPM": a2_rpm, "TPM": 0, "IPM": 0},
    }


def test_picks_first_account_when_free():
    """Оба аккаунта свободны — выбирается первый, его счётчики растут на запрос."""
    lim = make_limiter()
    counts = counters()
    request = {"RPM": 1, "TPM": 100, "IPM": 0}

    account = lim._select_account_for_generating(
        data_with_info=request,
        key_with_time="k",
        dict_from_redis_with_keytime=counts,
    )

    assert account == OPENAI_ACCOUNT_1
    # счётчики первого аккаунта обновились на величину запроса
    assert counts[OPENAI_ACCOUNT_1]["RPM"] == 1
    assert counts[OPENAI_ACCOUNT_1]["TPM"] == 100
    lim._saving_to_database.assert_called_once()


def test_falls_back_to_second_when_first_full():
    """Первый аккаунт на пределе RPM — выбирается второй."""
    lim = make_limiter()
    counts = counters(a1_rpm=RPM_LIMIT)  # первый аккаунт на пределе RPM
    request = {"RPM": 1, "TPM": 100, "IPM": 0}

    account = lim._select_account_for_generating(
        data_with_info=request,
        key_with_time="k",
        dict_from_redis_with_keytime=counts,
    )

    assert account == OPENAI_ACCOUNT_2


def test_returns_none_when_all_full():
    """Оба аккаунта исчерпали лимит — возвращается None, запись в Redis не делается."""
    lim = make_limiter()
    counts = counters(a1_rpm=RPM_LIMIT, a2_rpm=RPM_LIMIT)
    request = {"RPM": 1, "TPM": 100, "IPM": 0}

    account = lim._select_account_for_generating(
        data_with_info=request,
        key_with_time="k",
        dict_from_redis_with_keytime=counts,
    )

    assert account is None
    lim._saving_to_database.assert_not_called()
