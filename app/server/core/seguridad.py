import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verificar_password(hash_guardado: str, password: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, password)
    except (VerificationError, InvalidHashError):
        return False


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # en la BD solo queda el hash: quien lea la tabla de sesiones no puede suplantar a nadie
    return hashlib.sha256(token.encode()).hexdigest()
