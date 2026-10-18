"""lattice.py - the lattice as a graph with levels and kinetic energy, and the two views the owner described: from below (what MUST happen) and from above (what COULD happen).

THE PICTURE (owner, 2026-10-16, treated as metaphor; the math below stands on its own): levels are relationship types stacked like a 3D chessboard; kinetic energy flows up the edges; a black hole's
event horizon is the convergence layer where flow concentrates; the white hole is the future, a family tree of possibilities each with a confidence. From below you see only what has to happen for an
outcome; from above, what could happen, brighter where more energy supports it.
THE MATH:
  flow(n)         energy that reaches n = own energy + sum over incoming edges of flow(source) * weight / (total outgoing weight of source)     (energy is shared out, never multiplied)
  convergence(n)  1 - exp(-0.35 * incoming_flow(n))    in 0..1: how strongly flow concentrates on n
  must_pass(t)    the nodes every path from any source node to t goes through (dominators): the necessary conditions, from below
  could_happen    a beam search forward over outgoing weights with a reported dropped probability mass (vega_reasoning.aquire.forecast): the possibilities, from above
The graph must be acyclic (flow needs an order); a cycle is refused, never broken silently. Labels are plain ids; no content text is held."""
import math
import re

LEVELS = ("meaning", "value", "association", "family", "metamorphosis", "evolution", "mergers", "interactions", "bonds", "reactions", "convergences")
MAX_NODES = 20000
MAX_EDGES = 100000
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}")
K = 0.35


class LatticeRefused(ValueError):
    pass


class Lattice:
    def __init__(self, nodes, edges):
        """nodes: {id: {"level": one of LEVELS, "energy": number >= 0}}.  edges: [(source, target, weight > 0)] with the source on the same level or lower than the target."""
        if not isinstance(nodes, dict) or not nodes or len(nodes) > MAX_NODES:
            raise LatticeRefused("nodes is a non-empty dict of at most %d" % MAX_NODES)
        self.nodes = {}
        for n, d in nodes.items():
            if not isinstance(n, str) or not _ID.fullmatch(n) or not isinstance(d, dict) or set(d) - {"level", "energy"} or d.get("level") not in LEVELS:
                raise LatticeRefused("a node is id -> {level, energy}")
            e = d.get("energy", 0.0)
            if isinstance(e, bool) or not isinstance(e, (int, float)) or not math.isfinite(e) or e < 0:
                raise LatticeRefused("energy is a finite non-negative number")
            self.nodes[n] = {"level": d["level"], "energy": float(e)}
        if not isinstance(edges, (list, tuple)) or len(edges) > MAX_EDGES:
            raise LatticeRefused("edges is a list of at most %d" % MAX_EDGES)
        self.out = {n: {} for n in self.nodes}
        self.inn = {n: {} for n in self.nodes}
        for ed in edges:
            if not isinstance(ed, (list, tuple)) or len(ed) != 3:
                raise LatticeRefused("an edge is (source, target, weight)")
            s, t, w = ed
            if s not in self.nodes or t not in self.nodes or s == t:
                raise LatticeRefused("an edge joins two different known nodes")
            if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0:
                raise LatticeRefused("an edge weight is a finite number above zero")
            if LEVELS.index(self.nodes[s]["level"]) > LEVELS.index(self.nodes[t]["level"]):
                raise LatticeRefused("edge %s -> %s runs down the levels: energy flows up" % (s, t))
            if t in self.out[s]:
                raise LatticeRefused("edge %s -> %s is listed twice" % (s, t))
            self.out[s][t] = float(w)
            self.inn[t][s] = float(w)
        self.order = self._topological()
        self._flow = None

    def _topological(self):
        indeg = {n: len(self.inn[n]) for n in self.nodes}
        ready = sorted(n for n, d in indeg.items() if d == 0)
        order = []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for t in sorted(self.out[n]):
                indeg[t] -= 1
                if indeg[t] == 0:
                    ready.append(t)
            ready.sort()
        if len(order) != len(self.nodes):
            raise LatticeRefused("the lattice contains a cycle: flow needs an order")
        return order

    def flow(self):
        """{node: {"incoming": energy that arrived, "total": own + incoming}}; computed once."""
        if self._flow is None:
            tot_out = {n: sum(self.out[n].values()) for n in self.nodes}
            f = {}
            for n in self.order:
                inc = sum(f[s]["total"] * w / tot_out[s] for s, w in self.inn[n].items())
                f[n] = {"incoming": inc, "total": self.nodes[n]["energy"] + inc}
            self._flow = f
        return self._flow

    def convergence(self):
        return {n: round(1 - math.exp(-K * v["incoming"]), 6) for n, v in self.flow().items()}

    def must_pass(self, target):
        """Necessary conditions: every node that lies on ALL paths from any source (a node with no incoming edge) to `target`, target included. Found by removing each ancestor in turn and asking whether
        any source can still reach the target."""
        if target not in self.nodes:
            raise LatticeRefused("unknown target")
        anc = self._ancestors(target)
        sources = [n for n in anc if not self.inn[n]] or [target]
        needed = []
        for cand in sorted(anc | {target}):
            if not self._reaches(sources, target, banned=cand):               # with this node removed, no source can still reach the target
                needed.append(cand)
        return needed

    def _ancestors(self, t):
        seen, stack = set(), [t]
        while stack:
            n = stack.pop()
            for s in self.inn[n]:
                if s not in seen:
                    seen.add(s)
                    stack.append(s)
        return seen

    def _reaches(self, sources, target, banned):
        seen, stack = set(), [s for s in sources if s != banned]
        while stack:
            n = stack.pop()
            if n == target:
                return True
            if n in seen:
                continue
            seen.add(n)
            stack.extend(t for t in self.out[n] if t != banned)
        return False

    def could_happen(self, start, beam=8, depth=6):
        """Possibilities from above: the likeliest outcomes of walking forward from `start`, with the probability the beam threw away reported. Needs vega-reasoning-sdk."""
        if start not in self.nodes:
            raise LatticeRefused("unknown start")
        try:
            from vega_reasoning import aquire
        except ImportError as exc:
            raise LatticeRefused("the view from above needs vega-reasoning-sdk (%s)" % exc)
        graph = {n: dict(self.out[n]) for n in self.nodes}
        return aquire.forecast(graph, start, beam=beam, depth=depth)
