from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Experience, KnowledgeItem
from app.schemas import KnowledgeCreate, KnowledgeOut, KnowledgeUpdate
from app.tree_utils import find_node

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _to_out(row: KnowledgeItem) -> KnowledgeOut:
    return KnowledgeOut(
        id=row.id,
        source_exp_id=row.source_exp_id,
        source_node_id=row.source_node_id,
        question=row.question,
        my_answer=row.my_answer or "",
        reference_answer=row.reference_answer or "",
        tags=row.tags,
        note=row.note or "",
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=List[KnowledgeOut])
def list_knowledge(tag: Optional[str] = Query(None), db: Session = Depends(get_db)):
    rows = db.query(KnowledgeItem).order_by(KnowledgeItem.created_at.desc()).all()
    out = [_to_out(r) for r in rows]
    if tag:
        out = [k for k in out if any(tag in t or t in tag for t in k.tags)]
    return out


@router.post("", response_model=KnowledgeOut)
def create_knowledge(body: KnowledgeCreate, db: Session = Depends(get_db)):
    # 若带来源节点且字段为空，尝试从树上补全
    question = body.question
    my_answer = body.my_answer
    tags = body.tags
    if body.source_exp_id and body.source_node_id:
        exp = db.get(Experience, body.source_exp_id)
        if exp:
            node = find_node(exp.qa_tree, body.source_node_id)
            if node:
                if not question:
                    question = node.get("question") or ""
                if not my_answer:
                    my_answer = node.get("answer") or ""
                if not tags:
                    tags = node.get("knowledgeTags") or node.get("labels") or []

    if not question:
        raise HTTPException(400, "question 不能为空")

    row = KnowledgeItem(
        id=f"k_{uuid.uuid4().hex[:10]}",
        source_exp_id=body.source_exp_id,
        source_node_id=body.source_node_id,
        question=question,
        my_answer=my_answer,
        reference_answer=body.reference_answer,
        note=body.note,
        status=body.status,
    )
    row.tags = tags
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.put("/{kid}", response_model=KnowledgeOut)
def update_knowledge(kid: str, body: KnowledgeUpdate, db: Session = Depends(get_db)):
    row = db.get(KnowledgeItem, kid)
    if not row:
        raise HTTPException(404, "知识条目不存在")
    data = body.model_dump(exclude_unset=True)
    tags = data.pop("tags", None)
    for k, v in data.items():
        setattr(row, k, v)
    if tags is not None:
        row.tags = tags
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{kid}")
def delete_knowledge(kid: str, db: Session = Depends(get_db)):
    row = db.get(KnowledgeItem, kid)
    if not row:
        raise HTTPException(404, "知识条目不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
