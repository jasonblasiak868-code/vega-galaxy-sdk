"""RED TEAM 3 - galaxy SDK: numbers that overflow, a scene that must stay strict JSON, an honest report of what was left out, and a necessary-conditions search that stays fast at the size limit."""
import json
import time
import unittest

from vega_galaxy import lattice as L
from vega_galaxy import scene as S

LV = L.LEVELS


def two_children(w):
    return L.Lattice({"s": {"level": "meaning", "energy": 10}, "a": {"level": "value"}, "b": {"level": "value"}}, [("s", "a", w), ("s", "b", w)])


class A_Overflow(unittest.TestCase):
    def test_huge_weights_still_share_energy_evenly(self):
        f = two_children(1e308).flow()
        self.assertAlmostEqual(f["a"]["incoming"], 5.0)
        self.assertAlmostEqual(f["b"]["incoming"], 5.0)

    def test_tiny_weights_still_share_energy_evenly(self):
        f = two_children(1e-300).flow()
        self.assertAlmostEqual(f["a"]["incoming"], 5.0)

    def test_energies_that_cannot_add_up_are_refused(self):
        with self.assertRaises(L.LatticeRefused):
            L.Lattice({"s": {"level": "meaning", "energy": 1.7e308}, "t": {"level": "value", "energy": 1.7e308}}, [("s", "t", 1)])

    def test_the_scene_is_strict_json_for_very_large_but_valid_numbers(self):
        lat = L.Lattice({"s": {"level": "meaning", "energy": 1e299}, "t": {"level": "value", "energy": 1e299}}, [("s", "t", 1)])
        sc = S.build_scene(lat)
        json.dumps(sc, allow_nan=False)
        json.dumps(S.scene_record(sc), allow_nan=False)


class B_HonestReporting(unittest.TestCase):
    def test_a_lattice_with_no_convergence_has_no_active_black_hole(self):
        lat = L.Lattice({"a": {"level": "meaning", "energy": 1}, "b": {"level": "meaning", "energy": 1}}, [])
        sc = S.build_scene(lat)
        self.assertIs(sc["black_hole_active"], False)
        self.assertIs(S.scene_record(sc)["black_hole_active"], False)

    def test_a_converging_lattice_has_an_active_black_hole(self):
        lat = L.Lattice({"s": {"level": "meaning", "energy": 4}, "t": {"level": "value"}}, [("s", "t", 1)])
        self.assertIs(S.build_scene(lat)["black_hole_active"], True)

    def test_cutting_the_future_layer_is_reported(self):
        nodes = {"r": {"level": "meaning", "energy": 1}}
        nodes.update({"n%d" % i: {"level": "value"} for i in range(400)})
        lat = L.Lattice(nodes, [("r", "n%d" % i, 1) for i in range(400)])
        fut = S.build_scene(lat, future_from="r", beam=400, depth=2)["future"]
        self.assertEqual(fut["outcomes_total"], 400)
        self.assertEqual(fut["outcomes_shown"], S.MAX_FUTURE)
        self.assertTrue(fut["truncated"])
        self.assertAlmostEqual(fut["mass_not_shown"] + sum(o["probability"] for o in fut["outcomes"]), 1.0, places=4)

    def test_an_uncut_future_layer_says_so(self):
        lat = L.Lattice({"s": {"level": "meaning", "energy": 1}, "t": {"level": "value"}}, [("s", "t", 1)])
        fut = S.build_scene(lat, future_from="s")["future"]
        self.assertFalse(fut["truncated"])
        self.assertEqual(fut["mass_not_shown"], 0.0)

    def test_bad_beam_or_depth_is_one_kind_of_refusal(self):
        lat = L.Lattice({"s": {"level": "meaning", "energy": 1}, "t": {"level": "value"}}, [("s", "t", 1)])
        for beam, depth in ((0, 3), (-1, 3), (3, 0), (True, 3), (3, "x"), (10 ** 9, 3)):
            with self.assertRaises(L.LatticeRefused, msg=repr((beam, depth))):
                lat.could_happen("s", beam=beam, depth=depth)


class C_NecessaryConditionsScale(unittest.TestCase):
    def test_a_chain_at_the_size_limit_is_fast(self):
        n = L.MAX_NODES
        nodes = {"c%d" % i: {"level": LV[min(i * len(LV) // n, len(LV) - 1)], "energy": 1.0 if i == 0 else 0.0} for i in range(n)}
        lat = L.Lattice(nodes, [("c%d" % i, "c%d" % (i + 1), 1.0) for i in range(n - 1)])
        t0 = time.time()
        got = lat.must_pass("c%d" % (n - 1))
        self.assertLess(time.time() - t0, 10.0)
        self.assertEqual(len(got), n)                      # every node of a chain is unavoidable


class D_Limits(unittest.TestCase):
    def test_the_edge_limit_is_enforced_on_distinct_valid_edges(self):
        n = 460                                                    # 460 * 459 / 2 = 105,570 distinct forward edges, all on one level, all acyclic
        nodes = {"n%d" % i: {"level": "meaning", "energy": 0} for i in range(n)}
        edges = [("n%d" % i, "n%d" % j, 1) for i in range(n) for j in range(i + 1, n)][: L.MAX_EDGES + 1]
        self.assertEqual(len(edges), L.MAX_EDGES + 1)
        with self.assertRaises(L.LatticeRefused):
            L.Lattice(nodes, edges)
        L.Lattice(nodes, edges[: L.MAX_EDGES])                     # exactly at the limit is accepted


if __name__ == "__main__":
    unittest.main()
