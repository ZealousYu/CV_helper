"""投递式面试会话：多段经历 + 岗位/JD → 系统覆盖提问。"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned
from app.models import Experience, InterviewSession, User
from app.schemas import (
    AnswerOut,
    DraftIn,
    DraftOut,
    ExperienceOut,
    SessionAnswerIn,
    SessionArchiveIn,
    SessionArchiveOut,
    SessionCreateIn,
    SessionNextIn,
    SessionOut,
)
from app.services.llm import get_llm
from app.tree_utils import (
    add_child,
    add_root,
    clone_subtree_with_new_ids,
    empty_node,
    find_duplicate_question,
    find_node,
    generate_node_id,
    resolve_insert_parent,
    update_node,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _exp_dict(row: Experience) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "company": row.company,
        "role": row.role,
        "period": row.period,
        "summary": row.summary,
        "metrics": row.metrics,
        "extra": row.extra,
        "tags": row.tags,
    }


def _collect_asked_titles(tree: List[Dict[str, Any]]) -> List[str]:
    titles: List[str] = []

    def walk(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes or []:
            t = n.get("targetExpTitle")
            if t and t not in titles:
                titles.append(t)
            walk(n.get("children") or [])

    walk(tree)
    return titles


def _covered_ids(tree: List[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []

    def walk(nodes: List[Dict[str, Any]]) -> None:
        for n in nodes or []:
            tid = n.get("targetExpId")
            if tid and tid not in ids:
                ids.append(tid)
            walk(n.get("children") or [])

    walk(tree)
    return ids


def _load_exps(db: Session, exp_ids: List[str], user: User) -> List[Experience]:
    rows = []
    for eid in exp_ids:
        row = (
            db.query(Experience)
            .filter(Experience.id == eid, Experience.user_id == user.id)
            .first()
        )
        if row:
            rows.append(row)
    return rows


def _get_session(db: Session, sid: str, user: User) -> InterviewSession:
    return get_owned(db, InterviewSession, sid, user, not_found="面试会话不存在")


def _to_out(
    row: InterviewSession,
    *,
    active_node_id: Optional[str] = None,
    question: Optional[str] = None,
    phase: str = "idle",
    node: Optional[Dict[str, Any]] = None,
) -> SessionOut:
    return SessionOut(
        id=row.id,
        target_role=row.target_role or "",
        jd_text=row.jd_text or "",
        exp_ids=row.exp_ids,
        channel=row.channel or "text",
        qa_tree=row.qa_tree,
        active_node_id=active_node_id,
        question=question,
        phase=phase,
        node=node,
        covered_exp_ids=_covered_ids(row.qa_tree),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _composite_exp(exps: List[Experience], target_role: str) -> Dict[str, Any]:
    """给 draft/feedback 用的合成经历摘要。"""
    titles = "、".join(e.title or e.company for e in exps) or "投递经历"
    return {
        "title": f"投递包 · {target_role or titles}",
        "company": titles,
        "role": target_role or (exps[0].role if exps else ""),
        "period": "",
        "summary": "；".join((e.summary or "")[:120] for e in exps),
        "metrics": "；".join(e.metrics for e in exps if e.metrics),
        "extra": "",
        "tags": [],
    }


@router.get("", response_model=List[SessionOut])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(20)
        .all()
    )
    return [_to_out(r) for r in rows]


@router.post("/start", response_model=SessionOut)
async def start_session(body: SessionCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not body.exp_ids:
        raise HTTPException(400, "请至少选择一段经历")
    exps = _load_exps(db, body.exp_ids, user)
    if not exps:
        raise HTTPException(400, "所选经历不存在")
    # 保持用户勾选顺序
    order = {eid: i for i, eid in enumerate(body.exp_ids)}
    exps.sort(key=lambda r: order.get(r.id, 999))

    llm = get_llm()
    generated = await llm.session_first_question(
        [_exp_dict(e) for e in exps],
        body.target_role.strip(),
        body.jd_text.strip(),
    )
    node = empty_node(
        "q1",
        generated["question"],
        labels=generated.get("labels") or [],
        knowledgeTags=generated.get("knowledgeTags") or [],
        targetExpId=generated.get("targetExpId") or exps[0].id,
        targetExpTitle=generated.get("targetExpTitle") or exps[0].title,
    )
    row = InterviewSession(
        id=f"sess_{uuid.uuid4().hex[:10]}",
        user_id=user.id,
        target_role=body.target_role.strip(),
        jd_text=body.jd_text.strip(),
        channel=body.channel,
    )
    row.exp_ids = [e.id for e in exps]
    row.qa_tree = [node]
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(
        row,
        active_node_id=node["nodeId"],
        question=node["question"],
        phase="question",
        node=node,
    )


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_session(db, session_id, user)
    tree = row.qa_tree
    active = tree[0] if tree else None
    return _to_out(
        row,
        active_node_id=active["nodeId"] if active else None,
        question=active.get("question") if active else None,
        phase="feedback" if active and active.get("answer") else ("question" if active else "idle"),
        node=active,
    )


@router.post("/{session_id}/answer", response_model=AnswerOut)
async def session_answer(session_id: str, body: SessionAnswerIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_session(db, session_id, user)
    tree = row.qa_tree
    node = find_node(tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    exps = _load_exps(db, row.exp_ids, user)
    # feedback 锚定本题 target 经历，否则用合成包
    target = next((e for e in exps if e.id == node.get("targetExpId")), None)
    exp_ctx = _exp_dict(target) if target else _composite_exp(exps, row.target_role)
    if row.jd_text:
        exp_ctx = {**exp_ctx, "extra": (exp_ctx.get("extra") or "") + f"\n【岗位】{row.target_role}\n【JD】{row.jd_text[:1500]}"}

    llm = get_llm()
    result = await llm.feedback(exp_ctx, node, body.answer)
    patch = {
        "answer": body.answer,
        "answerMode": body.answer_mode,
        "aiFeedback": result.get("aiFeedback") or "",
        "knowledgeTags": result.get("knowledgeTags") or [],
        "labels": result.get("labels") or [],
        "score": result.get("score"),
        "scoreDims": result.get("scoreDims") or {},
        "scoreHints": result.get("scoreHints") or [],
    }
    tree = update_node(tree, body.node_id, patch)
    row.qa_tree = tree
    db.commit()
    db.refresh(row)
    updated = find_node(row.qa_tree, body.node_id)
    return AnswerOut(
        node=updated or {},
        qa_tree=row.qa_tree,
        ai_feedback=patch["aiFeedback"],
        knowledge_tags=patch["knowledgeTags"],
        score=patch.get("score"),
        score_dims=patch.get("scoreDims") or {},
        score_hints=patch.get("scoreHints") or [],
    )


@router.post("/{session_id}/next", response_model=SessionOut)
async def session_next(session_id: str, body: SessionNextIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_session(db, session_id, user)
    if body.action == "end":
        return _to_out(row, phase="idle")

    tree = row.qa_tree
    current = find_node(tree, body.from_node_id)
    if not current:
        raise HTTPException(404, "节点不存在")

    exps = _load_exps(db, row.exp_ids, user)
    llm = get_llm()
    generated = await llm.session_next_question(
        [_exp_dict(e) for e in exps],
        row.target_role or "",
        row.jd_text or "",
        current,
        body.action,
        _collect_asked_titles(tree),
    )

    # cover_next：作为同级新根问（换经历）；其余按原分支规则
    tree_action = "new_angle" if body.action == "cover_next" else body.action
    if tree_action not in ("deep_dive", "new_angle", "diverge"):
        tree_action = "deep_dive"
    try:
        insert_parent_id, siblings = resolve_insert_parent(tree, body.from_node_id, tree_action)
    except KeyError:
        raise HTTPException(404, "节点不存在")

    node_id = generate_node_id(insert_parent_id, siblings)
    child = empty_node(
        node_id,
        generated["question"],
        labels=generated.get("labels") or [],
        knowledgeTags=generated.get("knowledgeTags") or [],
        triggerFrom=generated.get("triggerFrom"),
        targetExpId=generated.get("targetExpId"),
        targetExpTitle=generated.get("targetExpTitle"),
    )
    if insert_parent_id is None:
        tree = add_root(tree, child)
    else:
        tree = add_child(tree, insert_parent_id, child)
    row.qa_tree = tree
    db.commit()
    db.refresh(row)
    return _to_out(
        row,
        active_node_id=child["nodeId"],
        question=child["question"],
        phase="question",
        node=child,
    )


@router.post("/{session_id}/draft", response_model=DraftOut)
async def session_draft(session_id: str, body: DraftIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _get_session(db, session_id, user)
    node = find_node(row.qa_tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    exps = _load_exps(db, row.exp_ids, user)
    target = next((e for e in exps if e.id == node.get("targetExpId")), None)
    exp_ctx = _exp_dict(target) if target else _composite_exp(exps, row.target_role)
    llm = get_llm()
    result = await llm.draft_answer(exp_ctx, node, body.mode)
    return DraftOut(draft=result.get("draft") or "", mode=body.mode)


def _exp_out(row: Experience) -> ExperienceOut:
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


@router.post("/{session_id}/archive-node", response_model=SessionArchiveOut)
def archive_session_node(session_id: str, body: SessionArchiveIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """将语音会话追问树中的节点归档到对应经历的笔记本（Experience.qa_tree）。"""
    row = _get_session(db, session_id, user)
    node = find_node(row.qa_tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")

    if node.get("archivedToExpId") and node.get("archivedToNodeId"):
        exp_row = (
            db.query(Experience)
            .filter(Experience.id == node["archivedToExpId"], Experience.user_id == user.id)
            .first()
        )
        if not exp_row:
            raise HTTPException(404, "已归档的经历不存在")
        return SessionArchiveOut(
            exp_id=node["archivedToExpId"],
            exp_node_id=node["archivedToNodeId"],
            already_existed=True,
            message="该题已归档过",
            experience=_exp_out(exp_row),
            session=_to_out(row),
        )

    exp_id = node.get("targetExpId") or (row.exp_ids[0] if row.exp_ids else None)
    if not exp_id:
        raise HTTPException(400, "无法确定目标经历，请确认节点锚定经历")
    exp_row = (
        db.query(Experience)
        .filter(Experience.id == exp_id, Experience.user_id == user.id)
        .first()
    )
    if not exp_row:
        raise HTTPException(404, "目标经历不存在")

    exp_tree = list(exp_row.qa_tree or [])
    dup = find_duplicate_question(exp_tree, node.get("question") or "")
    already = False
    if dup:
        archived_node_id = dup["nodeId"]
        already = True
        msg = "笔记本里已有相同问题，已关联到原节点"
    else:
        cloned = clone_subtree_with_new_ids(node, None, exp_tree)
        exp_tree = add_root(exp_tree, cloned)
        exp_row.qa_tree = exp_tree
        archived_node_id = cloned["nodeId"]
        msg = "已归档到笔记本"

    session_tree = update_node(
        row.qa_tree,
        body.node_id,
        {"archivedToExpId": exp_id, "archivedToNodeId": archived_node_id},
    )
    row.qa_tree = session_tree
    db.commit()
    db.refresh(exp_row)
    db.refresh(row)

    return SessionArchiveOut(
        exp_id=exp_id,
        exp_node_id=archived_node_id,
        already_existed=already,
        message=msg,
        experience=_exp_out(exp_row),
        session=_to_out(row),
    )
