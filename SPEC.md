# vega-galaxy-sdk — Specification

Spec v1.0 — 2026-10-20 — describes the published reference implementation as tested. Where this document and the source disagree, the source wins.

**Contents:** [Purpose](#1-purpose-and-scope) · [Vocabulary](#2-vocabulary) · [Components](#3-components) · [Guarantees](#4-guarantees-and-non-guarantees) · [Failure modes](#5-failure-modes) · [Interfaces](#6-interfaces-and-diagnostics)

## 1. Purpose and scope

Specified: the lattice graph model, its flow and convergence math, the two views (necessary conditions and possibilities), and the deterministic scene and its hash record. Out of scope: rendering, data collection, and any claim that the metaphor predicts events.

## 2. Vocabulary

| Term | Meaning |
|---|---|
| Level | One of 11 ordered relationship types: meaning, value, association, family, metamorphosis, evolution, mergers, interactions, bonds, reactions, convergences. |
| Energy | A finite non-negative number on a node. |
| Flow | Energy that reaches a node. Total flow is own energy plus incoming. |
| Convergence | `1 - exp(-0.35 * incoming flow)`, in 0 to 1. |
| Necessary condition | A node on every path from any source to the target. |
| Possibility | A forward outcome with a probability, from a beam search. |
| Black hole | The node with the highest convergence. |
| Horizon | Nodes whose convergence meets a chosen threshold. |

## 3. Components

### 3.1 `lattice`

**Public interface.** `Lattice`, `LatticeRefused`, `LEVELS`, `MAX_NODES` (20,000), `MAX_EDGES` (100,000), `K` (0.35).

**Construction rules.** `nodes` is a non-empty dict of plain ids to `{level, energy}`. `edges` is a list of `(source, target, weight)` with weight a finite number above zero, between two different known nodes, never listed twice, and never running down the levels. The graph must be acyclic, and the node energies must add up to at most 1e300 so that no total can overflow. Violations raise `LatticeRefused`.

**Behavior.**
- `flow()`: for each node in topological order, incoming is the sum over incoming edges of the source's total times the edge's share of the source's outgoing weight. Shares are computed from weights scaled by the source's largest outgoing weight, so very large or very small weights neither overflow nor underflow. Sums are exact and taken in a fixed order, so the same lattice gives the same numbers whatever order its edges were listed in. Energy is shared out, never multiplied. Cached after the first call.
- `convergence()`: `round(1 - exp(-K * incoming), 6)` per node.
- `must_pass(target)`: returns every node that lies on all paths from any source to the target (the dominators below a virtual root that feeds every source), target included. It is found in one pass over the ancestors in topological order using a binary-lifting nearest common ancestor, so it stays fast at the size limit (a 20,000-node chain takes well under a second; the earlier remove-and-search method took minutes).
- `could_happen(start, beam, depth)`: calls the reasoning kit's forecast on the out-edge weights. Raises `LatticeRefused` if the reasoning kit is not installed, and also for a beam or depth the reasoning kit refuses.

**Invariants.** Acyclic, upward-only, finite numbers, ids only: no content text is held.

### 3.2 `scene`

**Public interface.** `build_scene`, `scene_record`, `MAX_FUTURE` (200).

**Behavior.** `build_scene(lat, future_from, beam, depth, horizon)` returns a dict with the black hole id, a `black_hole_active` flag (false when nothing converges), the level list, nodes, edges and an optional future layer. Node radius is `1.0 + 1.5 * level index`, angle is a stable function of the SHA-256 of the id, height is total flow scaled to 3, brightness is convergence over the maximum. The future layer carries outcomes, the best path, entropy in bits, dropped probability mass, `outcomes_total`, `outcomes_shown`, a `truncated` flag and `mass_not_shown` (the layer draws at most `MAX_FUTURE` outcomes, and the probability of the ones it did not draw is reported), and a note that these are possibilities, not predictions. `scene_record` returns the scene's SHA-256 over canonical JSON, counts, the black hole and whether it is active, horizon node count and future outcome count.

## 4. Guarantees and non-guarantees

| Guarantee | Module | Evidence |
|---|---|---|
| The same lattice always yields the same scene | `scene` | `tests/redteam_2_math_and_scale.py` |
| Cycles and downward edges are refused, not repaired | `lattice` | `tests/redteam_1_graph_and_views.py` |
| Energy is shared, not multiplied | `lattice` | `tests/redteam_2_math_and_scale.py` |
| The scene holds ids and numbers, never record text | `scene` | `tests/redteam_1_graph_and_views.py` |

| Non-guarantee | Reality |
|---|---|
| The future layer predicts events | No. It reports possibilities with confidence. |
| Necessary conditions scale to very large graphs | No. Cost grows with ancestors times edges. |
| Anything is rendered | No. A viewer is separate. |

## 5. Failure modes

| Event | What happens |
|---|---|
| Cycle in the lattice | `LatticeRefused` |
| Edge runs down the levels | `LatticeRefused` |
| Duplicate edge, unknown node, self-loop, bad weight | `LatticeRefused` |
| Unknown target or start | `LatticeRefused` |
| Reasoning kit missing | `could_happen` raises `LatticeRefused` |
| `horizon` outside 0 to 1 | `LatticeRefused` |

## 6. Interfaces and diagnostics

No console script. Diagnostics are the returned dictionaries and the `scene_record` hashes. No environment variables are read.
