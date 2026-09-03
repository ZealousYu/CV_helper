from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned
from app.models import Debrief, User
from app.schemas import DebriefAnalyzeIn, DebriefCreate, DebriefOut, DebriefUpdate
from app.services.llm import get_llm

router = APIRouter(prefix="/api/debriefs", tags=["debriefs"])


def _to_out(row: Debrief) -> DebriefOut:
    return DebriefOut(
        id=row.id,
        title=row.title or "",
        company=row.company or "",
        role=row.role or "",
        interview_date=row.interview_date or "",
        transcript=row.transcript or "",
        items=row.items,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _meta(row: Debrief) -> dict:
    return {"company": row.company, "role": row.role, "title": row.title}


def _auto_title(body: DebriefCreate) -> str:
    if body.title.strip():
        return body.title.strip()
    parts = [p for p in [body.company.strip(), body.role.strip(), body.interview_date.strip()] if p]
    return " · ".join(parts) if parts else "未命名面经"


@router.get("", response_model=List[DebriefOut])
def list_debriefs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Debrief)
        .filter(Debrief.user_id == user.id)
        .order_by(Debrief.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.post("", response_model=DebriefOut)
def create_debrief(
    body: DebriefCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (body.transcript or "").strip():
        raise HTTPException(400, "transcript 不能为空")
    row = Debrief(
        id=f"db_{uuid.uuid4().hex[:10]}",
        user_id=user.id,
        title=_auto_title(body),
        company=body.company,
        role=body.role,
        interview_date=body.interview_date,
        transcript=body.transcript.strip(),
    )
    row.items = []
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/{debrief_id}", response_model=DebriefOut)
def get_debrief(
    debrief_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    return _to_out(row)


@router.put("/{debrief_id}", response_model=DebriefOut)
def update_debrief(
    debrief_id: str,
    body: DebriefUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{debrief_id}")
def delete_debrief(
    debrief_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.delete("/{debrief_id}/items/{item_id}", response_model=DebriefOut)
def delete_debrief_item(
    debrief_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    items = list(row.items or [])
    new_items = [it for it in items if it.get("id") != item_id]
    if len(new_items) == len(items):
        raise HTTPException(404, "问答条目不存在")
    row.items = new_items
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/{debrief_id}/extract", response_model=DebriefOut)
async def extract_qa(
    debrief_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    llm = get_llm()
    items = await llm.extract_interview_qa(row.transcript, _meta(row))
    row.items = items
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/{debrief_id}/analyze", response_model=DebriefOut)
async def analyze_qa(
    debrief_id: str,
    body: DebriefAnalyzeIn = DebriefAnalyzeIn(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Debrief, debrief_id, user, not_found="面经不存在")
    items = list(row.items or [])
    if not items:
        raise HTTPException(400, "请先提取问答")

    llm = get_llm()
    meta = _meta(row)
    updated = []
    for it in items:
        if body.item_id and it.get("id") != body.item_id:
            updated.append(it)
            continue
        result = await llm.analyze_interview_qa(it, meta)
        updated.append(
            {
                **it,
                "quality": result.get("quality") or "weak",
                "analysis": result.get("analysis") or "",
                "optimized_answer": result.get("optimized_answer") or "",
                "tags": result.get("tags") or it.get("tags") or [],
                "score": result.get("score"),
                "scoreDims": result.get("scoreDims") or {},
                "scoreHints": result.get("scoreHints") or [],
            }
        )
    row.items = updated
    db.commit()
    db.refresh(row)
    return _to_out(row)
