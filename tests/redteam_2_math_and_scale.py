"""RED TEAM 2 - galaxy SDK: the math against brute force and random graphs, input order, and size."""
import itertools
import json
import math
import random
import time
import unittest

from vega_galaxy import lattice as L
from vega_galaxy import scene as S

LV = L.LEVELS


def random_dag(rnd, n, p):
    names = ["n%d" % i for i in range(n)]
    levels = sorted(rnd.choice(range(len(LV))) for _ in names)
    nodes = {nm: {"level": LV[lv], "energy": round(rnd.random() * 5, 3)} for nm, lv in zip(names, levels)}
    edges = []
    for i, j in itertools.combinations(range(n), 2):
        if rnd.random() < p:
            edges.append((names[i], names[j], round(0.1 + rnd.random() * 3, 3)))
    return nodes, edges


def all_paths(out, src, dst, path=None):
    path = (path or []) + [src]
    if src == dst:
        yield path
        return
    for t in out.get(src, ()):
        yield from all_paths(out, t, dst, path)


class A_Conservation(unittest.TestCase):
    def test_total_energy_is_conserved_on_random_graphs(self):
        for seed in range(150):
            rnd = random.Random(seed)
            nodes, edges = random_dag(rnd, rnd.randint(2, 12), 0.35)
            lat = L.Lattice(nodes, edges)
            f = lat.flow()
            sinks = [n for n in lat.nodes if not lat.out[n]]
            self.assertAlmostEqual(sum(f[s]["total"] for s in sinks), sum(v["energy"] for v in lat.nodes.values()), places=6, msg="seed %d" % seed)

    def test_flow_never_goes_negative_and_convergence_stays_a_probability(self):
        for seed in range(100):
            nodes, edges = random_dag(random.Random(1000 + seed), 10, 0.4)
            lat = L.Lattice(nodes, edges)
            self.assertTrue(all(v["incoming"] >= 0 for v in lat.flow().values()))
            self.assertTrue(all(0 <= c < 1 for c in lat.convergence().values()))

    def test_convergence_is_monotone_in_incoming_flow(self):
        nodes, edges = random_dag(random.Random(5), 12, 0.4)
        lat = L.Lattice(nodes, edges)
        pairs = sorted((v["incoming"], lat.convergence()[n]) for n, v in lat.flow().items())
        self.assertEqual([c for _, c in pairs], sorted(c for _, c in pairs))


class B_NecessaryConditions(unittest.TestCase):
    def test_must_pass_matches_brute_force_on_random_graphs(self):
        for seed in range(120):
            rnd = random.Random(seed)
            nodes, edges = random_dag(rnd, rnd.randint(2, 8), 0.4)
            lat = L.Lattice(nodes, edges)
            for target in lat.nodes:
                anc = lat._ancestors(target)
                sources = [n for n in anc if not lat.inn[n]] or [target]
                paths = [p for s in sources for p in all_paths(lat.out, s, target)]
                expected = sorted(x for x in (anc | {target}) if all(x in p for p in paths)) if paths else [target]
                self.assertEqual(lat.must_pass(target), expected, "seed %d target %s" % (seed, target))


class C_Determinism(unittest.TestCase):
    def test_the_scene_does_not_depend_on_the_order_nodes_or_edges_were_listed(self):
        nodes, edges = random_dag(random.Random(9), 10, 0.4)
        a = S.build_scene(L.Lattice(nodes, edges))
        shuffled_nodes = dict(reversed(list(nodes.items())))
        shuffled_edges = list(reversed(edges))
        b = S.build_scene(L.Lattice(shuffled_nodes, shuffled_edges))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_scene_numbers_are_finite_and_brightness_is_in_range(self):
        for seed in range(40):
            nodes, edges = random_dag(random.Random(seed), 9, 0.4)
            s = S.build_scene(L.Lattice(nodes, edges), future_from=sorted(nodes)[0])
            for n in s["nodes"]:
                for k in ("x", "y", "z", "flow", "convergence", "brightness"):
                    self.assertTrue(math.isfinite(n[k]), (seed, k))
                self.assertTrue(0 <= n["brightness"] <= 1)
            for f in s["future"]["outcomes"]:
                self.assertTrue(0 <= f["probability"] <= 1)

    def test_the_black_hole_is_the_most_convergent_node(self):
        nodes, edges = random_dag(random.Random(3), 10, 0.5)
        lat = L.Lattice(nodes, edges)
        s = S.build_scene(lat)
        conv = lat.convergence()
        self.assertEqual(conv[s["black_hole"]], max(conv.values()))

    def test_a_different_lattice_gives_a_different_scene_hash(self):
        n1, e1 = random_dag(random.Random(1), 8, 0.4)
        n2, e2 = random_dag(random.Random(2), 8, 0.4)
        self.assertNotEqual(S.scene_record(S.build_scene(L.Lattice(n1, e1)))["scene_sha256"], S.scene_record(S.build_scene(L.Lattice(n2, e2)))["scene_sha256"])


class D_Scale(unittest.TestCase):
    def test_a_long_chain_is_handled_without_recursion_trouble_or_long_waits(self):
        n = 2500
        nodes = {"c%d" % i: {"level": LV[min(i * len(LV) // n, len(LV) - 1)], "energy": 1.0 if i == 0 else 0.0} for i in range(n)}
        edges = [("c%d" % i, "c%d" % (i + 1), 1.0) for i in range(n - 1)]
        t0 = time.time()
        lat = L.Lattice(nodes, edges)
        lat.flow()
        lat.convergence()
        S.build_scene(lat)
        self.assertLess(time.time() - t0, 10.0)

    def test_the_size_limits_hold(self):
        with self.assertRaises(L.LatticeRefused):
            L.Lattice({("n%d" % i): {"level": "meaning"} for i in range(L.MAX_NODES + 1)}, [])
        with self.assertRaises(L.LatticeRefused):
            L.Lattice({"a": {"level": "meaning"}, "b": {"level": "value"}}, [("a", "b", 1)] * (L.MAX_EDGES + 1))

    def test_the_future_layer_is_capped(self):
        nodes = {"r": {"level": "meaning", "energy": 1}}
        nodes.update({"n%d" % i: {"level": "value"} for i in range(400)})
        lat = L.Lattice(nodes, [("r", "n%d" % i, 1) for i in range(400)])
        s = S.build_scene(lat, future_from="r", beam=400, depth=2)
        self.assertLessEqual(len(s["future"]["outcomes"]), S.MAX_FUTURE)


if __name__ == "__main__":
    unittest.main()
