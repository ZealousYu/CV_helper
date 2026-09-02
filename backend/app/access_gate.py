"""公网访问口令：设置 ACCESS_PASSWORD 后，未解锁请求会被拦到解锁页。"""

from __future__ import annotations

import hmac
from typing import Optional
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

COOKIE_NAME = "cv_helper_access"
UNLOCK_PATH = "/unlock"


def _expected_token() -> str:
    pwd = (settings.access_password or "").strip()
    if not pwd:
        return ""
    # 不直接存明文密码到 cookie，用 hmac 派生固定 token
    return hmac.new(b"cv-helper-access", pwd.encode("utf-8"), "sha256").hexdigest()


def access_enabled() -> bool:
    return bool((settings.access_password or "").strip())


def request_unlocked(request: Request) -> bool:
    expected = _expected_token()
    if not expected:
        return True
    cookie = request.cookies.get(COOKIE_NAME) or ""
    header = request.headers.get("x-access-token") or ""
    auth = request.headers.get("authorization") or ""
    bearer = ""
    if auth.lower().startswith("bearer "):
        bearer = auth[7:].strip()
    provided = cookie or header or bearer
    return bool(provided) and hmac.compare_digest(provided, expected)


UNLOCK_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>简历面试助手 · 访问验证</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#e8edf4; margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center; }
    .box { background:#fff; padding:28px 24px; border-radius:12px; width:min(400px,92vw); box-shadow:0 8px 28px rgba(21,32,43,.12); }
    h1 { font-size:20px; margin:0 0 8px; }
    p { color:#5c6b7a; font-size:14px; margin:0 0 16px; line-height:1.5; }
    input { width:100%; padding:10px 12px; border:1px solid #b8c5d6; border-radius:8px; font-size:14px; box-sizing:border-box; }
    button { margin-top:12px; width:100%; padding:10px 14px; border:none; border-radius:8px; background:#1a56db; color:#fff; font-size:14px; font-weight:600; cursor:pointer; }
    .err { color:#c62828; font-size:13px; margin-top:10px; display:none; }
  </style>
</head>
<body>
  <div class="box">
    <h1>访问验证</h1>
    <p>此站点已开启访问密码。输入后可进入简历面试助手。</p>
    <form method="post" action="/unlock">
      <input type="password" name="password" placeholder="访问密码" autofocus required />
      <input type="hidden" name="next" value="__NEXT__" />
      <button type="submit">进入</button>
    </form>
    <div class="err" id="err" style="__ERR_STYLE__">密码不正确，请重试</div>
  </div>
</body>
</html>
"""


class AccessPasswordMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not access_enabled():
            return await call_next(request)

        path = request.url.path or "/"
        if path in (UNLOCK_PATH, "/api/health") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        if request_unlocked(request):
            return await call_next(request)

        # API 返回 401；页面跳转解锁
        if path.startswith("/api/"):
            return JSONResponse({"detail": "需要访问密码"}, status_code=401)

        next_url = path
        if request.url.query:
            next_url += "?" + request.url.query
        return RedirectResponse(url=f"{UNLOCK_PATH}?next={quote(next_url, safe='')}", status_code=302)


def unlock_page(next_url: str = "/", error: bool = False) -> HTMLResponse:
    html = UNLOCK_HTML.replace("__NEXT__", next_url or "/").replace(
        "__ERR_STYLE__", "display:block" if error else "display:none"
    )
    return HTMLResponse(html)


def try_unlock(password: str) -> Optional[str]:
    """校验密码，成功返回 cookie token。"""
    expected_pwd = (settings.access_password or "").strip()
    if not expected_pwd:
        return None
    if not password or not hmac.compare_digest(password.strip(), expected_pwd):
        return None
    return _expected_token()


def set_access_cookie(response: Response, token: str, secure: bool = False) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        secure=secure,
    )
