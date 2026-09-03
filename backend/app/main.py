from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.access_gate import (
    AccessPasswordMiddleware,
    access_enabled,
    set_access_cookie,
    try_unlock,
    unlock_page,
)
from app.config import settings, _ENV_FILE as _ENV_HINT
from app.database import Base, SessionLocal, engine
from app.models import Experience, KnowledgeItem, Debrief, InterviewSession, User
from app.routers import experiences, interview, knowledge, debriefs, job, sessions, intro, voice, auth, admin
from app.routers.auth import ensure_admin_from_env, assign_orphan_data

app = FastAPI(title="CV Helper API", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# allow_origins=["*"] 时不能带 credentials，否则浏览器会拦跨域（含 file:// 的 Origin: null）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins == ["*"] else origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessPasswordMiddleware)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(experiences.router)
app.include_router(interview.router)
app.include_router(sessions.router)
app.include_router(knowledge.router)
app.include_router(debriefs.router)
app.include_router(job.router)
app.include_router(intro.router)
app.include_router(voice.router)

# 前端 Demo：同端口访问，避免 file:// 跨域麻烦
_DEMO_DIR = Path(__file__).resolve().parents[2] / "demo"
if _DEMO_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_DEMO_DIR), html=True), name="ui")


@app.get("/")
def root():
    if _DEMO_DIR.is_dir():
        return RedirectResponse(url="/ui/standalone.html")
    return {"message": "CV Helper API", "docs": "/docs"}


@app.get("/unlock")
def unlock_get(next: str = "/"):
    if not access_enabled():
        return RedirectResponse(url=next or "/")
    return unlock_page(next_url=next or "/", error=False)


@app.post("/unlock")
async def unlock_post(
    request: Request,
    password: str = Form(""),
    next: str = Form("/"),
):
    if not access_enabled():
        return RedirectResponse(url=next or "/", status_code=303)
    token = try_unlock(password)
    if not token:
        return unlock_page(next_url=next or "/", error=True)
    target = next or "/"
    if not target.startswith("/"):
        target = "/"
    resp = RedirectResponse(url=target, status_code=303)
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    set_access_cookie(resp, token, secure=secure)
    return resp


def _ensure_user_id_column(table: str) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if "user_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(64)"))


def _migrate_schema() -> None:
    Base.metadata.create_all(bind=engine)
    for table in ("experiences", "knowledge_items", "debriefs", "interview_sessions"):
        _ensure_user_id_column(table)


@app.on_event("startup")
def on_startup():
    # 确保持久化目录存在（Docker /data）
    db_url = settings.database_url or ""
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url[len("sqlite:///"):])
        if db_path.parent and str(db_path.parent) not in ("", "."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_schema()
    db = SessionLocal()
    try:
        admin_user = ensure_admin_from_env(db)
        # 若已有管理员但 env 未配：把遗留空归属数据挂到首位管理员
        if not admin_user:
            admin_user = db.query(User).filter(User.is_admin.is_(True)).order_by(User.created_at.asc()).first()
        if admin_user:
            assign_orphan_data(db, admin_user.id)
            db.commit()
            _purge_demo_seed_experiences(db)
    finally:
        db.close()


def _purge_demo_seed_experiences(db) -> None:
    """清理历史自动写入的示例经历。"""
    demo_summaries = (
        "用户增长模块的数据分析与需求推进",
        "校园二手交易数据分析看板",
        "did stuff",  # 早期接口测试残留
    )
    rows = db.query(Experience).all()
    changed = False
    for row in rows:
        summary = row.summary or ""
        title = row.title or ""
        if any(s in summary for s in demo_summaries) or title in (
            "XX公司 · 产品实习生",
            "校园数据分析项目",
        ):
            db.delete(row)
            changed = True
    if changed:
        db.commit()


@app.get("/api/health")
def health():
    from app.services.doubao_tts import is_doubao_tts_configured

    effective = "openai" if (settings.llm_provider == "openai" and settings.llm_api_key) else "mock"
    tts_configured = is_doubao_tts_configured()
    tts_provider = settings.tts_provider or "auto"
    tts_effective = "doubao" if tts_configured and tts_provider != "browser" else "browser"
    return {
        "ok": True,
        "llm_provider": settings.llm_provider,
        "llm_key_set": bool(settings.llm_api_key),
        "llm_effective": effective,
        "llm_model": settings.llm_model if effective == "openai" else None,
        "tts_provider": tts_provider,
        "tts_effective": tts_effective,
        "tts_doubao_configured": tts_configured,
        "access_password_enabled": bool((settings.access_password or "").strip()),
        "auth_required": True,
        "env_file": str(_ENV_HINT),
    }
