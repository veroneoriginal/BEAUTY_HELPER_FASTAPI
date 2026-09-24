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
