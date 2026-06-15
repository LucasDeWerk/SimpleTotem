"""Criptografia simétrica para credenciais no SQLite (somente esta instalação)."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from core.config import CREDENTIAL_KEY_FILE

_fernet: Fernet | None = None


def _load_or_create_key() -> bytes:
    if CREDENTIAL_KEY_FILE.exists():
        return CREDENTIAL_KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    CREDENTIAL_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIAL_KEY_FILE.write_bytes(key)
    try:
        CREDENTIAL_KEY_FILE.chmod(0o600)
    except OSError:
        pass
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _get_fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Não foi possível descriptografar credencial") from exc
