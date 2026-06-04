# Тесты безопасности: валидация пароля, хеширование bcrypt, JWT.

import pytest
from pydantic import ValidationError

from apps.auth.schemas import RegisterRequest
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordValidation:
    """Валидация пароля в схеме регистрации (длина и лимит bcrypt в 72 байта)."""

    def test_valid_password_ok(self):
        """Нормальный пароль проходит валидацию без изменений."""
        req = RegisterRequest(email="user@example.com", password="password123")
        assert req.password == "password123"

    def test_too_short_rejected(self):
        """Пароль короче 8 символов отклоняется."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="short")

    def test_over_72_bytes_ascii_rejected(self):
        """73 ascii-символа = 73 байта > лимита bcrypt — отклоняется."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="a" * 73)

    def test_cyrillic_over_72_bytes_rejected(self):
        """40 символов кириллицы = 80 байт: ловится проверкой по байтам, а не символам."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="я" * 40)

    def test_exactly_72_bytes_ok(self):
        """Ровно 72 байта — граница допустимого, проходит."""
        req = RegisterRequest(email="user@example.com", password="a" * 72)
        assert len(req.password.encode("utf-8")) == 72


class TestPasswordHashing:
    """Хеширование bcrypt: хеш отличается от пароля и корректно проверяется."""

    def test_hash_then_verify_true(self):
        """Хеш не равен паролю, а verify_password подтверждает верный пароль."""
        hashed = hash_password("password123")
        assert hashed != "password123"
        assert verify_password("password123", hashed) is True

    def test_verify_wrong_password_false(self):
        """Неверный пароль не проходит проверку против хеша."""
        hashed = hash_password("password123")
        assert verify_password("wrong-password", hashed) is False


class TestJWT:
    """Выпуск и проверка JWT-токенов (тип токена, целостность подписи)."""

    def test_access_token_roundtrip(self):
        """Access-токен декодируется обратно с sub и type='access'."""
        token = create_access_token(data={"sub": "42"})
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_refresh_token_marked_as_refresh(self):
        """Refresh-токен помечается type='refresh'."""
        token = create_refresh_token(data={"sub": "42"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_tampered_token_rejected(self):
        """Изменённый (подделанный) токен не проходит декодирование."""
        token = create_access_token(data={"sub": "42"})
        with pytest.raises(Exception):
            decode_token(token + "tampered")
