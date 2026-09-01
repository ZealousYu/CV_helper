from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


L1_TAGS = ["行为面试", "技术", "业务理解", "协作沟通", "职业规划"]


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
        }
    return {
        "quality": "good",
        "analysis": "结构较完整，有一定信息量；可再压一版更短的口述稿方便临场发挥。",
        "optimized_answer": answer,
        "tags": item.get("tags") or guess_tags(question),
    }


class MockLLM(BaseLLM):
    async def first_question(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        title = experience.get("title") or experience.get("company") or "这段经历"
        q = f"请介绍一下「{title}」里你负责的部分，以及最终取得了什么成果？"
        tags = ["行为面试", "项目介绍"]
        return {"question": q, "knowledgeTags": tags, "labels": [tags[0]]}

    async def feedback(self, experience: Dict[str, Any], node: Dict[str, Any], answer: str) -> Dict[str, Any]:
        tags = guess_tags(node.get("question", ""))
        has_digit = bool(re.search(r"\d", answer or ""))
        if has_digit:
            fb = "结构较清晰，已有量化信息；可再补「为什么这么做」的决策过程。"
        else:
            fb = "结构清晰，建议补充 1 个量化数据支撑结论。"
        return {"aiFeedback": fb, "knowledgeTags": tags, "labels": [tags[0]]}

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
            '{"aiFeedback":"一两句点评","knowledgeTags":["一级","二级"],"labels":["一级"]}。'
            f"一级标签必须来自：{L1_TAGS}。点评关注 STAR/量化/风险点，不要长篇大论。"
        )
        user = (
            self._exp_brief(experience)
            + f"\n问题：{node.get('question')}\n回答：{answer}\n请点评并打标签。"
        )
        try:
            return await self._chat_json(system, user)
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
            '只输出 JSON：{"quality":"good|weak","analysis":"点评","optimized_answer":"优化答法","tags":["一级","二级"]}。'
            f"一级标签必须来自：{L1_TAGS}。弱答（缺量化/STAR不清/含糊）必须 quality=weak。"
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
            return {
                "quality": q,
                "analysis": data.get("analysis") or "",
                "optimized_answer": data.get("optimized_answer") or "",
                "tags": data.get("tags") or guess_tags(item.get("question") or ""),
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


def get_llm() -> BaseLLM:
    if settings.llm_provider == "openai" and settings.llm_api_key:
        return OpenAILLM()
    return MockLLM()
