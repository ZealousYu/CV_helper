from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ExperienceCreate(BaseModel):
    type: str = "实习"
    company: str
    role: str
    period: str
    summary: str
    metrics: str = ""
    extra: str = ""
    tags: List[str] = Field(default_factory=list)
    title: Optional[str] = None


class ExperienceUpdate(BaseModel):
    type: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    period: Optional[str] = None
    summary: Optional[str] = None
    metrics: Optional[str] = None
    extra: Optional[str] = None
    tags: Optional[List[str]] = None
    title: Optional[str] = None


class ExperienceOut(BaseModel):
    id: str
    type: str
    company: str
    title: str
    role: str
    period: str
    summary: str
    metrics: str
    extra: str
    tags: List[str]
    qa_tree: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InterviewStartOut(BaseModel):
    exp_id: str
    active_node_id: str
    question: str
    phase: str
    node: Dict[str, Any]
    qa_tree: List[Dict[str, Any]]


class AnswerIn(BaseModel):
    node_id: str
    answer: str
    answer_mode: Literal["user_answered", "ai_generated", "framework_only"] = "user_answered"


class AnswerOut(BaseModel):
    node: Dict[str, Any]
    qa_tree: List[Dict[str, Any]]
    ai_feedback: str
    knowledge_tags: List[str]


class NextIn(BaseModel):
    from_node_id: str
    action: Literal["deep_dive", "new_angle", "diverge", "switch_exp", "end"]


class NextOut(BaseModel):
    action: str
    new_node: Optional[Dict[str, Any]] = None
    active_node_id: Optional[str] = None
    question: Optional[str] = None
    phase: str
    qa_tree: List[Dict[str, Any]]


class MarksIn(BaseModel):
    marks: List[Literal["star", "practice"]]


class KnowledgeCreate(BaseModel):
    question: str
    my_answer: str = ""
    reference_answer: str = ""
    tags: List[str] = Field(default_factory=list)
    note: str = ""
    status: str = "待巩固"
    source_exp_id: Optional[str] = None
    source_node_id: Optional[str] = None


class KnowledgeUpdate(BaseModel):
    question: Optional[str] = None
    my_answer: Optional[str] = None
    reference_answer: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[str] = None


class KnowledgeOut(BaseModel):
    id: str
    source_exp_id: Optional[str]
    source_node_id: Optional[str]
    question: str
    my_answer: str
    reference_answer: str
    tags: List[str]
    note: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DebriefCreate(BaseModel):
    title: str = ""
    company: str = ""
    role: str = ""
    interview_date: str = ""
    transcript: str


class DebriefUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    interview_date: Optional[str] = None
    transcript: Optional[str] = None


class DebriefOut(BaseModel):
    id: str
    title: str
    company: str
    role: str
    interview_date: str
    transcript: str
    items: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DebriefAnalyzeIn(BaseModel):
    item_id: Optional[str] = None  # 空则分析全部


class DraftIn(BaseModel):
    node_id: str
    mode: Literal["ai_generated", "framework_only"] = "ai_generated"


class DraftOut(BaseModel):
    draft: str
    mode: str


class ReviewIn(BaseModel):
    node_id: str
    new_answer: str


class ReviewOut(BaseModel):
    question: str
    old_answer: str
    new_answer: str
    progress: str
    still_weak: str


class JobMatchIn(BaseModel):
    jd_text: str


class JobMatchOut(BaseModel):
    score: int
    matches: List[Dict[str, Any]]
    gaps: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    llm_effective: str


class ParsedExperienceCard(BaseModel):
    """简历解析预览卡（尚未入库）。"""

    type: str = "实习"
    company: str = ""
    role: str = ""
    period: str = ""
    summary: str = ""
    metrics: str = ""
    extra: str = ""
    tags: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    missing_hint: str = ""


class ResumeParseOut(BaseModel):
    items: List[ParsedExperienceCard]
    text_preview: str = ""
    warning: str = ""
    llm_effective: str
    char_count: int = 0


class ResumeImportIn(BaseModel):
    items: List[ExperienceCreate]


class ResumeImportOut(BaseModel):
    created: List[ExperienceOut]
    count: int
