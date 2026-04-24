# core/exceptions.py
"""
Кастомные исключения бизнес-логики.
Каждый тип ошибки — отдельный класс.
Роуты ловят конкретные исключения и возвращают нужный HTTP-статус.
"""


class AppError(Exception):
    """Базовое исключение приложения."""
    pass


class UserAlreadyExistsError(AppError):
    """Email уже зарегистрирован."""
    pass


class InvalidCredentialsError(AppError):
    """Неверный email или пароль."""
    pass


class EmailNotConfirmedError(AppError):
    """Email не подтверждён."""
    pass


class UserBannedError(AppError):
    """Аккаунт заблокирован."""
    pass


class InvalidTokenError(AppError):
    """Токен невалидный, просроченный или неверного типа."""
    pass


class UserNotFoundError(AppError):
    """Пользователь не найден."""
    pass


class TokenRevokedError(AppError):
    """Токен отозван (в blacklist)."""
    pass
