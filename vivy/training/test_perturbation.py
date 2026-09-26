import unittest

from training.perturbation import order_flip_rate, permute_candidates


class PerturbationTests(unittest.TestCase):
    def test_permutation_preserves_ids_and_selected_label(self):
        record = {"candidates": [{"id": "a"}, {"id": "b"}], "selected_candidate": "b"}
        perturbed = permute_candidates(record, seed=7)
        self.assertEqual({x["id"] for x in perturbed["candidates"]}, {"a", "b"})
        self.assertEqual(perturbed["selected_candidate"], "b")

    def test_flip_rate(self):
        self.assertEqual(order_flip_rate({}, ["a", "a", "a", "a", "a"]), 0.0)
        self.assertEqual(order_flip_rate({}, ["a", "b", "a", "b", "a"]), 0.5)


if __name__ == "__main__":
    unittest.main()
