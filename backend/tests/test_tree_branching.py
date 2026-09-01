"""追问树分支规则：深挖/发散=子节点，换角度=同级兄弟。"""
from app.tree_utils import generate_node_id, resolve_insert_parent


def _tree():
    return [
        {
            "nodeId": "q1",
            "question": "root",
            "children": [
                {"nodeId": "q1.1", "question": "child", "children": []},
            ],
        }
    ]


def test_deep_dive_from_q1_1_creates_child():
    tree = _tree()
    parent, sibs = resolve_insert_parent(tree, "q1.1", "deep_dive")
    assert parent == "q1.1"
    assert generate_node_id(parent, sibs) == "q1.1.1"


def test_new_angle_from_q1_1_creates_sibling():
    tree = _tree()
    parent, sibs = resolve_insert_parent(tree, "q1.1", "new_angle")
    assert parent == "q1"
    assert generate_node_id(parent, sibs) == "q1.2"


def test_new_angle_from_root_creates_new_root():
    tree = _tree()
    parent, sibs = resolve_insert_parent(tree, "q1", "new_angle")
    assert parent is None
    assert generate_node_id(parent, sibs) == "q2"


def test_diverge_is_child_like_deep_dive():
    tree = _tree()
    parent, sibs = resolve_insert_parent(tree, "q1.1", "diverge")
    assert parent == "q1.1"
    assert generate_node_id(parent, sibs) == "q1.1.1"


def test_delete_node_removes_subtree():
    from app.tree_utils import delete_node, find_node

    tree = [
        {
            "nodeId": "q1",
            "children": [
                {
                    "nodeId": "q1.1",
                    "children": [{"nodeId": "q1.1.1", "children": []}],
                },
                {"nodeId": "q1.2", "children": []},
            ],
        }
    ]
    new_tree, ok = delete_node(tree, "q1.1")
    assert ok
    assert find_node(new_tree, "q1.1") is None
    assert find_node(new_tree, "q1.1.1") is None
    assert find_node(new_tree, "q1.2") is not None
    assert find_node(new_tree, "q1") is not None


def test_delete_missing_node():
    from app.tree_utils import delete_node

    tree = [{"nodeId": "q1", "children": []}]
    new_tree, ok = delete_node(tree, "q9")
    assert not ok
    assert len(new_tree) == 1
