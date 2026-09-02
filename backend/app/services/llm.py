from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.tag_utils import normalize_exp_tags


L1_TAGS = ["行为面试", "技术", "业务理解", "协作沟通", "职业规划"]

# 参考 interview-agent 语义维（准确性/深度/逻辑/表达）；文字模式权重均分。
# 语音上线后再叠副语言/视觉（彼时语义约占 75%）。
SCORE_DIM_KEYS = ("accuracy", "depth", "logic", "expression")
SCORE_DIM_LABELS = {
    "accuracy": "准确性",
    "depth": "深度",
    "logic": "逻辑",
    "expression": "表达",
}
SCORE_DIM_WEIGHTS = {
    "accuracy": 0.30,
    "depth": 0.30,
    "logic": 0.20,
    "expression": 0.20,
}


def guess_tags(question: str) -> List[str]:
    q = question or ""
    if re.search(r"RAG|向量|embedding|大模型|LLM|AI", q, re.I):
        return ["技术", "AI应用", "RAG调优"]
    if re.search(r"后端|接口|数据库|MySQL|Redis", q, re.I):
        return ["技术", "后端", "知识库"]
    if re.search(r"协作|跨部门|冲突|沟通", q, re.I):
        return ["协作沟通", "跨部门"]
    if re.search(r"指标|漏斗|增长|数据", q, re.I):
        return ["业务理解", "指标设计"]
    if re.search(r"介绍|负责|STAR", q, re.I):
        return ["行为面试", "项目介绍"]
    return ["行为面试"]


def _clamp_dim(v: Any) -> int:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        n = 5
    return max(0, min(10, n))


def normalize_score_block(raw: Optional[Dict[str, Any]] = None, answer: str = "") -> Dict[str, Any]:
    """统一分数结构：score 0–100 + 四维 0–10。不驱动追问路由。"""
    raw = raw or {}
    dims_in = raw.get("scoreDims") or raw.get("score_dims") or raw
    dims = {k: _clamp_dim(dims_in.get(k) if isinstance(dims_in, dict) else None) for k in SCORE_DIM_KEYS}
    # 若调用方没给维分，用启发式（Mock / 兜底）
    if all(dims[k] == 5 for k in SCORE_DIM_KEYS) and not any(
        isinstance(dims_in, dict) and dims_in.get(k) is not None for k in SCORE_DIM_KEYS
    ):
        dims = _heuristic_dims(answer)

    overall = raw.get("score")
    if overall is None:
        overall = sum(dims[k] * SCORE_DIM_WEIGHTS[k] for k in SCORE_DIM_KEYS) * 10
    try:
        score = max(0, min(100, int(round(float(overall)))))
    except (TypeError, ValueError):
        score = int(round(sum(dims[k] * SCORE_DIM_WEIGHTS[k] for k in SCORE_DIM_KEYS) * 10))

    hints = raw.get("scoreHints") or raw.get("score_hints") or []
    if isinstance(hints, str):
        hints = [hints] if hints.strip() else []
    hints = [str(h).strip() for h in hints if str(h).strip()][:4]
    return {"score": score, "scoreDims": dims, "scoreHints": hints}


def _heuristic_dims(answer: str) -> Dict[str, int]:
    a = (answer or "").strip()
    length = len(a)
    has_digit = bool(re.search(r"\d", a))
    has_star = bool(re.search(r"背景|当时|负责|我|因此|结果|导致", a))
    vague = bool(re.search(r"差不多|可能|大概|忘了|不太清楚", a))

    accuracy = 6 + (2 if has_digit else 0) - (2 if vague else 0)
    depth = 4 + (2 if length > 80 else 0) + (2 if length > 160 else 0) + (1 if has_digit else 0)
    logic = 5 + (2 if has_star else 0) + (1 if "因此" in a or "所以" in a else 0)
    expression = 5 + (1 if 40 <= length <= 400 else 0) - (2 if length < 30 else 0) - (1 if vague else 0)
    return {
        "accuracy": _clamp_dim(accuracy),
        "depth": _clamp_dim(depth),
        "logic": _clamp_dim(logic),
        "expression": _clamp_dim(expression),
    }


class BaseLLM:
    async def first_question(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def feedback(self, experience: Dict[str, Any], node: Dict[str, Any], answer: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def next_question(
        self,
        experience: Dict[str, Any],
        from_node: Dict[str, Any],
        action: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def extract_interview_qa(self, transcript: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def analyze_interview_qa(self, item: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def draft_answer(self, experience: Dict[str, Any], node: Dict[str, Any], mode: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def compare_review(
        self, experience: Dict[str, Any], question: str, old_answer: str, new_answer: str
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def match_jd(self, jd_text: str, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    async def parse_resume_experiences(self, resume_text: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def session_first_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def session_next_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
        from_node: Dict[str, Any],
        action: str,
        asked_titles: List[str],
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def consolidate_qa_nodes(
        self, experience: Dict[str, Any], nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def intro_generate(
        self, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def intro_polish(
        self, content: str, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def intro_guide(
        self,
        content: str,
        guide_answers: List[str],
        experiences: List[Dict[str, Any]],
        target_role: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError


def _question_similarity(a: str, b: str) -> bool:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return False
    if a[:10] == b[:10]:
        return True
    words_a = set(re.findall(r"[\u4e00-\u9fff]{2,}", a))
    words_b = set(re.findall(r"[\u4e00-\u9fff]{2,}", b))
    return len(words_a & words_b) >= 2


def _mock_consolidate_nodes(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    groups: List[Dict[str, Any]] = []
    used: set[str] = set()
    for i, n in enumerate(nodes):
        nid = n.get("nodeId") or ""
        if nid in used:
            continue
        cluster = [n]
        q1 = n.get("question") or ""
        for m in nodes[i + 1 :]:
            mid = m.get("nodeId") or ""
            if mid in used:
                continue
            if _question_similarity(q1, m.get("question") or ""):
                cluster.append(m)
                used.add(mid)
        if len(cluster) >= 2:
            best = max(cluster, key=lambda x: len(x.get("answer") or ""))
            groups.append(
                {
                    "id": f"g_{len(groups) + 1}",
                    "node_ids": [x.get("nodeId") for x in cluster if x.get("nodeId")],
                    "canonical_question": best.get("question") or q1,
                    "merged_answer": best.get("answer") or "",
                    "reason": "问题表述相近，建议合并为一道精练题",
                }
            )
            for x in cluster:
                used.add(x.get("nodeId") or "")
        else:
            used.add(nid)
    summary = (
        f"共 {len(nodes)} 道题，发现 {len(groups)} 组相似题可合并"
        if groups
        else f"共 {len(nodes)} 道题，未发现明显重复"
    )
    return {"summary": summary, "groups": groups}


def _intro_brief(experiences: List[Dict[str, Any]]) -> str:
    if not experiences:
        return "（用户尚未填写经历，请结合常见产品实习背景组织）"
    lines = []
    for e in experiences[:4]:
        lines.append(
            f"- {e.get('title') or e.get('company')} / {e.get('role') or ''}\n"
            f"  {e.get('summary') or ''}\n"
            f"  成果：{e.get('metrics') or '待补充'}"
        )
    return "\n".join(lines)


def _mock_intro_generate(experiences: List[Dict[str, Any]], target_role: str) -> Dict[str, Any]:
    role = (target_role or "产品").strip()
    parts = [f"您好，我是 CHEN，目前求职方向是{role}。"]
    for e in experiences[:2]:
        title = e.get("title") or e.get("company") or "一段经历"
        metric = e.get("metrics") or "取得了可量化的业务结果"
        parts.append(f"在「{title}」中，我主要负责{e.get('role') or '核心模块'}，{metric}。")
    parts.append("我习惯用数据驱动决策，也具备跨团队协作推进落地的经验。以上是我的简要介绍，谢谢。")
    return {"content": "".join(parts)}


def _mock_intro_polish(content: str, experiences: List[Dict[str, Any]], target_role: str) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        return _mock_intro_generate(experiences, target_role)
    # 简单压缩空行、补口述节奏
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    polished = " ".join(lines)
    if experiences and experiences[0].get("metrics") and experiences[0]["metrics"] not in polished:
        polished += f" 其中代表性成果包括 {experiences[0]['metrics']}。"
    return {"content": polished}


GUIDE_QUESTIONS = [
    "你最想突出的 1 个能力是什么？",
    "哪段经历最能体现你和别人的不同？",
    "你期望的目标岗位是什么方向？",
]


def _mock_intro_guide(
    content: str,
    guide_answers: List[str],
    experiences: List[Dict[str, Any]],
    target_role: str,
) -> Dict[str, Any]:
    step = len(guide_answers or [])
    if step < len(GUIDE_QUESTIONS):
        return {"content": "", "hint": GUIDE_QUESTIONS[step]}
    role = (guide_answers[2] if len(guide_answers) > 2 else target_role) or "产品"
    ability = guide_answers[0] if guide_answers else "数据驱动"
    diff = guide_answers[1] if len(guide_answers) > 1 else "一段项目经历"
    base = _mock_intro_generate(experiences, role)["content"]
    extra = f"我想特别强调：{ability}；{diff}。"
    return {"content": base + extra, "hint": ""}


def _brief_exps(experiences: List[Dict[str, Any]]) -> str:
    parts = []
    for i, e in enumerate(experiences, start=1):
        parts.append(
            f"[{i}] id={e.get('id')} 标题={e.get('title') or e.get('company')}\n"
            f"角色={e.get('role')} 时间={e.get('period')}\n"
            f"内容={e.get('summary')}\n成果={e.get('metrics')}\n补充={e.get('extra')}"
        )
    return "\n---\n".join(parts) if parts else "（无经历）"


def _pick_uncovered(experiences: List[Dict[str, Any]], asked_titles: List[str]) -> Optional[Dict[str, Any]]:
    asked = set(t for t in (asked_titles or []) if t)
    for e in experiences:
        title = e.get("title") or e.get("company") or ""
        if title and title not in asked:
            return e
    return experiences[0] if experiences else None


def _normalize_parsed_card(raw: Dict[str, Any]) -> Dict[str, Any]:
    company = (raw.get("company") or raw.get("title") or "").strip() or "未命名经历"
    role = (raw.get("role") or "").strip() or "待补充角色"
    period = (raw.get("period") or "").strip() or "待补充时间"
    summary = (raw.get("summary") or "").strip() or "待补充工作内容"
    metrics = (raw.get("metrics") or "").strip()
    exp_type = (raw.get("type") or "实习").strip()
    if exp_type not in ("实习", "项目", "校园", "其他"):
        exp_type = "实习"
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[,，]", tags) if t.strip()]
    tags = [str(t).strip() for t in tags if str(t).strip()][:8]
    tags = normalize_exp_tags(tags)
    missing = (raw.get("missing_hint") or raw.get("missingHint") or "").strip()
    if not metrics and not missing:
        missing = "这段建议补充量化结果，面试容易被追问"
    title = (raw.get("title") or "").strip() or f"{company} · {role}"
    return {
        "type": exp_type,
        "company": company[:120],
        "role": role[:80],
        "period": period[:80],
        "summary": summary[:2000],
        "metrics": metrics[:500],
        "extra": (raw.get("extra") or "").strip()[:1000],
        "tags": tags,
        "title": title[:160],
        "missing_hint": missing[:200],
    }


def _mock_parse_resume(text: str) -> List[Dict[str, Any]]:
    """无 Key 时：按段落粗切 + 兜底演示卡。"""
    chunks = [c.strip() for c in re.split(r"\n{2,}", text or "") if len(c.strip()) >= 20]
    items: List[Dict[str, Any]] = []
    for chunk in chunks[:6]:
        first = chunk.split("\n", 1)[0][:40]
        has_digit = bool(re.search(r"\d", chunk))
        items.append(
            _normalize_parsed_card(
                {
                    "type": "实习" if re.search(r"实习|公司", chunk) else "项目",
                    "company": first,
                    "role": "待确认角色",
                    "period": "待确认时间",
                    "summary": chunk[:400],
                    "metrics": "" if not has_digit else "（请从正文核对数字）",
                    "tags": ["待确认"],
                    "missing_hint": "" if has_digit else "这段建议补充量化结果，面试容易被追问",
                }
            )
        )
    if items:
        return items
    return [
        _normalize_parsed_card(
            {
                "type": "实习",
                "company": "（Mock）请上传含实习/项目段落的简历",
                "role": "产品实习生",
                "period": "2024.06 - 2024.09",
                "summary": (text or "简历正文过短，未能拆出经历；配置 LLM 后效果更好。")[:300],
                "metrics": "",
                "tags": ["待确认"],
            }
        )
    ]


def _mock_extract(transcript: str) -> List[Dict[str, Any]]:
    """从转写文本粗提取问答；识别失败时给演示条目。"""
    items: List[Dict[str, Any]] = []
    # 支持：面试官：/候选人： 或 Q:/A: 或 问：/答：
    pattern = re.compile(
        r"(?:面试官|面试官问|HR|Q|问)[:：\s]*(.+?)(?:\n+)(?:候选人|我|答|A)[:：\s]*(.+?)(?=(?:\n+(?:面试官|面试官问|HR|Q|问)[:：])|\Z)",
        re.S | re.I,
    )
    for i, m in enumerate(pattern.finditer(transcript or ""), start=1):
        q, a = m.group(1).strip(), m.group(2).strip()
        if len(q) < 4:
            continue
        items.append(
            {
                "id": f"di_{i}",
                "question": q[:500],
                "answer": a[:2000],
                "quality": "pending",
                "analysis": "",
                "optimized_answer": "",
                "tags": guess_tags(q),
            }
        )
    if items:
        return items[:12]

    # 兜底：按空行切几段，或返回演示数据
    chunks = [c.strip() for c in re.split(r"\n{2,}", transcript or "") if c.strip()]
    if len(chunks) >= 2:
        for i in range(0, min(len(chunks) - 1, 6), 2):
            items.append(
                {
                    "id": f"di_{len(items)+1}",
                    "question": chunks[i][:500],
                    "answer": chunks[i + 1][:2000],
                    "quality": "pending",
                    "analysis": "",
                    "optimized_answer": "",
                    "tags": guess_tags(chunks[i]),
                }
            )
        if items:
            return items

    return [
        {
            "id": "di_1",
            "question": "请做一下自我介绍，并突出和本岗位相关的经历。",
            "answer": (transcript or "（转写文本较短，未能自动切分；这是占位问答，请替换为真实转写）")[:400],
            "quality": "pending",
            "analysis": "",
            "optimized_answer": "",
            "tags": ["行为面试", "项目介绍"],
        },
        {
            "id": "di_2",
            "question": "项目里你负责的最难的技术/业务问题是什么？怎么解决的？",
            "answer": "当时主要靠查文档和问同事，最后差不多解决了。",
            "quality": "pending",
            "analysis": "",
            "optimized_answer": "",
            "tags": ["技术"],
        },
    ]


def _mock_analyze(item: Dict[str, Any]) -> Dict[str, Any]:
    answer = (item.get("answer") or "").strip()
    question = item.get("question") or ""
    weak_reasons = []
    if len(answer) < 40:
        weak_reasons.append("回答过短，信息密度不足")
    if not re.search(r"\d", answer):
        weak_reasons.append("缺少量化结果")
    if not re.search(r"我|我们|负责|做成|导致|因此", answer):
        weak_reasons.append("主体行动不清晰，STAR 不完整")
    if re.search(r"差不多|可能|大概|忘了|不太清楚", answer):
        weak_reasons.append("表达犹豫，暴露准备不足")

    scored = normalize_score_block(answer=answer)
    if weak_reasons:
        return {
            "quality": "weak",
            "analysis": "；".join(weak_reasons) + "。建议按 STAR 重述，并补 1～2 个数字。",
            "optimized_answer": (
                f"针对「{question[:40]}」可以这样答：\n"
                f"背景：先用一句话交代场景与目标。\n"
                f"任务：明确你的职责边界。\n"
                f"行动：列出 2～3 个关键动作（原回答可保留：{answer[:80]}…）。\n"
                f"结果：补上可验证的量化结果与复盘一句话。"
            ),
            "tags": item.get("tags") or guess_tags(question),
            **scored,
        }
    return {
        "quality": "good",
        "analysis": "结构较完整，有一定信息量；可再压一版更短的口述稿方便临场发挥。",
        "optimized_answer": answer,
        "tags": item.get("tags") or guess_tags(question),
        **scored,
    }


class MockLLM(BaseLLM):
    async def first_question(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        title = experience.get("title") or experience.get("company") or "这段经历"
        q = f"请介绍一下「{title}」里你负责的部分，以及最终取得了什么成果？"
        tags = ["行为面试", "项目介绍"]
        return {"question": q, "knowledgeTags": tags, "labels": [tags[0]]}

    async def feedback(self, experience: Dict[str, Any], node: Dict[str, Any], answer: str) -> Dict[str, Any]:
        tags = guess_tags(node.get("question", ""))
        scored = normalize_score_block(answer=answer)
        has_digit = bool(re.search(r"\d", answer or ""))
        if has_digit:
            fb = "结构较清晰，已有量化信息；可再补「为什么这么做」的决策过程。"
        else:
            fb = "结构清晰，建议补充 1 个量化数据支撑结论。"
        if scored["score"] < 60:
            fb += " 当前综合分偏低，建议先补 STAR 里最弱的一环。"
        return {
            "aiFeedback": fb,
            "knowledgeTags": tags,
            "labels": [tags[0]],
            **scored,
        }

    async def next_question(
        self,
        experience: Dict[str, Any],
        from_node: Dict[str, Any],
        action: str,
    ) -> Dict[str, Any]:
        bank = {
            "deep_dive": "如果当时的关键决策选错了，你会怎么发现并纠正？",
            "new_angle": "从团队协作角度看，这个项目里你最大的收获是什么？",
            "diverge": "你刚才回答里提到的一个关键点，能展开讲讲具体怎么落地的吗？",
        }
        q = bank.get(action, bank["deep_dive"])
        tags = guess_tags(q)
        trigger = None
        if action == "diverge":
            trigger = "从上一轮回答中识别到的关键词"
        return {
            "question": q,
            "knowledgeTags": tags,
            "labels": [tags[0]],
            "triggerFrom": trigger,
        }

    async def extract_interview_qa(self, transcript: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        return _mock_extract(transcript)

    async def analyze_interview_qa(self, item: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return _mock_analyze(item)

    async def draft_answer(self, experience: Dict[str, Any], node: Dict[str, Any], mode: str) -> Dict[str, Any]:
        title = experience.get("title") or "该项目"
        q = node.get("question") or ""
        metrics = experience.get("metrics") or "可补充量化结果"
        if mode == "framework_only":
            return {
                "draft": (
                    "【答题框架】请按 STAR 填写，紧扣本题：\n"
                    f"问题：{q}\n"
                    "1. 背景：当时的目标/约束是什么？\n"
                    "2. 任务：你具体负责哪一块？\n"
                    "3. 行动：2～3 个关键动作（含协作对象）\n"
                    "4. 结果：数字 + 若做错会如何发现\n"
                    "5. 复盘：下次会改哪一步？"
                )
            }
        return {
            "draft": (
                f"针对「{q}」：在「{title}」里，我会先对照目标指标做复盘。"
                f"若结果偏离（例如 {metrics} 未达成），会拆漏斗定位环节，对齐相关团队后调整方案并跟踪一周数据。"
                "发现机制靠周报异常阈值，纠正靠缩小范围做对照实验。"
            )
        }

    async def compare_review(
        self, experience: Dict[str, Any], question: str, old_answer: str, new_answer: str
    ) -> Dict[str, Any]:
        longer = len(new_answer or "") > len(old_answer or "")
        has_digit = bool(re.search(r"\d", new_answer or ""))
        progress = []
        if longer:
            progress.append("信息量比上次更足")
        if has_digit:
            progress.append("补上了量化信息")
        if not progress:
            progress.append("结构有调整，但信息量提升不明显")
        weak = []
        if not has_digit:
            weak.append("仍缺少可验证的数字")
        if len(new_answer or "") < 40:
            weak.append("仍然过短，建议补 STAR 中的行动细节")
        return {
            "progress": "；".join(progress) + "。",
            "still_weak": "；".join(weak) + "。" if weak else "本次已明显好于上次。",
        }

    async def match_jd(self, jd_text: str, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        titles = [e.get("title") or e.get("company") or "经历" for e in experiences] or ["（暂无经历）"]
        return {
            "score": 70,
            "matches": [{"exp": titles[0], "point": "（Mock）与 JD 中的核心职责有部分重合，请接真模型获得具体分析"}],
            "gaps": [{"skill": "需对照 JD 细项", "tip": "当前为 Mock 报告；配置 LLM_API_KEY 后会按你的经历逐条匹配"}],
            "actions": [{"type": "练经历", "text": f"优先用模拟面试深挖「{titles[0]}」"}],
        }

    async def parse_resume_experiences(self, resume_text: str) -> List[Dict[str, Any]]:
        return _mock_parse_resume(resume_text)

    async def session_first_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
    ) -> Dict[str, Any]:
        e = experiences[0] if experiences else {}
        title = e.get("title") or e.get("company") or "这段经历"
        role = target_role or "目标岗位"
        q = (
            f"请先结合「{role}」做个简短自我介绍，并重点讲讲「{title}」里你负责的部分与结果。"
            if not (jd_text or "").strip()
            else f"对照岗位「{role}」，请介绍「{title}」里和 JD 最相关的一段工作与量化结果。"
        )
        return {
            "question": q,
            "knowledgeTags": ["行为面试", "项目介绍"],
            "labels": ["行为面试"],
            "targetExpId": e.get("id"),
            "targetExpTitle": title,
        }

    async def session_next_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
        from_node: Dict[str, Any],
        action: str,
        asked_titles: List[str],
    ) -> Dict[str, Any]:
        if action == "cover_next":
            e = _pick_uncovered(experiences, asked_titles) or {}
            title = e.get("title") or e.get("company") or "下一段经历"
            q = f"接下来请介绍「{title}」：你负责什么、怎么做的、结果如何？（岗位：{target_role or '通用'}）"
            return {
                "question": q,
                "knowledgeTags": ["行为面试", "项目介绍"],
                "labels": ["行为面试"],
                "targetExpId": e.get("id"),
                "targetExpTitle": title,
                "triggerFrom": None,
            }
        # 深挖/换角度/发散：沿用单经历文案，但锚定当前节点的 target
        bank = {
            "deep_dive": "如果当时的关键决策选错了，你会怎么发现并纠正？",
            "new_angle": "从团队协作角度看，这个项目里你最大的收获是什么？",
            "diverge": "你刚才回答里提到的一个关键点，能展开讲讲具体怎么落地的吗？",
        }
        q = bank.get(action, bank["deep_dive"])
        return {
            "question": q,
            "knowledgeTags": guess_tags(q),
            "labels": [guess_tags(q)[0]],
            "targetExpId": from_node.get("targetExpId"),
            "targetExpTitle": from_node.get("targetExpTitle"),
            "triggerFrom": "从上一轮回答中识别到的关键词" if action == "diverge" else None,
        }

    async def consolidate_qa_nodes(
        self, experience: Dict[str, Any], nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return _mock_consolidate_nodes(nodes)

    async def intro_generate(
        self, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        return _mock_intro_generate(experiences, target_role)

    async def intro_polish(
        self, content: str, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        return _mock_intro_polish(content, experiences, target_role)

    async def intro_guide(
        self,
        content: str,
        guide_answers: List[str],
        experiences: List[Dict[str, Any]],
        target_role: str,
    ) -> Dict[str, Any]:
        return _mock_intro_guide(content, guide_answers, experiences, target_role)


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 Chat Completions（也可用国内兼容网关改 base_url）。"""

    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    async def _chat_json(self, system: str, user: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _exp_brief(self, experience: Dict[str, Any]) -> str:
        return (
            f"经历：{experience.get('title')}\n"
            f"角色：{experience.get('role')}\n"
            f"时间：{experience.get('period')}\n"
            f"内容：{experience.get('summary')}\n"
            f"成果：{experience.get('metrics')}\n"
            f"补充：{experience.get('extra')}"
        )

    async def first_question(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "你是中文模拟面试官。只输出 JSON："
            '{"question":"...","knowledgeTags":["一级","二级"],"labels":["一级"]}。'
            f"一级标签必须来自：{L1_TAGS}。"
        )
        user = self._exp_brief(experience) + "\n请提出第一个项目介绍类问题。"
        try:
            return await self._chat_json(system, user)
        except Exception:
            return await MockLLM().first_question(experience)

    async def feedback(self, experience: Dict[str, Any], node: Dict[str, Any], answer: str) -> Dict[str, Any]:
        system = (
            "你是中文面试辅导。只输出 JSON："
            '{"aiFeedback":"一两句点评","knowledgeTags":["一级","二级"],"labels":["一级"],'
            '"scoreDims":{"accuracy":0到10,"depth":0到10,"logic":0到10,"expression":0到10},'
            '"scoreHints":["可选，最多2条短提示"]}。'
            f"一级标签必须来自：{L1_TAGS}。"
            "四维含义：准确性(事实/量化)、深度(细节与决策)、逻辑(STAR连贯)、表达(清晰简洁)。"
            "分数仅供参考，不要建议系统自动追问。点评关注 STAR/量化/风险点，不要长篇大论。"
        )
        user = (
            self._exp_brief(experience)
            + f"\n问题：{node.get('question')}\n回答：{answer}\n请点评、打标签并打四维分。"
        )
        try:
            data = await self._chat_json(system, user)
            scored = normalize_score_block(data, answer=answer)
            return {
                "aiFeedback": data.get("aiFeedback") or "",
                "knowledgeTags": data.get("knowledgeTags") or guess_tags(node.get("question") or ""),
                "labels": data.get("labels") or [],
                **scored,
            }
        except Exception:
            return await MockLLM().feedback(experience, node, answer)

    async def next_question(
        self,
        experience: Dict[str, Any],
        from_node: Dict[str, Any],
        action: str,
    ) -> Dict[str, Any]:
        action_hint = {
            "deep_dive": "针对同一问题深挖细节或压力追问",
            "new_angle": "换角度问同一项目（协作/失败/替代方案等）",
            "diverge": "抓住上一答中的一个词发散追问，并填写 triggerFrom",
        }.get(action, "继续追问")
        system = (
            "你是中文模拟面试官。只输出 JSON："
            '{"question":"...","knowledgeTags":["一级","二级"],"labels":["一级"],"triggerFrom":null或字符串}。'
            f"一级标签必须来自：{L1_TAGS}。"
        )
        user = (
            self._exp_brief(experience)
            + f"\n上一问：{from_node.get('question')}\n上一答：{from_node.get('answer')}\n"
            + f"用户选择：{action}（{action_hint}）\n请生成下一问。"
        )
        try:
            return await self._chat_json(system, user)
        except Exception:
            return await MockLLM().next_question(experience, from_node, action)

    async def extract_interview_qa(self, transcript: str, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        system = (
            "你是面试复盘助手。从中文面试转写文本中提取关键问答。"
            '只输出 JSON：{"items":[{"question":"...","answer":"...","tags":["一级","二级"]}]}。'
            f"一级标签必须来自：{L1_TAGS}。最多 12 条，跳过寒暄。"
        )
        user = (
            f"公司：{meta.get('company')} 岗位：{meta.get('role')}\n"
            f"转写文本：\n{transcript[: settings.llm_transcript_max_chars]}"
        )
        try:
            data = await self._chat_json(system, user)
            raw = data.get("items") or []
            out = []
            for i, it in enumerate(raw, start=1):
                out.append(
                    {
                        "id": f"di_{i}",
                        "question": it.get("question") or "",
                        "answer": it.get("answer") or "",
                        "quality": "pending",
                        "analysis": "",
                        "optimized_answer": "",
                        "tags": it.get("tags") or guess_tags(it.get("question") or ""),
                    }
                )
            return out or await MockLLM().extract_interview_qa(transcript, meta)
        except Exception:
            return await MockLLM().extract_interview_qa(transcript, meta)

    async def analyze_interview_qa(self, item: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "你是中文面试辅导。评估候选人当场回答质量。"
            '只输出 JSON：{"quality":"good|weak","analysis":"点评","optimized_answer":"优化答法",'
            '"tags":["一级","二级"],'
            '"scoreDims":{"accuracy":0到10,"depth":0到10,"logic":0到10,"expression":0到10},'
            '"scoreHints":["可选短提示"]}。'
            f"一级标签必须来自：{L1_TAGS}。弱答（缺量化/STAR不清/含糊）必须 quality=weak。"
            "四维：准确性/深度/逻辑/表达。分数仅参考，不决定流程。"
        )
        user = (
            f"公司：{meta.get('company')} 岗位：{meta.get('role')}\n"
            f"问题：{item.get('question')}\n回答：{item.get('answer')}"
        )
        try:
            data = await self._chat_json(system, user)
            q = data.get("quality") or "weak"
            if q not in ("good", "weak"):
                q = "weak"
            scored = normalize_score_block(data, answer=item.get("answer") or "")
            return {
                "quality": q,
                "analysis": data.get("analysis") or "",
                "optimized_answer": data.get("optimized_answer") or "",
                "tags": data.get("tags") or guess_tags(item.get("question") or ""),
                **scored,
            }
        except Exception:
            return await MockLLM().analyze_interview_qa(item, meta)

    async def draft_answer(self, experience: Dict[str, Any], node: Dict[str, Any], mode: str) -> Dict[str, Any]:
        q = node.get("question") or ""
        if mode == "framework_only":
            system = (
                "你是中文面试教练。只输出 JSON：{\"draft\":\"答题框架文本\"}。"
                "给 STAR 框架，必须紧扣本题，列出要填的要点，不要直接写成完整答案。"
            )
            user = self._exp_brief(experience) + f"\n面试题：{q}\n请给出填写框架。"
        else:
            system = (
                "你是中文面试候选人。只输出 JSON：{\"draft\":\"完整口述答案\"}。"
                "用第一人称，STAR 结构，紧扣本题（协作/纠错/指标等都要答到题上），"
                "结合经历里的真实信息，不要套无关的 DAU 模板。150～250 字。"
            )
            user = self._exp_brief(experience) + f"\n面试题：{q}\n请写一版可直接口述的参考答案。"
        try:
            data = await self._chat_json(system, user)
            draft = (data.get("draft") or "").strip()
            if draft:
                return {"draft": draft}
        except Exception:
            pass
        return await MockLLM().draft_answer(experience, node, mode)

    async def compare_review(
        self, experience: Dict[str, Any], question: str, old_answer: str, new_answer: str
    ) -> Dict[str, Any]:
        system = (
            "你是中文面试辅导。对比同一题的两次回答。只输出 JSON："
            '{"progress":"比上次进步在哪（一两句）","still_weak":"仍可改进（一两句）"}。'
            "要具体，不要空话。"
        )
        user = (
            self._exp_brief(experience)
            + f"\n问题：{question}\n上次回答：{old_answer or '（无）'}\n本次回答：{new_answer or '（无）'}"
        )
        try:
            data = await self._chat_json(system, user)
            return {
                "progress": data.get("progress") or "",
                "still_weak": data.get("still_weak") or "",
            }
        except Exception:
            return await MockLLM().compare_review(experience, question, old_answer, new_answer)

    async def match_jd(self, jd_text: str, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        briefs = "\n---\n".join(
            f"{e.get('title')} | {e.get('role')} | {e.get('period')}\n{e.get('summary')}\n成果：{e.get('metrics')}"
            for e in experiences
        ) or "（用户尚未填写经历）"
        system = (
            "你是中文求职顾问。对照 JD 与候选人经历做匹配。只输出 JSON："
            '{"score":0到100整数,"matches":[{"exp":"经历标题","point":"匹配说明"}],'
            '"gaps":[{"skill":"缺口","tip":"怎么补"}],'
            '"actions":[{"type":"练经历或补知识或追问风格","text":"具体行动"}]}。'
            "matches/gaps/actions 各 2～4 条。score 要有依据。"
        )
        user = f"JD：\n{jd_text[:6000]}\n\n经历：\n{briefs[:6000]}"
        try:
            data = await self._chat_json(system, user)
            score = data.get("score") or 0
            try:
                score = max(0, min(100, int(score)))
            except (TypeError, ValueError):
                score = 60
            return {
                "score": score,
                "matches": data.get("matches") or [],
                "gaps": data.get("gaps") or [],
                "actions": data.get("actions") or [],
            }
        except Exception:
            return await MockLLM().match_jd(jd_text, experiences)

    async def parse_resume_experiences(self, resume_text: str) -> List[Dict[str, Any]]:
        system = (
            "你是中文简历解析助手。从简历正文中只提取「实习 / 项目 / 校园经历」卡片，"
            "忽略教育背景、求职意向、技能列表、证书（除非本身是一段可面试的项目）。"
            "只输出 JSON："
            '{"items":[{"type":"实习|项目|校园|其他","company":"公司或项目名","role":"角色",'
            '"period":"时间段","summary":"主要工作（2～5句）","metrics":"量化结果，没有则空串",'
            '"extra":"","tags":["标签"],"title":"可选短标题","missing_hint":"缺数字时给一句提示，否则空串"}]}。'
            "最多 8 条；不要编造简历里没有的公司或成果；字段尽量填满。"
        )
        user = f"简历正文：\n{resume_text[: settings.llm_resume_max_chars]}"
        try:
            data = await self._chat_json(system, user)
            raw = data.get("items") or []
            out = [_normalize_parsed_card(it) for it in raw if isinstance(it, dict)]
            out = [x for x in out if x.get("summary")]
            return out or await MockLLM().parse_resume_experiences(resume_text)
        except Exception:
            return await MockLLM().parse_resume_experiences(resume_text)

    async def session_first_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
    ) -> Dict[str, Any]:
        system = (
            "你是中文面试官。候选人提交了多段简历经历，并可能附带目标岗位与 JD。"
            "第一问必须紧扣投递材料，优先覆盖简历上最相关的一段经历。"
            "只输出 JSON："
            '{"question":"...","knowledgeTags":["一级","二级"],"labels":["一级"],'
            '"targetExpId":"经历id","targetExpTitle":"经历标题"}。'
            f"一级标签必须来自：{L1_TAGS}。targetExpId 必须来自给定经历列表。"
        )
        user = (
            f"目标岗位：{target_role or '未填'}\nJD：\n{(jd_text or '（未提供）')[:4000]}\n\n"
            f"简历经历：\n{_brief_exps(experiences)}\n\n请提出第一问。"
        )
        try:
            data = await self._chat_json(system, user)
            ids = {e.get("id") for e in experiences}
            tid = data.get("targetExpId")
            if tid not in ids and experiences:
                data["targetExpId"] = experiences[0].get("id")
                data["targetExpTitle"] = experiences[0].get("title") or experiences[0].get("company")
            return data
        except Exception:
            return await MockLLM().session_first_question(experiences, target_role, jd_text)

    async def session_next_question(
        self,
        experiences: List[Dict[str, Any]],
        target_role: str,
        jd_text: str,
        from_node: Dict[str, Any],
        action: str,
        asked_titles: List[str],
    ) -> Dict[str, Any]:
        action_hint = {
            "deep_dive": "针对同一问题深挖细节或压力追问，target 保持当前经历",
            "new_angle": "换角度问同一项目，target 保持当前经历",
            "diverge": "抓住上一答中的词发散，target 保持当前经历，可填 triggerFrom",
            "cover_next": "换到简历上尚未覆盖的经历提问；若都覆盖了则深挖 JD 缺口或最弱一段",
        }.get(action, "继续提问")
        system = (
            "你是中文面试官。目标：尽量把候选人提交的每段简历经历都问到，并紧扣岗位/JD。"
            "只输出 JSON："
            '{"question":"...","knowledgeTags":["一级","二级"],"labels":["一级"],'
            '"targetExpId":"经历id","targetExpTitle":"经历标题","triggerFrom":null或字符串}。'
            f"一级标签必须来自：{L1_TAGS}。"
        )
        user = (
            f"目标岗位：{target_role or '未填'}\nJD：\n{(jd_text or '（未提供）')[:3000]}\n\n"
            f"简历经历：\n{_brief_exps(experiences)}\n\n"
            f"已覆盖经历标题：{asked_titles or ['（无）']}\n"
            f"上一问：{from_node.get('question')}\n上一答：{from_node.get('answer')}\n"
            f"上一问锚定经历：{from_node.get('targetExpTitle')}\n"
            f"用户选择：{action}（{action_hint}）\n请生成下一问。"
        )
        try:
            data = await self._chat_json(system, user)
            ids = {e.get("id") for e in experiences}
            if data.get("targetExpId") not in ids and experiences:
                fallback = _pick_uncovered(experiences, asked_titles) or experiences[0]
                data["targetExpId"] = fallback.get("id")
                data["targetExpTitle"] = fallback.get("title") or fallback.get("company")
            return data
        except Exception:
            return await MockLLM().session_next_question(
                experiences, target_role, jd_text, from_node, action, asked_titles
            )

    async def consolidate_qa_nodes(
        self, experience: Dict[str, Any], nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if len(nodes) < 2:
            return {"summary": "节点太少，无需归纳", "groups": []}
        brief = "\n".join(
            f"- {n.get('nodeId')}: {n.get('question') or ''} | 答：{(n.get('answer') or '')[:120]}"
            for n in nodes
        )
        system = (
            "你是中文面试辅导。用户经历里有多道相似但不完全重复的面试题，请归纳合并。"
            '只输出 JSON：{"summary":"一两句总结","groups":[{"id":"g1","node_ids":["q1","q2"],'
            '"canonical_question":"合并后的标准问法","merged_answer":"综合多答后的精炼版",'
            '"reason":"为何可合并"}]}。'
            "只合并语义明显相近的题（如同一 STAR 点的不同问法）；不要硬合无关题。"
            "node_ids 必须来自输入列表。"
        )
        user = (
            f"经历：{experience.get('title')}\n"
            f"问答列表：\n{brief}\n"
            "请找出可合并的相似题组。"
        )
        try:
            data = await self._chat_json(system, user)
            groups = data.get("groups") or []
            valid_ids = {n.get("nodeId") for n in nodes}
            cleaned = []
            for i, g in enumerate(groups):
                ids = [x for x in (g.get("node_ids") or []) if x in valid_ids]
                if len(ids) < 2:
                    continue
                cleaned.append(
                    {
                        "id": g.get("id") or f"g_{i + 1}",
                        "node_ids": ids,
                        "canonical_question": (g.get("canonical_question") or "").strip() or nodes[0].get("question", ""),
                        "merged_answer": (g.get("merged_answer") or "").strip(),
                        "reason": (g.get("reason") or "").strip(),
                    }
                )
            return {
                "summary": (data.get("summary") or "").strip() or f"发现 {len(cleaned)} 组可合并",
                "groups": cleaned,
            }
        except Exception:
            return await MockLLM().consolidate_qa_nodes(experience, nodes)

    async def intro_generate(
        self, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        system = (
            "你是中文求职辅导。根据候选人经历写 1 分钟自我介绍口述稿。"
            '只输出 JSON：{"content":"完整自我介绍文本"}。'
            "要求：第一人称、60～120 秒可读完、先总后分、至少 1 个量化成果、"
            "紧扣目标岗位，不要编造经历里没有的数字。"
        )
        user = f"目标岗位：{target_role or '未指定'}\n经历：\n{_intro_brief(experiences)}"
        try:
            data = await self._chat_json(system, user)
            content = (data.get("content") or "").strip()
            if content:
                return {"content": content}
        except Exception:
            pass
        return await MockLLM().intro_generate(experiences, target_role)

    async def intro_polish(
        self, content: str, experiences: List[Dict[str, Any]], target_role: str
    ) -> Dict[str, Any]:
        system = (
            "你是中文求职辅导。润色自我介绍口述稿。"
            '只输出 JSON：{"content":"润色后全文"}。'
            "保留事实，优化节奏与亮点排序，适合 1 分钟口述，不要加长超过 30%。"
        )
        user = (
            f"目标岗位：{target_role or '未指定'}\n"
            f"经历参考：\n{_intro_brief(experiences)}\n\n"
            f"待润色文稿：\n{content or '（空）'}"
        )
        try:
            data = await self._chat_json(system, user)
            content = (data.get("content") or "").strip()
            if content:
                return {"content": content}
        except Exception:
            pass
        return await MockLLM().intro_polish(content, experiences, target_role)

    async def intro_guide(
        self,
        content: str,
        guide_answers: List[str],
        experiences: List[Dict[str, Any]],
        target_role: str,
    ) -> Dict[str, Any]:
        step = len(guide_answers or [])
        if step < len(GUIDE_QUESTIONS):
            return {"content": "", "hint": GUIDE_QUESTIONS[step]}
        system = (
            "你是中文求职辅导。根据引导问答与经历，组织 1 分钟自我介绍。"
            '只输出 JSON：{"content":"完整自我介绍"}。'
            "融合用户三个回答的要点，结合经历中的真实信息。"
        )
        user = (
            f"目标岗位：{target_role or '未指定'}\n"
            f"经历：\n{_intro_brief(experiences)}\n"
            f"用户已有草稿：{content or '（无）'}\n"
            f"引导回答：\n"
            + "\n".join(f"{i+1}. {a}" for i, a in enumerate(guide_answers))
        )
        try:
            data = await self._chat_json(system, user)
            content = (data.get("content") or "").strip()
            if content:
                return {"content": content, "hint": ""}
        except Exception:
            pass
        return await MockLLM().intro_guide(content, guide_answers, experiences, target_role)


def get_llm() -> BaseLLM:
    if settings.llm_provider == "openai" and settings.llm_api_key:
        return OpenAILLM()
    return MockLLM()
