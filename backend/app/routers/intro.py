from __future__ import annotations

from fastapi import APIRouter

from app.schemas import IntroIn, IntroOut
from app.services.llm import get_llm

router = APIRouter(prefix="/api/intro", tags=["intro"])


@router.post("", response_model=IntroOut)
async def intro_assist(body: IntroIn):
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
