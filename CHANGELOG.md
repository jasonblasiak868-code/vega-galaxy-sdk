# Changelog

## 2026-10-21: fixes found by a line-by-line source read

Found by reading `lattice.py` and `scene.py` against the README and SPEC, then reproducing each suspected defect before fixing it. Each fix has a regression test in `tests/redteam_3_overflow_and_report.py` that failed before the fix, and each fix was checked by undoing it and confirming a test fails.

### Fixed
- **Large edge weights produced `nan` flow.** Two edges of weight 1e308 from one source made every share `nan`. Shares are now computed from weights scaled by the source's largest weight, so the sum cannot overflow.
- **Huge node energies put `nan` into the scene.** Flow totals became `inf`, scene heights became `nan`, and the scene hash was taken over invalid JSON. A lattice whose node energies add up to more than 1e300 is now refused, and `scene_record` refuses non-finite numbers.
- **The necessary-conditions search was quadratic.** A 20,000-node chain (the size limit) took 163 seconds. `must_pass` now finds the dominators in one pass and takes well under a second. It matches the old method on 120 random graphs (the existing brute-force test).
- **The future layer cut outcomes silently.** With 400 equally likely outcomes it drew 200, their probabilities summed to 0.5, and `mass_dropped` still read 0.0. The layer now reports `outcomes_total`, `outcomes_shown`, `truncated` and `mass_not_shown`.
- **A lattice with no convergence still named a black hole** as if one existed. The scene now carries `black_hole_active`, false when nothing converges. The label itself is unchanged.
- A bad `beam` or `depth` raised the reasoning kit's exception instead of `LatticeRefused`. It is now one kind of refusal.
- The test for the edge limit used duplicate edges, which the duplicate check already refused, so the limit itself was untested. It now uses distinct valid edges.

### Changed
- Flow sums are exact (`math.fsum`) and taken in a fixed order, so numbers no longer depend on the order edges were listed in.
- `scene_record` has new fields (`black_hole_active`), so a record taken with this version differs from one taken with the earlier version for the same lattice.
- A lattice whose node energies add up to more than 1e300 is refused where it was accepted before.

### Not changed
- Nodes held in a `Lattice` are treated as read-only after construction. Changing a node's energy afterwards does not refresh the cached flow.
- `vega-custody-sdk` is listed as a dependency but used only by the test that records a scene on the chain; the library itself needs only `vega-reasoning-sdk`, and only for the view from above.
