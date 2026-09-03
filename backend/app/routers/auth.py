"""注册 / 登录 / 当前用户。"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Debrief, Experience, InterviewSession, KnowledgeItem, User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fff]{2,32}$")


class AuthIn(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = Field("", max_length=64)


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        username=u.username,
        display_name=u.display_name or u.username,
        is_admin=bool(u.is_admin),
        created_at=u.created_at,
    )


def _normalize_username(raw: str) -> str:
    return (raw or "").strip()


def _validate_credentials(username: str, password: str) -> str:
    name = _normalize_username(username)
    if not _USERNAME_RE.match(name):
        raise HTTPException(400, "用户名需 2–32 位，仅字母数字下划线或中文")
    if not password or len(password) < 4:
        raise HTTPException(400, "密码至少 4 位")
    return name


def assign_orphan_data(db: Session, user_id: str) -> None:
    """把尚未归属的业务数据挂到指定用户（迁移用）。"""
    for model in (Experience, KnowledgeItem, Debrief, InterviewSession):
        db.query(model).filter(model.user_id.is_(None)).update(  # type: ignore[attr-defined]
            {model.user_id: user_id},  # type: ignore[attr-defined]
            synchronize_session=False,
        )


def ensure_admin_from_env(db: Session) -> Optional[User]:
    """若配置了 ADMIN_USERNAME / ADMIN_PASSWORD，确保管理员存在并接收遗留数据。"""
    from app.config import settings

    username = (settings.admin_username or "").strip()
    password = settings.admin_password or ""
    if not username:
        return None
    if not password:
        # 有用户名无密码：只查找已有管理员，不强制创建
        row = db.query(User).filter(User.username == username).first()
        if row:
            if not row.is_admin:
                row.is_admin = True
                db.commit()
            assign_orphan_data(db, row.id)
            db.commit()
        return row

    row = db.query(User).filter(User.username == username).first()
    if not row:
        row = User(
            id=f"u_{uuid.uuid4().hex[:12]}",
            username=username,
            password_hash=hash_password(password),
            display_name=username,
            is_admin=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    else:
        if not row.is_admin:
            row.is_admin = True
        # 不在每次启动覆盖密码，避免无意改密；仅保证管理员标记
        db.commit()
    assign_orphan_data(db, row.id)
    db.commit()
    return row


@router.post("/register", response_model=TokenOut)
def register(body: AuthIn, db: Session = Depends(get_db)):
    username = _validate_credentials(body.username, body.password)
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "用户名已被占用")

    # 库里还没有任何用户 / 还没有管理员 → 首位注册者为管理员，并接收遗留数据
    make_admin = db.query(User).count() == 0 or db.query(User).filter(User.is_admin.is_(True)).count() == 0

    user = User(
        id=f"u_{uuid.uuid4().hex[:12]}",
        username=username,
        password_hash=hash_password(body.password),
        display_name=(body.display_name or "").strip() or username,
        is_admin=make_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if make_admin:
        assign_orphan_data(db, user.id)
        db.commit()

    token = create_access_token(user.id, user.username, is_admin=user.is_admin)
    return TokenOut(access_token=token, user=_user_out(user))


@router.post("/login", response_model=TokenOut)
def login(body: AuthIn, db: Session = Depends(get_db)):
    username = _normalize_username(body.username)
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码不正确")
    token = create_access_token(user.id, user.username, is_admin=user.is_admin)
    return TokenOut(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
