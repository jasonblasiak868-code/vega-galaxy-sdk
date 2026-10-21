"""scene.py - a deterministic 3D scene of the lattice for a viewer (three.js in Vega OS), plus the record that goes on the chain.

  radius  grows with the level (outer levels are further from the black hole); the black hole sits at the centre and is the node with the highest convergence; black_hole_active is false when nothing converges (every convergence is 0), so the label is not a claim
  angle   a stable function of the node id, so the same lattice always draws the same galaxy
  height  the node's total flow, scaled
  brightness  convergence for present nodes; for the future layer (white hole) the forecast probability
The scene holds ids, levels and numbers only: no text of any record. scene_record() gives the hashes for the chain, so a picture can be shown to be the picture of THAT lattice."""
import hashlib
import json
import math

from vega_galaxy.lattice import LEVELS, Lattice, LatticeRefused

MAX_FUTURE = 200


def _angle(node_id):
    return int(hashlib.sha256(node_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF * 2 * math.pi


def build_scene(lat, future_from=None, beam=8, depth=6, horizon=0.5):
    if not isinstance(lat, Lattice):
        raise LatticeRefused("build_scene takes a Lattice")
    if isinstance(horizon, bool) or not isinstance(horizon, (int, float)) or not 0 <= horizon <= 1:
        raise LatticeRefused("horizon is a number in 0..1")
    flow, conv = lat.flow(), lat.convergence()
    top = max(conv.values()) or 1.0
    maxflow = max(v["total"] for v in flow.values()) or 1.0
    nodes = []
    for n in sorted(lat.nodes):
        lv = LEVELS.index(lat.nodes[n]["level"])
        a = _angle(n)
        r = 1.0 + 1.5 * lv
        nodes.append({"id": n, "level": lat.nodes[n]["level"], "x": round(r * math.cos(a), 4), "y": round(r * math.sin(a), 4), "z": round(3.0 * flow[n]["total"] / maxflow, 4),
                      "flow": round(flow[n]["total"], 6), "convergence": conv[n], "brightness": round(conv[n] / top, 4), "horizon": conv[n] >= horizon})
    black_hole = max(sorted(lat.nodes), key=lambda n: (conv[n], n))
    edges = [{"from": s, "to": t, "weight": w} for s in sorted(lat.out) for t, w in sorted(lat.out[s].items())]
    scene = {"kind": "lattice_galaxy", "black_hole": black_hole, "black_hole_active": conv[black_hole] > 0, "levels": list(LEVELS), "nodes": nodes, "edges": edges, "future": None}
    if future_from is not None:
        f = lat.could_happen(future_from, beam=beam, depth=depth)
        fut = []
        items = list(f["outcomes"].items())
        for i, (n, p) in enumerate(items[:MAX_FUTURE]):
            a = _angle(n)
            fut.append({"id": n, "probability": p, "x": round(2.0 * math.cos(a), 4), "y": round(2.0 * math.sin(a), 4), "z": round(4.0 + 2.0 * p, 4), "brightness": round(p, 4)})
        scene["future"] = {"from": future_from, "outcomes": fut, "best_path": f["best_path"], "entropy_bits": f["entropy_bits"], "mass_dropped": f["mass_dropped"],
                           "outcomes_total": len(items), "outcomes_shown": len(fut), "truncated": len(items) > MAX_FUTURE,
                           "mass_not_shown": round(sum(p for _, p in items[MAX_FUTURE:]), 6),
                           "note": "possibilities with confidence, not predictions of what will happen"}
    return scene


def scene_record(scene):
    """Hash-only record for the chain: which lattice this picture is of, and what the future layer said."""
    if not isinstance(scene, dict) or scene.get("kind") != "lattice_galaxy":
        raise LatticeRefused("scene_record takes a scene from build_scene")
    body = json.dumps(scene, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {"trace": "mapping", "kind": "galaxy_scene", "scene_sha256": hashlib.sha256(body).hexdigest(), "nodes": len(scene["nodes"]), "edges": len(scene["edges"]), "black_hole": scene["black_hole"], "black_hole_active": scene["black_hole_active"],
            "horizon_nodes": sum(1 for n in scene["nodes"] if n["horizon"]), "future_outcomes": len(scene["future"]["outcomes"]) if scene["future"] else 0}
