# apps/parser/exceptions.py

# Ошибки парсера.
# Снаружи ловят их, а не ошибки httpx / Playwright:
# так остальной код не зависит от того, чем парсер ходит в сеть.


class ParserError(Exception):
    """
    Общий родитель всех ошибок парсера.
    """


class NoAliveProxy(ParserError):
    """
    В пуле не осталось ни одного живого прокси.
    """


class SiteBlocked(ParserError):
    """
    Сайт не пустил через этот прокси: 403, обрыв соединения, таймаут.

    Прокси надо выкинуть (pool.mark_bad) и попробовать другой.
    """


class ProductNotFound(ParserError):
    """
    Товара по ссылке нет: сайт ответил 404.

    Другой прокси не поможет, ссылка плохая.
    """


class ParseError(ParserError):
    """
    Ответ пришёл, но разобрать его не получилось:
    не JSON или нет нужных полей.
    """
