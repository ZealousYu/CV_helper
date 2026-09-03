"""鉴权依赖：当前用户、管理员、按归属取资源。"""

from __future__ import annotations

from typing import Optional, Type, TypeVar

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

T = TypeVar("T")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(401, "请先登录")
    payload = decode_access_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(401, "登录已失效，请重新登录")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(401, "用户不存在，请重新登录")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "需要管理员权限")
    return user


def get_owned(db: Session, model: Type[T], resource_id: str, user: User, *, not_found: str = "资源不存在") -> T:
    row = (
        db.query(model)
        .filter(model.id == resource_id, model.user_id == user.id)  # type: ignore[attr-defined]
        .first()
    )
    if not row:
        raise HTTPException(404, not_found)
    return row
