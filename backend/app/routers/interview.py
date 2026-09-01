from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experience
from app.schemas import (
    AnswerIn,
    AnswerOut,
    DraftIn,
    DraftOut,
    InterviewStartOut,
    MarksIn,
    NextIn,
    NextOut,
    ReviewIn,
    ReviewOut,
)
from app.services.llm import get_llm
from app.tree_utils import (
    add_child,
    add_root,
    delete_node,
    empty_node,
    find_node,
    generate_node_id,
    resolve_insert_parent,
    update_node,
)

router = APIRouter(prefix="/api/interview", tags=["interview"])


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


def _get_exp(db: Session, exp_id: str) -> Experience:
    row = db.get(Experience, exp_id)
    if not row:
        raise HTTPException(404, "经历不存在")
    return row


@router.post("/{exp_id}/start", response_model=InterviewStartOut)
async def start_interview(exp_id: str, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    tree = row.qa_tree
    llm = get_llm()

    if not tree:
        generated = await llm.first_question(_exp_dict(row))
        node = empty_node(
            "q1",
            generated["question"],
            labels=generated.get("labels") or [],
            knowledgeTags=generated.get("knowledgeTags") or [],
        )
        tree = [node]
        row.qa_tree = tree
        db.commit()
        db.refresh(row)
        active = node
    else:
        active = tree[0]

    return InterviewStartOut(
        exp_id=row.id,
        active_node_id=active["nodeId"],
        question=active["question"],
        phase="feedback" if active.get("answer") else "question",
        node=active,
        qa_tree=row.qa_tree,
    )


@router.post("/{exp_id}/answer", response_model=AnswerOut)
async def submit_answer(exp_id: str, body: AnswerIn, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    tree = row.qa_tree
    node = find_node(tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")

    llm = get_llm()
    result = await llm.feedback(_exp_dict(row), node, body.answer)
    patch = {
        "answer": body.answer,
        "answerMode": body.answer_mode,
        "aiFeedback": result.get("aiFeedback") or "",
        "knowledgeTags": result.get("knowledgeTags") or [],
        "labels": result.get("labels") or [],
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
    )


@router.post("/{exp_id}/next", response_model=NextOut)
async def next_step(exp_id: str, body: NextIn, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    tree = row.qa_tree

    if body.action == "end":
        return NextOut(action="end", phase="idle", qa_tree=tree)

    if body.action == "switch_exp":
        return NextOut(action="switch_exp", phase="idle", qa_tree=tree)

    current = find_node(tree, body.from_node_id)
    if not current:
        raise HTTPException(404, "节点不存在")

    llm = get_llm()
    generated = await llm.next_question(_exp_dict(row), current, body.action)

    # 深挖/发散 → 子节点；换角度 → 同级兄弟（q1.1→q1.2，根则 q1→q2）
    try:
        insert_parent_id, siblings = resolve_insert_parent(tree, body.from_node_id, body.action)
    except KeyError:
        raise HTTPException(404, "节点不存在")

    node_id = generate_node_id(insert_parent_id, siblings)
    child = empty_node(
        node_id,
        generated["question"],
        labels=generated.get("labels") or [],
        knowledgeTags=generated.get("knowledgeTags") or [],
        triggerFrom=generated.get("triggerFrom"),
    )
    if insert_parent_id is None:
        tree = add_root(tree, child)
    else:
        tree = add_child(tree, insert_parent_id, child)
    row.qa_tree = tree
    db.commit()
    db.refresh(row)

    return NextOut(
        action=body.action,
        new_node=child,
        active_node_id=child["nodeId"],
        question=child["question"],
        phase="question",
        qa_tree=row.qa_tree,
    )


@router.post("/{exp_id}/draft", response_model=DraftOut)
async def draft_answer(exp_id: str, body: DraftIn, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    node = find_node(row.qa_tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    llm = get_llm()
    result = await llm.draft_answer(_exp_dict(row), node, body.mode)
    return DraftOut(draft=result.get("draft") or "", mode=body.mode)


@router.post("/{exp_id}/review", response_model=ReviewOut)
async def review_answer(exp_id: str, body: ReviewIn, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    node = find_node(row.qa_tree, body.node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    llm = get_llm()
    result = await llm.compare_review(
        _exp_dict(row),
        node.get("question") or "",
        node.get("answer") or "",
        body.new_answer,
    )
    return ReviewOut(
        question=node.get("question") or "",
        old_answer=node.get("answer") or "",
        new_answer=body.new_answer,
        progress=result.get("progress") or "",
        still_weak=result.get("still_weak") or "",
    )


@router.patch("/{exp_id}/nodes/{node_id}/marks")
def update_marks(exp_id: str, node_id: str, body: MarksIn, db: Session = Depends(get_db)):
    row = _get_exp(db, exp_id)
    node = find_node(row.qa_tree, node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    tree = update_node(row.qa_tree, node_id, {"marks": list(body.marks)})
    row.qa_tree = tree
    db.commit()
    db.refresh(row)
    return {"node": find_node(row.qa_tree, node_id), "qa_tree": row.qa_tree}


@router.delete("/{exp_id}/nodes/{node_id}")
def remove_node(exp_id: str, node_id: str, db: Session = Depends(get_db)):
    """删除追问树节点（含子树）。"""
    row = _get_exp(db, exp_id)
    tree, removed = delete_node(row.qa_tree, node_id)
    if not removed:
        raise HTTPException(404, "节点不存在")
    row.qa_tree = tree
    db.commit()
    db.refresh(row)
    return {"ok": True, "deleted_node_id": node_id, "qa_tree": row.qa_tree}
