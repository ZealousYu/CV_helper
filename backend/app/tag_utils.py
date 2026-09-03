"""经历库标签归一化：大类 → 细分，减少杂乱标签。"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

# 大类 → [(细分名, 匹配规则), ...]
EXP_TAG_TREE: Sequence[Tuple[str, Sequence[Tuple[str, re.Pattern[str]]]]] = (
    (
        "AI",
        (
            ("AI提效", re.compile(r"AI提效|提效|Copilot|自动化助手|Agent|智能助手", re.I)),
            ("RAG调优", re.compile(r"RAG|向量|embedding|检索增强|知识库检索", re.I)),
            ("大模型应用", re.compile(r"大模型|LLM|GPT|豆包|提示词|Prompt|生成式", re.I)),
            ("工程开发", re.compile(r"Python|Java|后端|前端|API|代码|开发|算法|技术", re.I)),
        ),
    ),
    (
        "数据",
        (
            ("数据分析", re.compile(r"数据分析|分析洞察|洞察|复盘|数据", re.I)),
            ("指标设计", re.compile(r"指标|漏斗|DAU|埋点|核心指标", re.I)),
            ("可视化", re.compile(r"可视化|看板|Dashboard|Tableau|图表", re.I)),
            ("SQL/数仓", re.compile(r"SQL|Excel|BI|数仓|数据仓库", re.I)),
        ),
    ),
    (
        "产品",
        (
            ("需求设计", re.compile(r"需求|PRD|功能设计|产品设计|产品", re.I)),
            ("用户研究", re.compile(r"用户研究|调研|访谈|体验", re.I)),
            ("0-1项目", re.compile(r"0-1|0到1|从零|新建|立项|冷启动", re.I)),
        ),
    ),
    (
        "协作",
        (
            ("跨部门推进", re.compile(r"跨部门|推进|对齐|推动落地", re.I)),
            ("沟通协调", re.compile(r"协作|沟通|协调|冲突", re.I)),
        ),
    ),
    (
        "增长",
        (
            ("用户增长", re.compile(r"增长|获客|留存|转化|投放", re.I)),
            ("运营策略", re.compile(r"运营|活动运营|内容运营", re.I)),
        ),
    ),
)

_CHILD_TO_PARENT: Dict[str, str] = {
    child: parent
    for parent, children in EXP_TAG_TREE
    for child, _ in children
}
_PARENT_KEYS = {parent for parent, _ in EXP_TAG_TREE}


def allowed_child_tags() -> List[str]:
    return [child for _, children in EXP_TAG_TREE for child, _ in children]


def extract_tags_from_text(text: str) -> List[str]:
    """启发式：对整段文本匹配所有细分标签（可多选）。"""
    found: List[str] = []
    seen: set[str] = set()
    t = text or ""
    for _parent, children in EXP_TAG_TREE:
        for child_name, pat in children:
            if pat.search(t) and child_name not in seen:
                seen.add(child_name)
                found.append(child_name)
    return found[:6] or ["待整理"]


def normalize_exp_tags(tags: List[str]) -> List[str]:
    """将原始标签归并为细分标签（优先），便于筛选；最多 6 个。"""
    children: List[str] = []
    parents_only: List[str] = []
    seen_c: set[str] = set()
    seen_p: set[str] = set()

    for raw in tags or []:
        t = str(raw).strip()
        if not t:
            continue
        if t in _CHILD_TO_PARENT:
            if t not in seen_c:
                seen_c.add(t)
                children.append(t)
            continue
        if t in _PARENT_KEYS:
            if t not in seen_p:
                seen_p.add(t)
                parents_only.append(t)
            continue

        matched = False
        for parent, child_list in EXP_TAG_TREE:
            for child_name, pat in child_list:
                if pat.search(t):
                    if child_name not in seen_c:
                        seen_c.add(child_name)
                        children.append(child_name)
                    matched = True
                    break
            if matched:
                break

        if not matched and re.search(r"待确认|待补充|待整理", t):
            if "待整理" not in seen_c:
                seen_c.add("待整理")
                children.append("待整理")
        elif not matched and len(t) <= 10 and t not in seen_c:
            # 短标签无法归类时暂留，前端可显示为待整理类
            seen_c.add(t)
            children.append(t)

    # 只有大类、没有细分命中时，保留大类名（前端会按大类筛）
    out = list(children)
    for p in parents_only:
        has_child = any(_CHILD_TO_PARENT.get(c) == p for c in children)
        if not has_child and p not in out:
            out.append(p)

    return out[:6] or ["待整理"]
