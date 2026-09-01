from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def find_node(tree: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
    for node in tree:
        if node.get("nodeId") == node_id:
            return node
        found = find_node(node.get("children") or [], node_id)
        if found:
            return found
    return None


def locate_parent(
    tree: List[Dict[str, Any]], node_id: str, parent: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """找到节点的父节点对象；若节点在根层则返回 None。节点不存在时也返回 None。"""
    for node in tree:
        if node.get("nodeId") == node_id:
            return parent
        if find_node(node.get("children") or [], node_id):
            return locate_parent(node.get("children") or [], node_id, node)
    return None


def update_node(tree: List[Dict[str, Any]], node_id: str, patch: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for node in tree:
        if node.get("nodeId") == node_id:
            result.append({**node, **patch})
        else:
            result.append({**node, "children": update_node(node.get("children") or [], node_id, patch)})
    return result


def add_child(tree: List[Dict[str, Any]], parent_id: str, child: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []
    for node in tree:
        if node.get("nodeId") == parent_id:
            children = list(node.get("children") or [])
            children.append(child)
            result.append({**node, "children": children})
        else:
            result.append({**node, "children": add_child(node.get("children") or [], parent_id, child)})
    return result


def add_root(tree: List[Dict[str, Any]], node: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(tree) + [node]


def delete_node(tree: List[Dict[str, Any]], node_id: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    删除指定节点及其整棵子树。
    返回 (新树, 是否找到并删除)。
    """
    removed = False
    result: List[Dict[str, Any]] = []
    for node in tree:
        if node.get("nodeId") == node_id:
            removed = True
            continue
        children, child_removed = delete_node(node.get("children") or [], node_id)
        if child_removed:
            removed = True
        result.append({**node, "children": children})
    return result, removed


def resolve_insert_parent(
    tree: List[Dict[str, Any]], from_node_id: str, action: str
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    决定新节点挂在谁下面。
    - deep_dive / diverge：挂在当前节点下（子节点，如 q1.1 → q1.1.1）
    - new_angle：与当前节点同级（兄弟，如 q1.1 → q1.2；当前是根则 q1 → q2）
    返回 (parent_id, siblings)。parent_id 为 None 表示挂到根层。
    """
    current = find_node(tree, from_node_id)
    if not current:
        raise KeyError(from_node_id)

    if action == "new_angle":
        parent = locate_parent(tree, from_node_id)
        if parent is None:
            return None, tree
        return parent.get("nodeId"), list(parent.get("children") or [])

    return from_node_id, list(current.get("children") or [])


def generate_node_id(parent_id: Optional[str], siblings: List[Dict[str, Any]]) -> str:
    if not parent_id:
        nums = []
        for s in siblings:
            try:
                nums.append(int(str(s.get("nodeId", "")).replace("q", "").split(".")[0]))
            except ValueError:
                pass
        nxt = max(nums) + 1 if nums else 1
        return f"q{nxt}"
    child_nums = []
    prefix = f"{parent_id}."
    for s in siblings:
        nid = str(s.get("nodeId", ""))
        if nid.startswith(prefix):
            try:
                child_nums.append(int(nid[len(prefix) :].split(".")[0]))
            except ValueError:
                pass
    nxt = max(child_nums) + 1 if child_nums else 1
    return f"{parent_id}.{nxt}"


def empty_node(node_id: str, question: str, **kwargs: Any) -> Dict[str, Any]:
    return {
        "nodeId": node_id,
        "question": question,
        "answerMode": None,
        "answer": None,
        "aiFeedback": None,
        "labels": kwargs.get("labels", []),
        "knowledgeTags": kwargs.get("knowledgeTags", []),
        "marks": [],
        "triggerFrom": kwargs.get("triggerFrom"),
        "children": [],
    }
