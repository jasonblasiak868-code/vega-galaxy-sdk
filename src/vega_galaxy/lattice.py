"""lattice.py - the lattice as a graph with levels and kinetic energy, and the two views the owner described: from below (what MUST happen) and from above (what COULD happen).

THE PICTURE (owner, 2026-10-16, treated as metaphor; the math below stands on its own): levels are relationship types stacked like a 3D chessboard; kinetic energy flows up the edges; a black hole's
event horizon is the convergence layer where flow concentrates; the white hole is the future, a family tree of possibilities each with a confidence. From below you see only what has to happen for an
outcome; from above, what could happen, brighter where more energy supports it.
THE MATH:
  flow(n)         energy that reaches n = own energy + sum over incoming edges of flow(source) * share(source -> n)     where share = weight / (total outgoing weight of the source), computed from weights
                  scaled by the source's largest outgoing weight so that very large or very small weights neither overflow nor underflow     (energy is shared out, never multiplied)
  convergence(n)  1 - exp(-0.35 * incoming_flow(n))    in 0..1: how strongly flow concentrates on n
  must_pass(t)    the nodes every path from any source node to t goes through (dominators, found in one pass over the ancestors with a binary-lifting nearest common ancestor): the necessary conditions, from below
  could_happen    a beam search forward over outgoing weights with a reported dropped probability mass (vega_reasoning.aquire.forecast): the possibilities, from above
The graph must be acyclic (flow needs an order); a cycle is refused, never broken silently. Labels are plain ids; no content text is held."""
import math
import re

LEVELS = ("meaning", "value", "association", "family", "metamorphosis", "evolution", "mergers", "interactions", "bonds", "reactions", "convergences")
MAX_NODES = 20000
MAX_EDGES = 100000
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}")
K = 0.35
MAX_TOTAL_ENERGY = 1e300          # the energies of all nodes must add up to at most this, so no flow total can overflow


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
        try:
            total_energy = math.fsum(v["energy"] for v in self.nodes.values())
        except OverflowError:
            total_energy = math.inf
        if not math.isfinite(total_energy) or total_energy > MAX_TOTAL_ENERGY:
            raise LatticeRefused("the node energies add up to more than %g" % MAX_TOTAL_ENERGY)
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
        """{node: {"incoming": energy that arrived, "total": own + incoming}}; computed once. Sums are exact (math.fsum) and taken in a fixed order, so the same lattice gives the same numbers whatever order its edges were listed in."""
        if self._flow is None:
            share = {}
            for n in self.nodes:
                outs = self.out[n]
                if outs:
                    m = max(outs.values())                                   # scale by the largest weight: w / m is in (0, 1], so the sum below cannot overflow
                    denom = math.fsum(w / m for w in outs.values())
                    share[n] = {t: (w / m) / denom for t, w in outs.items()}
            f = {}
            for n in self.order:
                inc = math.fsum(f[s]["total"] * share[s][n] for s in sorted(self.inn[n]))
                f[n] = {"incoming": inc, "total": self.nodes[n]["energy"] + inc}
            self._flow = f
        return self._flow

    def convergence(self):
        return {n: round(1 - math.exp(-K * v["incoming"]), 6) for n, v in self.flow().items()}

    def must_pass(self, target):
        """Necessary conditions: every node that lies on ALL paths from any source (a node with no incoming edge) to `target`, target included. These are the dominators of the target below a virtual root that
        feeds every source. They are found in one pass over the ancestors in topological order: the dominator of a node is the nearest common ancestor, in the dominator tree built so far, of all its
        predecessors (binary lifting, so each step costs O(log n)). Removing each ancestor in turn and searching again would be quadratic."""
        if target not in self.nodes:
            raise LatticeRefused("unknown target")
        members = self._ancestors(target) | {target}
        position = {n: i for i, n in enumerate(self.order)}
        todo = sorted(members, key=position.__getitem__)
        index = {n: i + 1 for i, n in enumerate(todo)}                     # 0 is the virtual root
        size = len(todo) + 1
        levels = max(1, size.bit_length())
        up = [[0] * size for _ in range(levels)]                           # up[k][i]: the 2**k-th dominator above i
        depth = [0] * size
        for n in todo:
            i = index[n]
            preds = [index[p] for p in self.inn[n]]
            if not preds:
                parent = 0
            else:
                parent = preds[0]
                for q in preds[1:]:
                    parent = self._common(parent, q, up, depth)
            depth[i] = depth[parent] + 1
            up[0][i] = parent
            for k in range(1, levels):
                up[k][i] = up[k - 1][up[k - 1][i]]
        needed = []
        i = index[target]
        while i != 0:
            needed.append(todo[i - 1])
            i = up[0][i]
        return sorted(needed)

    @staticmethod
    def _common(a, b, up, depth):
        if depth[a] < depth[b]:
            a, b = b, a
        diff = depth[a] - depth[b]
        k = 0
        while diff:
            if diff & 1:
                a = up[k][a]
            diff >>= 1
            k += 1
        if a == b:
            return a
        for k in range(len(up) - 1, -1, -1):
            if up[k][a] != up[k][b]:
                a, b = up[k][a], up[k][b]
        return up[0][a]

    def _ancestors(self, t):
        seen, stack = set(), [t]
        while stack:
            n = stack.pop()
            for s in self.inn[n]:
                if s not in seen:
                    seen.add(s)
                    stack.append(s)
        return seen

    def could_happen(self, start, beam=8, depth=6):
        """Possibilities from above: the likeliest outcomes of walking forward from `start`, with the probability the beam threw away reported. Needs vega-reasoning-sdk."""
        if start not in self.nodes:
            raise LatticeRefused("unknown start")
        try:
            from vega_reasoning import aquire
        except ImportError as exc:
            raise LatticeRefused("the view from above needs vega-reasoning-sdk (%s)" % exc)
        graph = {n: dict(self.out[n]) for n in self.nodes}
        try:
            return aquire.forecast(graph, start, beam=beam, depth=depth)
        except aquire.AquireRefused as exc:
            raise LatticeRefused(str(exc))
