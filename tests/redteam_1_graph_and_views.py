"""Functional tests and attacks for the galaxy SDK."""
import json
import math
import os
import pathlib
import tempfile
import unittest

from vega_custody.dag.dag import Dag
from vega_galaxy import lattice as L
from vega_galaxy import scene as S


def diamond():
    """a -> b -> d and a -> c -> d, with e feeding d only: d MUST pass through itself; a is needed only if e is not a source of its own."""
    nodes = {"a": {"level": "meaning", "energy": 10}, "b": {"level": "value", "energy": 0}, "c": {"level": "value", "energy": 0}, "e": {"level": "meaning", "energy": 5}, "d": {"level": "association", "energy": 0}}
    edges = [("a", "b", 1), ("a", "c", 1), ("b", "d", 1), ("c", "d", 1), ("e", "d", 2)]
    return L.Lattice(nodes, edges)


def chain3():
    nodes = {"s": {"level": "meaning", "energy": 6}, "m": {"level": "value", "energy": 0}, "t": {"level": "association", "energy": 0}}
    return L.Lattice(nodes, [("s", "m", 1), ("m", "t", 1)])


class Flow(unittest.TestCase):
    def test_energy_is_shared_out_never_multiplied(self):
        lat = diamond()
        f = lat.flow()
        self.assertAlmostEqual(f["b"]["incoming"], 5.0)                  # a gives half to b and half to c
        self.assertAlmostEqual(f["d"]["incoming"], 5.0 + 5.0 + 5.0)      # b, c and all of e
        total_in = sum(n["energy"] for n in lat.nodes.values())
        self.assertAlmostEqual(f["d"]["total"], total_in)                # everything that was put in ends up at the single sink

    def test_convergence_is_a_probability_that_grows_with_flow(self):
        c = diamond().convergence()
        self.assertTrue(all(0 <= v < 1 for v in c.values()))
        self.assertEqual(c["a"], 0.0)
        self.assertGreater(c["d"], c["b"])


class Views(unittest.TestCase):
    def test_necessary_conditions_from_below(self):
        self.assertEqual(chain3().must_pass("t"), ["m", "s", "t"])
        lat = diamond()
        self.assertEqual(lat.must_pass("d"), ["d"])                      # two independent sources and two routes: nothing but d itself is unavoidable
        self.assertEqual(lat.must_pass("b"), ["a", "b"])

    def test_possibilities_from_above_report_what_they_dropped(self):
        f = chain3().could_happen("s")
        self.assertEqual(f["soft_landing"][0], "t")
        self.assertIn("mass_dropped", f)

    def test_the_scene_is_deterministic_and_content_free(self):
        a = S.build_scene(diamond(), future_from="a")
        b = S.build_scene(diamond(), future_from="a")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a["black_hole"], "d")
        self.assertIsNotNone(a["future"])
        self.assertEqual(S.scene_record(a), S.scene_record(b))

    def test_the_record_goes_on_the_chain_as_hashes(self):
        from vega_trace import trace as T
        t = pathlib.Path(tempfile.mkdtemp())
        dag = Dag([t / "c.jsonl"], [t / "l.jsonl"])
        dag.record("GALAXY_SCENE", S.scene_record(S.build_scene(diamond())))
        self.assertIn("scene_sha256", (t / "c.jsonl").read_text(encoding="utf-8"))


class Attacks(unittest.TestCase):
    def test_cycles_are_refused(self):
        nodes = {"a": {"level": "meaning"}, "b": {"level": "meaning"}}
        with self.assertRaises(L.LatticeRefused):
            L.Lattice(nodes, [("a", "b", 1), ("b", "a", 1)])

    def test_energy_cannot_flow_down_the_levels(self):
        nodes = {"a": {"level": "value"}, "b": {"level": "meaning"}}
        with self.assertRaises(L.LatticeRefused):
            L.Lattice(nodes, [("a", "b", 1)])

    def test_bad_graphs_are_refused(self):
        good = {"a": {"level": "meaning", "energy": 1}, "b": {"level": "value", "energy": 0}}
        for nodes, edges in ((None, []), ({}, []), ({"a b": {"level": "meaning"}}, []), ({"a": {"level": "nonsense"}}, []), ({"a": {"level": "meaning", "energy": -1}}, []),
                             ({"a": {"level": "meaning", "energy": float("nan")}}, []), ({"a": {"level": "meaning", "energy": True}}, []), ({"a": {"level": "meaning", "extra": 1}}, []),
                             (good, [("a", "z", 1)]), (good, [("a", "a", 1)]), (good, [("a", "b", 0)]), (good, [("a", "b", -1)]), (good, [("a", "b", float("inf"))]), (good, [("a", "b", True)]),
                             (good, [("a", "b", 1), ("a", "b", 2)]), (good, [("a", "b")]), (good, "edges"), (good, [None]), ("nodes", [])):
            with self.assertRaises(L.LatticeRefused, msg=repr(edges)[:50]):
                L.Lattice(nodes, edges)

    def test_unknown_targets_and_starts(self):
        with self.assertRaises(L.LatticeRefused):
            chain3().must_pass("zzz")
        with self.assertRaises(L.LatticeRefused):
            chain3().could_happen("zzz")

    def test_scene_arguments(self):
        for bad in (None, "x", {}):
            with self.assertRaises(L.LatticeRefused):
                S.build_scene(bad)
        for h in (-0.1, 1.5, True, "x"):
            with self.assertRaises(L.LatticeRefused):
                S.build_scene(chain3(), horizon=h)
        with self.assertRaises(L.LatticeRefused):
            S.scene_record({"kind": "other"})

    def test_a_single_node_lattice_works(self):
        lat = L.Lattice({"only": {"level": "meaning", "energy": 2}}, [])
        s = S.build_scene(lat)
        self.assertEqual(s["black_hole"], "only")
        self.assertEqual(lat.must_pass("only"), ["only"])

    def test_a_wide_lattice_is_bounded(self):
        nodes = {"r": {"level": "meaning", "energy": 1}}
        nodes.update({"n%d" % i: {"level": "value", "energy": 0} for i in range(300)})
        lat = L.Lattice(nodes, [("r", "n%d" % i, 1) for i in range(300)])
        f = lat.could_happen("r", beam=5, depth=2)
        self.assertGreater(f["mass_dropped"], 0.9)

    def test_the_view_from_above_needs_the_reasoning_sdk(self):
        import builtins
        real = builtins.__import__

        def no(name, *a, **k):
            if name.startswith("vega_reasoning"):
                raise ImportError("simulated: not installed")
            return real(name, *a, **k)
        builtins.__import__ = no
        try:
            with self.assertRaises(L.LatticeRefused):
                chain3().could_happen("s")
        finally:
            builtins.__import__ = real


if __name__ == "__main__":
    unittest.main()
