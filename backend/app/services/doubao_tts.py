"""火山引擎 / 豆包语音合成 V3（HTTP 单向流式）。"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

DOUBAO_TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

# 面试读题：仅保留女声 / 男声各一
DOUBAO_VOICE_PACKS: List[Dict[str, str]] = [
    {
        "id": "zh_female_kefunvsheng_uranus_bigtts",
        "name": "女声",
        "gender": "女",
        "style": "温和稳重",
        "resource_id": "seed-tts-2.0",
    },
    {
        "id": "zh_male_taocheng_uranus_bigtts",
        "name": "男声",
        "gender": "男",
        "style": "清爽磁性",
        "resource_id": "seed-tts-2.0",
    },
]


def _strip(s: Optional[str]) -> str:
    return (s or "").strip()


def is_doubao_tts_configured() -> bool:
    """新版 API Key，或旧版 AppId+AccessToken，任一即可。"""
    if _strip(settings.doubao_tts_api_key):
        return True
    return bool(_strip(settings.doubao_tts_app_id) and _strip(settings.doubao_tts_access_key))


def list_voice_packs() -> List[Dict[str, str]]:
    return list(DOUBAO_VOICE_PACKS)


def resolve_speaker(speaker: Optional[str] = None) -> str:
    allowed = {p["id"] for p in DOUBAO_VOICE_PACKS}
    s = _strip(speaker) or _strip(settings.doubao_tts_speaker)
    if s in allowed:
        return s
    return DOUBAO_VOICE_PACKS[0]["id"]


def _resource_for_speaker(speaker: str) -> str:
    configured = _strip(settings.doubao_tts_resource_id)
    if configured:
        return configured
    if speaker.startswith("S_"):
        return "seed-icl-2.0"
    for pack in DOUBAO_VOICE_PACKS:
        if pack["id"] == speaker and pack.get("resource_id"):
            return pack["resource_id"]
    if "_uranus_" in speaker or "_saturn_" in speaker:
        return "seed-tts-2.0"
    return "seed-tts-2.0"


def _auth_headers(resource_id: str) -> Dict[str, str]:
    """
    鉴权对齐官方文档：
    - 新版控制台：X-Api-Key（推荐，双向流式文档只用这个）
    - 旧版控制台：X-Api-App-Id + X-Api-Access-Key
    """
    headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }
    api_key = _strip(settings.doubao_tts_api_key)
    if api_key:
        headers["X-Api-Key"] = api_key
        return headers
    headers["X-Api-App-Id"] = _strip(settings.doubao_tts_app_id)
    headers["X-Api-Access-Key"] = _strip(settings.doubao_tts_access_key)
    return headers


def _build_additions(speaker: str) -> str:
    extras: Dict[str, Any] = {}
    if speaker.startswith("S_"):
        extras["model_type"] = 4
    return json.dumps(extras, ensure_ascii=False)


async def synthesize_speech(text: str, *, speaker: Optional[str] = None) -> bytes:
    """合成语音，返回 mp3 二进制。读题场景用 HTTP 单向流式即可（不必上 WebSocket 双向）。"""
    if not is_doubao_tts_configured():
        raise RuntimeError(
            "未配置豆包 TTS：请在 backend/.env 填写 DOUBAO_TTS_API_KEY"
            "（新版控制台），或 DOUBAO_TTS_APP_ID + DOUBAO_TTS_ACCESS_KEY（旧版）"
        )

    speaker = resolve_speaker(speaker)
    resource_id = _resource_for_speaker(speaker)

    body = {
        "user": {"uid": f"cv_helper_{uuid.uuid4().hex[:12]}"},
        "req_params": {
            "text": (text or "")[:900],
            "speaker": speaker,
            "audio_params": {"format": "mp3", "sample_rate": 24000},
            "additions": _build_additions(speaker),
        },
    }
    headers = _auth_headers(resource_id)

    chunks: list[bytes] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", DOUBAO_TTS_URL, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                raw = (await resp.aread()).decode("utf-8", errors="replace")
                raise RuntimeError(_friendly_http_error(resp.status_code, raw, resource_id))
            async for line in resp.aiter_lines():
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                code = obj.get("code")
                if code == 20000000:
                    break
                if code not in (0, None) and code != 0:
                    msg = obj.get("message") or obj.get("msg") or str(obj)
                    raise RuntimeError(f"豆包 TTS 错误 code={code}: {msg}")
                data = obj.get("data")
                if data:
                    chunks.append(base64.b64decode(data))

    if not chunks:
        raise RuntimeError("豆包 TTS 未返回音频数据")
    return b"".join(chunks)


def _friendly_http_error(status: int, raw: str, resource_id: str) -> str:
    msg = raw
    try:
        obj = json.loads(raw)
        header = obj.get("header") or {}
        msg = header.get("message") or obj.get("message") or raw
        code = header.get("code")
        if code is not None:
            msg = f"code={code}: {msg}"
    except Exception:
        pass
    lower = (msg or "").lower()
    if status == 403 and ("not granted" in lower or "45000030" in str(msg)):
        return (
            f"语音资源未开通（{resource_id}）。"
            "请到火山引擎控制台开通「豆包语音合成」并给当前应用授权："
            "https://console.volcengine.com/speech/service/8 "
            "开通后若仍失败，确认买的是 2.0 字符版（seed-tts-2.0），"
            "或把 DOUBAO_TTS_RESOURCE_ID 改成你已开通的版本。"
            f" 原始信息：{msg}"
        )
    return f"HTTP {status}: {msg}"
