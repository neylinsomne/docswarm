"""Hashing/verificación de contraseñas con bcrypt.

Compatible con los hashes ``$2a$`` que genera pgcrypto en la semilla (V10), de
modo que los usuarios demo pueden autenticarse sin re-hashear.
"""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
