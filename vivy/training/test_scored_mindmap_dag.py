"""Tests for scored_mindmap_dag (Wave 3A — planning + QC).

Changelog:
    25/09/2026 (Claude Code — Wave 3A): Initial.
"""
from __future__ import annotations

import unittest

from training.scored_mindmap_dag import DAGPath, DecisionNode, MindmapDAG


def _build_simple_dag() -> MindmapDAG:
    """A → B → D, A → C → E  (diamond, C has higher score)."""
    dag = MindmapDAG()
    dag.add_node(DecisionNode(node_id="A", input_context="task-1", strategy="root", score=0.9))
    dag.add_node(DecisionNode(node_id="B", strategy="left", model_target="gemma4", score=0.4))
    dag.add_node(DecisionNode(node_id="C", strategy="right", model_target="qwen", score=0.8))
    dag.add_node(DecisionNode(node_id="D", strategy="leaf-left", score=0.5))
    dag.add_node(DecisionNode(node_id="E", strategy="leaf-right", score=0.7))
    dag.add_edge("A", "B")
    dag.add_edge("A", "C")
    dag.add_edge("B", "D")
    dag.add_edge("C", "E")
    return dag


class TestDecisionNode(unittest.TestCase):
    def test_is_leaf(self) -> None:
        n = DecisionNode(node_id="x")
        self.assertTrue(n.is_leaf())

    def test_not_leaf(self) -> None:
        n = DecisionNode(node_id="x", children=["y"])
        self.assertFalse(n.is_leaf())

    def test_to_dict(self) -> None:
        n = DecisionNode(node_id="x", strategy="s", score=0.8)
        d = n.to_dict()
        self.assertEqual(d["node_id"], "x")
        self.assertEqual(d["score"], 0.8)


class TestDAGPath(unittest.TestCase):
    def test_length(self) -> None:
        p = DAGPath(node_ids=("a", "b", "c"), score=0.5, rationale="r")
        self.assertEqual(p.length, 3)

    def test_leaf_id(self) -> None:
        p = DAGPath(node_ids=("a", "b"), score=0.5, rationale="r")
        self.assertEqual(p.leaf_id, "b")

    def test_empty_leaf(self) -> None:
        p = DAGPath(node_ids=(), score=0.0, rationale="r")
        self.assertEqual(p.leaf_id, "")


class TestGraphConstruction(unittest.TestCase):
    def test_add_node(self) -> None:
        dag = MindmapDAG()
        dag.add_node(DecisionNode(node_id="a"))
        self.assertEqual(dag.node_count, 1)

    def test_duplicate_raises(self) -> None:
        dag = MindmapDAG()
        dag.add_node(DecisionNode(node_id="a"))
        with self.assertRaises(ValueError):
            dag.add_node(DecisionNode(node_id="a"))

    def test_add_edge(self) -> None:
        dag = _build_simple_dag()
        a = dag.get_node("A")
        assert a is not None
        self.assertIn("B", a.children)
        self.assertIn("C", a.children)

    def test_edge_missing_node_raises(self) -> None:
        dag = MindmapDAG()
        dag.add_node(DecisionNode(node_id="a"))
        with self.assertRaises(KeyError):
            dag.add_edge("a", "ghost")

    def test_self_loop_raises(self) -> None:
        dag = MindmapDAG()
        dag.add_node(DecisionNode(node_id="a"))
        with self.assertRaises(ValueError):
            dag.add_edge("a", "a")

    def test_cycle_detection_raises(self) -> None:
        dag = _build_simple_dag()
        # A→B→D exists; adding D→A would cycle.
        with self.assertRaises(ValueError):
            dag.add_edge("D", "A")

    def test_roots(self) -> None:
        dag = _build_simple_dag()
        roots = dag.roots()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].node_id, "A")

    def test_leaves(self) -> None:
        dag = _build_simple_dag()
        leaf_ids = sorted(n.node_id for n in dag.leaves())
        self.assertEqual(leaf_ids, ["D", "E"])


class TestPlan(unittest.TestCase):
    def test_plan_picks_higher_scored_branch(self) -> None:
        dag = _build_simple_dag()
        path = dag.plan()
        # C (0.8) beats B (0.4), so path goes A→C→E.
        self.assertEqual(path.node_ids, ("A", "C", "E"))

    def test_plan_with_context_filter(self) -> None:
        dag = _build_simple_dag()
        path = dag.plan("task-1")
        self.assertEqual(path.node_ids[0], "A")

    def test_plan_empty_dag_raises(self) -> None:
        dag = MindmapDAG()
        with self.assertRaises(ValueError):
            dag.plan()

    def test_plan_score_is_mean(self) -> None:
        dag = _build_simple_dag()
        path = dag.plan()
        expected = (0.9 + 0.8 + 0.7) / 3
        self.assertAlmostEqual(path.score, expected, places=5)


class TestScorePath(unittest.TestCase):
    def test_score_path(self) -> None:
        dag = _build_simple_dag()
        s = dag.score_path(("A", "C", "E"))
        self.assertAlmostEqual(s, (0.9 + 0.8 + 0.7) / 3)

    def test_score_empty_path(self) -> None:
        dag = _build_simple_dag()
        self.assertEqual(dag.score_path(()), 0.0)

    def test_score_missing_node_raises(self) -> None:
        dag = _build_simple_dag()
        with self.assertRaises(KeyError):
            dag.score_path(("A", "ghost"))


class TestReroute(unittest.TestCase):
    def test_reroute_avoids_low_score_node(self) -> None:
        dag = _build_simple_dag()
        # Drop C's score below B's.
        new_path = dag.reroute("C", 0.1)
        # Now B branch (A→B→D) should win.
        self.assertEqual(new_path.node_ids, ("A", "B", "D"))

    def test_reroute_updates_score(self) -> None:
        dag = _build_simple_dag()
        dag.reroute("C", 0.1)
        c = dag.get_node("C")
        assert c is not None
        self.assertAlmostEqual(c.score, 0.1)

    def test_reroute_missing_node_raises(self) -> None:
        dag = _build_simple_dag()
        with self.assertRaises(KeyError):
            dag.reroute("ghost", 0.5)

    def test_reroute_invalid_score_raises(self) -> None:
        dag = _build_simple_dag()
        with self.assertRaises(ValueError):
            dag.reroute("A", 1.5)

    def test_reroute_root_only_graph(self) -> None:
        dag = MindmapDAG()
        dag.add_node(DecisionNode(node_id="solo", score=0.5))
        path = dag.reroute("solo", 0.9)
        self.assertEqual(path.node_ids, ("solo",))
        self.assertAlmostEqual(path.score, 0.9)


class TestThreshold(unittest.TestCase):
    def test_check_threshold(self) -> None:
        dag = MindmapDAG(score_threshold=0.3)
        dag.add_node(DecisionNode(node_id="hi", score=0.8))
        dag.add_node(DecisionNode(node_id="lo", score=0.1))
        low = dag.check_threshold()
        self.assertEqual(low, ["lo"])

    def test_all_above_threshold(self) -> None:
        dag = MindmapDAG(score_threshold=0.0)
        dag.add_node(DecisionNode(node_id="a", score=0.5))
        self.assertEqual(dag.check_threshold(), [])


class TestTrace(unittest.TestCase):
    def test_trace_records(self) -> None:
        dag = _build_simple_dag()
        records = dag.trace(("A", "C", "E"))
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["node_id"], "A")
        self.assertEqual(records[1]["model_target"], "qwen")

    def test_trace_skips_missing(self) -> None:
        dag = _build_simple_dag()
        records = dag.trace(("A", "ghost"))
        self.assertEqual(len(records), 1)


class TestSerialization(unittest.TestCase):
    def test_round_trip(self) -> None:
        dag = _build_simple_dag()
        d = dag.to_dict()
        dag2 = MindmapDAG.from_dict(d)
        self.assertEqual(dag2.node_count, 5)
        path = dag2.plan()
        self.assertEqual(path.node_ids, ("A", "C", "E"))

    def test_empty_round_trip(self) -> None:
        dag = MindmapDAG()
        dag2 = MindmapDAG.from_dict(dag.to_dict())
        self.assertEqual(dag2.node_count, 0)

    def test_from_dict_drops_ghost_children(self) -> None:
        """Children referencing missing nodes must not crash plan()."""
        data = {
            "nodes": [
                {"node_id": "A", "score": 0.9, "children": ["B", "ghost"]},
                {"node_id": "B", "score": 0.7, "children": []},
            ],
            "score_threshold": 0.3,
        }
        dag = MindmapDAG.from_dict(data)
        self.assertEqual(dag.node_count, 2)
        self.assertEqual(dag.get_node("A").children, ["B"])
        path = dag.plan()
        self.assertEqual(path.node_ids, ("A", "B"))


if __name__ == "__main__":
    unittest.main()
