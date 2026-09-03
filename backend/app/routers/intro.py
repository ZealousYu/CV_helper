from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User
from app.schemas import IntroIn, IntroOut
from app.services.llm import get_llm

router = APIRouter(prefix="/api/intro", tags=["intro"])


@router.post("", response_model=IntroOut)
async def intro_assist(body: IntroIn, user: User = Depends(get_current_user)):
    del user
    llm = get_llm()
    exps = [e.model_dump() for e in body.experiences]
    if body.mode == "generate":
        result = await llm.intro_generate(exps, body.target_role)
    elif body.mode == "polish":
        result = await llm.intro_polish(body.content, exps, body.target_role)
    else:
        result = await llm.intro_guide(
            body.content,
            body.guide_answers,
            exps,
            body.target_role,
        )
    return IntroOut(
        content=(result.get("content") or "").strip(),
        hint=(result.get("hint") or "").strip(),
    )
