"""密码哈希与 JWT。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), (password_hash or "").encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, username: str, *, is_admin: bool = False) -> str:
    days = max(1, int(settings.jwt_expire_days or 30))
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "is_admin": bool(is_admin),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
