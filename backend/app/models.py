from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), default="")
    display_name: Mapped[str] = mapped_column(String(128), default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="实习")
    company: Mapped[str] = mapped_column(String(256), default="")
    title: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(128), default="")
    period: Mapped[str] = mapped_column(String(64), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    qa_tree_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    @property
    def tags(self) -> List[Any]:
        return json.loads(self.tags_json or "[]")

    @tags.setter
    def tags(self, value: List[Any]) -> None:
        self.tags_json = json.dumps(value, ensure_ascii=False)

    @property
    def qa_tree(self) -> List[Any]:
        return json.loads(self.qa_tree_json or "[]")

    @qa_tree.setter
    def qa_tree(self, value: List[Any]) -> None:
        self.qa_tree_json = json.dumps(value, ensure_ascii=False)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    source_exp_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_node_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    question: Mapped[str] = mapped_column(Text, default="")
    my_answer: Mapped[str] = mapped_column(Text, default="")
    reference_answer: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="待巩固")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    @property
    def tags(self) -> List[Any]:
        return json.loads(self.tags_json or "[]")

    @tags.setter
    def tags(self, value: List[Any]) -> None:
        self.tags_json = json.dumps(value, ensure_ascii=False)


class Debrief(Base):
    """真实面经：录音转写文本 + 提取出的问答档案。"""

    __tablename__ = "debriefs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    company: Mapped[str] = mapped_column(String(256), default="")
    role: Mapped[str] = mapped_column(String(128), default="")
    interview_date: Mapped[str] = mapped_column(String(32), default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    @property
    def items(self) -> List[Any]:
        return json.loads(self.items_json or "[]")

    @items.setter
    def items(self, value: List[Any]) -> None:
        self.items_json = json.dumps(value, ensure_ascii=False)


class InterviewSession(Base):
    """投递式模拟面试：勾选多段经历 + 岗位/JD，会话自带追问树。"""

    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    target_role: Mapped[str] = mapped_column(String(256), default="")
    jd_text: Mapped[str] = mapped_column(Text, default="")
    exp_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    qa_tree_json: Mapped[str] = mapped_column(Text, default="[]")
    channel: Mapped[str] = mapped_column(String(32), default="text")  # text | voice
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    @property
    def exp_ids(self) -> List[str]:
        return json.loads(self.exp_ids_json or "[]")

    @exp_ids.setter
    def exp_ids(self, value: List[str]) -> None:
        self.exp_ids_json = json.dumps(value, ensure_ascii=False)

    @property
    def qa_tree(self) -> List[Any]:
        return json.loads(self.qa_tree_json or "[]")

    @qa_tree.setter
    def qa_tree(self, value: List[Any]) -> None:
        self.qa_tree_json = json.dumps(value, ensure_ascii=False)
