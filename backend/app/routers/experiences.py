from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_owned
from app.models import Experience, User
from app.schemas import (
    ExperienceCreate,
    ExperienceOut,
    ExperienceUpdate,
    ParsedExperienceCard,
    ResumeImportIn,
    ResumeImportOut,
    ResumeParseOut,
    SuggestExpTagsIn,
    SuggestExpTagsOut,
)
from app.services.llm import get_llm
from app.services.resume_text import extract_text
from app.tag_utils import normalize_exp_tags

router = APIRouter(prefix="/api/experiences", tags=["experiences"])


def _to_out(row: Experience) -> ExperienceOut:
    return ExperienceOut(
        id=row.id,
        type=row.type,
        company=row.company,
        title=row.title,
        role=row.role,
        period=row.period,
        summary=row.summary,
        metrics=row.metrics or "",
        extra=row.extra or "",
        tags=row.tags,
        qa_tree=row.qa_tree,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _make_title(company: str, role: str, title: Optional[str]) -> str:
    if title:
        return title
    return f"{company} · {role}"


def _create_row(body: ExperienceCreate, db: Session, user: User) -> Experience:
    row = Experience(
        id=f"exp_{uuid.uuid4().hex[:10]}",
        user_id=user.id,
        type=body.type,
        company=body.company,
        role=body.role,
        period=body.period,
        summary=body.summary,
        metrics=body.metrics,
        extra=body.extra,
        title=_make_title(body.company, body.role, body.title),
    )
    row.tags = normalize_exp_tags(body.tags or [])
    row.qa_tree = []
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=List[ExperienceOut])
def list_experiences(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Experience)
        .filter(Experience.user_id == user.id)
        .order_by(Experience.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.post("", response_model=ExperienceOut)
def create_experience(
    body: ExperienceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _to_out(_create_row(body, db, user))


@router.post("/parse", response_model=ResumeParseOut)
async def parse_resume(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
):
    """上传 PDF/docx/txt 或粘贴文本 → 抽出经历预览（不入库）。原文件不落盘。"""
    del user
    warning = ""
    resume_text = (text or "").strip()

    if file is not None and file.filename:
        data = await file.read()
        try:
            extracted, warn = extract_text(file.filename, data)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        warning = warn
        if extracted:
            resume_text = extracted if not resume_text else f"{resume_text}\n\n{extracted}"

    if not resume_text or len(resume_text) < 20:
        raise HTTPException(400, "请上传 PDF/Word，或粘贴至少一段简历文本")

    llm = get_llm()
    raw_items = await llm.parse_resume_experiences(resume_text)
    items = [ParsedExperienceCard(**it) for it in raw_items]
    effective = "openai" if (settings.llm_provider == "openai" and settings.llm_api_key) else "mock"
    preview = resume_text[:400] + ("…" if len(resume_text) > 400 else "")
    return ResumeParseOut(
        items=items,
        text_preview=preview,
        warning=warning,
        llm_effective=effective,
        char_count=len(resume_text),
    )


@router.post("/import", response_model=ResumeImportOut)
def import_experiences(
    body: ResumeImportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """确认导入：把勾选的预览卡批量写入经历库。"""
    if not body.items:
        raise HTTPException(400, "请至少选择一条经历")
    if len(body.items) > 20:
        raise HTTPException(400, "一次最多导入 20 条")
    created = []
    for item in body.items:
        if not (item.company and item.role and item.period and item.summary):
            raise HTTPException(400, "每条经历需包含公司、角色、时长、主要工作")
        created.append(_to_out(_create_row(item, db, user)))
    return ResumeImportOut(created=created, count=len(created))


@router.get("/{exp_id}", response_model=ExperienceOut)
def get_experience(
    exp_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Experience, exp_id, user, not_found="经历不存在")
    return _to_out(row)


@router.put("/{exp_id}", response_model=ExperienceOut)
def update_experience(
    exp_id: str,
    body: ExperienceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Experience, exp_id, user, not_found="经历不存在")
    data = body.model_dump(exclude_unset=True)
    tags = data.pop("tags", None)
    for k, v in data.items():
        setattr(row, k, v)
    if tags is not None:
        row.tags = normalize_exp_tags(tags)
    if "company" in data or "role" in data or "title" in data:
        if not data.get("title"):
            row.title = _make_title(row.company, row.role, None)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/suggest-tags", response_model=SuggestExpTagsOut)
async def suggest_exp_tags(
    body: SuggestExpTagsIn,
    user: User = Depends(get_current_user),
):
    """根据经历文案生成能力标签（接 LLM；未配 Key 时走启发式）。"""
    del user
    llm = get_llm()
    result = await llm.suggest_exp_tags(body.model_dump())
    tags = normalize_exp_tags(result.get("tags") or [])
    effective = "openai" if (settings.llm_provider == "openai" and settings.llm_api_key) else "mock"
    return SuggestExpTagsOut(tags=tags, llm_effective=effective)


@router.post("/normalize-tags", response_model=List[ExperienceOut])
def normalize_all_tags(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """将本人经历的标签归并到主题（数据分析 / 产品 / …）。"""
    rows = db.query(Experience).filter(Experience.user_id == user.id).all()
    for row in rows:
        row.tags = normalize_exp_tags(row.tags or [])
    db.commit()
    rows = (
        db.query(Experience)
        .filter(Experience.user_id == user.id)
        .order_by(Experience.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.delete("/{exp_id}")
def delete_experience(
    exp_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_owned(db, Experience, exp_id, user, not_found="经历不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
