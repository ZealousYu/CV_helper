from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Experience, User
from app.schemas import JobMatchIn, JobMatchOut
from app.services.llm import get_llm

router = APIRouter(prefix="/api/job", tags=["job"])


@router.post("/match", response_model=JobMatchOut)
async def match_jd(
    body: JobMatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows: List[Experience] = (
        db.query(Experience)
        .filter(Experience.user_id == user.id)
        .order_by(Experience.created_at.desc())
        .all()
    )
    experiences = [
        {
            "title": r.title,
            "company": r.company,
            "role": r.role,
            "period": r.period,
            "summary": r.summary,
            "metrics": r.metrics,
            "extra": r.extra,
            "tags": r.tags,
        }
        for r in rows
    ]
    llm = get_llm()
    jd = (body.jd_text or "").strip() or "（未粘贴 JD，请按通用互联网产品岗分析）"
    result = await llm.match_jd(jd, experiences)
    effective = "openai" if (settings.llm_provider == "openai" and settings.llm_api_key) else "mock"
    return JobMatchOut(
        score=result.get("score") or 0,
        matches=result.get("matches") or [],
        gaps=result.get("gaps") or [],
        actions=result.get("actions") or [],
        llm_effective=effective,
    )
