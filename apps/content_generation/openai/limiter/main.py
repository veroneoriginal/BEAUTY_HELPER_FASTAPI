# apps/content_generation/openai/limiter/main.py

import json
import time as limiter_time
from typing import Optional

import logging

from apps.content_generation.openai.limiter.limiter_errors import (
    LimiterChooseAccountException,
    LimiterRedisUnavailableException,
)

logger = logging.getLogger(__name__)

from apps.content_generation.openai.limiter.utils import (
    calculate_time_to_next_minute,
    creating_dict_with_info_from_query,
    generate_key_with_time,
    get_connect_to_redis,
)
from apps.content_generation.openai.settings import (
    ACCOUNT_LIMITS,
    STORE_CURRENT_REQUEST,
)
from core.config import settings


class Limiter:
    """
    Класс для проверки лимитов и выбора аккаунта для осуществления генерации контента.
    Использует Redis для хранения счётчиков запросов в текущей минуте.
    """

    def __init__(self):

        # Устанавливаем соединение с Redis
        self.redis_client = get_connect_to_redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1,
            password=settings.REDIS_PASSWORD,
        )

        # Загружаем account_limits из settings
        self.accounts_limits = ACCOUNT_LIMITS

        # Загружаем пустой словарь для хранения данных в текущей минуте
        self.storing_current_request = STORE_CURRENT_REQUEST

    def checking_key_in_redis(
        self,
        key_with_time: str,
    ) -> dict:
        """
        Проверяет наличие ключа в Redis.

        :param key_with_time: ключ со временем запроса вида "openai_DD_MM_YY_HH_MM"
        :return: словарь с данными из Redis или пустой шаблон если ключ отсутствует
        """

        try:
            dict_from_redis_with_keytime = self.redis_client.get(key_with_time)
        except Exception as exc:
            logger.error("[LIMITER] Redis недоступен при чтении ключа %s: %s", key_with_time, exc)
            raise LimiterRedisUnavailableException(f"Redis недоступен: {exc}") from exc

        if dict_from_redis_with_keytime:
            return json.loads(dict_from_redis_with_keytime.decode())

        return self.storing_current_request.copy()

    def _saving_to_database(
        self,
        key_with_time: str,
        dict_from_redis_with_keytime: dict,
    ) -> None:
        """
        Сохраняет обновлённые данные в Redis с TTL до конца текущей минуты.

        :param key_with_time: ключ с текущим временем запроса
        :param dict_from_redis_with_keytime: обновлённый словарь для сохранения
        :return: None
        """

        try:
            self.redis_client.set(
                key_with_time,
                json.dumps(dict_from_redis_with_keytime),
                ex=calculate_time_to_next_minute(),
            )
        except Exception as exc:
            logger.error("[LIMITER] Redis недоступен при записи ключа %s: %s", key_with_time, exc)
            raise LimiterRedisUnavailableException(f"Redis недоступен: {exc}") from exc

    def _select_account_for_generating(
        self,
        data_with_info: dict,
        key_with_time: str,
        dict_from_redis_with_keytime: dict,
    ) -> Optional[str] | None:
        """
        Ищет аккаунт у которого не превышены лимиты RPM/TPM/IPM.
        Если аккаунт найден — обновляет счётчики и сохраняет в Redis.

        :param data_with_info: словарь с RPM, TPM, IPM текущего запроса
        :param key_with_time: ключ с текущим временем запроса
        :param dict_from_redis_with_keytime: текущие счётчики из Redis
        :return: название аккаунта если найден, иначе None
        """

        for account, limits in self.accounts_limits.items():
            # Проверяем лимиты для всех метрик (RPM, TPM, IPM)
            if all(
                dict_from_redis_with_keytime[account].get(metric, 0)
                + data_with_info[metric]
                <= limits[metric]
                for metric in data_with_info
                if data_with_info[metric] > 0  # Проверяем только релевантные метрики
            ):
                # Если лимиты не превышены, обновляем данные
                for metric in data_with_info:
                    dict_from_redis_with_keytime[account][metric] = (
                        dict_from_redis_with_keytime[account].get(metric, 0)
                        + data_with_info[metric]
                    )

                # Сохраняем обновленные данные в Redis
                self._saving_to_database(
                    key_with_time=key_with_time,
                    dict_from_redis_with_keytime=dict_from_redis_with_keytime,
                )

                # Возвращаем подходящий аккаунт
                return account

        # Если ни один аккаунт не подходит
        return None

    def _choose_account(
        self,
        query_details: dict,
        key_with_time: str,
        dict_from_redis_with_keytime: dict,
    ) -> str:
        """
        Запускает цикл поиска доступного аккаунта с ожиданием между попытками.
        Максимум 5 попыток, между ними ждёт до следующей минуты.

        :param query_details: словарь с содержимым запроса
        :param key_with_time: ключ со временем запроса
        :param dict_from_redis_with_keytime: текущие счётчики из Redis
        :return: название аккаунта для генерации
        :raises LimiterChooseAccountException: если аккаунт не найден за 5 попыток
        """

        # Счетчик попыток
        retries = 0

        # Общее количество попыток
        max_retries = 5

        # Формирование словаря с информацией из запроса
        data_with_info = creating_dict_with_info_from_query(query_details=query_details)

        while retries < max_retries:
            # Пытаемся выбрать аккаунт
            selected_account = self._select_account_for_generating(
                data_with_info=data_with_info,
                key_with_time=key_with_time,
                dict_from_redis_with_keytime=dict_from_redis_with_keytime,
            )

            # Если подходящий аккаунт найден, возвращаем его название
            if selected_account:
                return selected_account

            # Если ни один аккаунт не доступен, ждем
            limiter_time.sleep(calculate_time_to_next_minute())
            # и увеличиваем счетчик попыток
            retries += 1

        # Если после использования max_retries не удалось найти подходящий аккаунт
        raise LimiterChooseAccountException(
            f"Аккаунт для генерации {query_details['target']} контента не найден"
        )

    def main_get_account_name(
        self,
        query_details: dict,
    ) -> str:
        """
        Главный метод класса.
        Получает ключ текущей минуты, блокирует Redis,
        выбирает доступный аккаунт для генерации.

        :param query_details: словарь с содержимым запроса
        :return: название аккаунта для отправки запроса в OpenAI
        """

        # Получаем ключ со временем запроса
        key_with_time = generate_key_with_time()

        # блокируем процесс
        lock = self.redis_client.lock(f"{key_with_time}_lock", timeout=10)

        with lock:
            # Проверяем есть ли ключ в Redis
            dict_from_redis_with_keytime = self.checking_key_in_redis(
                key_with_time=key_with_time
            )

            # Выбор аккаунта, через который дальше будет отправляться запрос
            return self._choose_account(
                query_details=query_details,
                key_with_time=key_with_time,
                dict_from_redis_with_keytime=dict_from_redis_with_keytime,
            )
