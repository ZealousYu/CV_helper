"""管理员：查看用户列表与完整只读数据。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models import Debrief, Experience, InterviewSession, KnowledgeItem, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminUserRow(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool
    created_at: Optional[datetime] = None
    experience_count: int = 0
    knowledge_count: int = 0
    debrief_count: int = 0
    session_count: int = 0


class AdminExperienceOut(BaseModel):
    id: str
    type: str
    company: str
    title: str
    role: str
    period: str
    summary: str
    metrics: str
    extra: str
    tags: List[Any]
    qa_tree: List[Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdminKnowledgeOut(BaseModel):
    id: str
    source_exp_id: Optional[str] = None
    source_node_id: Optional[str] = None
    question: str
    my_answer: str
    reference_answer: str
    tags: List[Any]
    note: str
    status: str
    created_at: Optional[datetime] = None


class AdminDebriefOut(BaseModel):
    id: str
    title: str
    company: str
    role: str
    interview_date: str
    transcript: str
    items: List[Any]
    created_at: Optional[datetime] = None


class AdminSessionOut(BaseModel):
    id: str
    target_role: str
    jd_text: str
    exp_ids: List[str]
    qa_tree: List[Any]
    channel: str
    created_at: Optional[datetime] = None


class AdminUserDetail(BaseModel):
    user: AdminUserRow
    experiences: List[AdminExperienceOut]
    knowledge: List[AdminKnowledgeOut]
    debriefs: List[AdminDebriefOut]
    sessions: List[AdminSessionOut]


def _user_row(db: Session, u: User) -> AdminUserRow:
    return AdminUserRow(
        id=u.id,
        username=u.username,
        display_name=u.display_name or u.username,
        is_admin=bool(u.is_admin),
        created_at=u.created_at,
        experience_count=db.query(Experience).filter(Experience.user_id == u.id).count(),
        knowledge_count=db.query(KnowledgeItem).filter(KnowledgeItem.user_id == u.id).count(),
        debrief_count=db.query(Debrief).filter(Debrief.user_id == u.id).count(),
        session_count=db.query(InterviewSession).filter(InterviewSession.user_id == u.id).count(),
    )


@router.get("/users", response_model=List[AdminUserRow])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del admin
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [_user_row(db, u) for u in users]


@router.get("/users/{user_id}/detail", response_model=AdminUserDetail)
def user_detail(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del admin
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")

    exps = (
        db.query(Experience)
        .filter(Experience.user_id == u.id)
        .order_by(Experience.created_at.desc())
        .all()
    )
    know = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.user_id == u.id)
        .order_by(KnowledgeItem.created_at.desc())
        .all()
    )
    debriefs = (
        db.query(Debrief)
        .filter(Debrief.user_id == u.id)
        .order_by(Debrief.created_at.desc())
        .all()
    )
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == u.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )

    return AdminUserDetail(
        user=_user_row(db, u),
        experiences=[
            AdminExperienceOut(
                id=e.id,
                type=e.type or "",
                company=e.company or "",
                title=e.title or "",
                role=e.role or "",
                period=e.period or "",
                summary=e.summary or "",
                metrics=e.metrics or "",
                extra=e.extra or "",
                tags=e.tags or [],
                qa_tree=e.qa_tree or [],
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in exps
        ],
        knowledge=[
            AdminKnowledgeOut(
                id=k.id,
                source_exp_id=k.source_exp_id,
                source_node_id=k.source_node_id,
                question=k.question or "",
                my_answer=k.my_answer or "",
                reference_answer=k.reference_answer or "",
                tags=k.tags or [],
                note=k.note or "",
                status=k.status or "",
                created_at=k.created_at,
            )
            for k in know
        ],
        debriefs=[
            AdminDebriefOut(
                id=d.id,
                title=d.title or "",
                company=d.company or "",
                role=d.role or "",
                interview_date=d.interview_date or "",
                transcript=d.transcript or "",
                items=d.items or [],
                created_at=d.created_at,
            )
            for d in debriefs
        ],
        sessions=[
            AdminSessionOut(
                id=s.id,
                target_role=s.target_role or "",
                jd_text=s.jd_text or "",
                exp_ids=s.exp_ids or [],
                qa_tree=s.qa_tree or [],
                channel=s.channel or "",
                created_at=s.created_at,
            )
            for s in sessions
        ],
    )


# 兼容旧前端摘要接口
@router.get("/users/{user_id}/summary", response_model=AdminUserDetail)
def user_summary(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_detail(user_id, admin, db)
