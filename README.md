# vega-galaxy-sdk

![vega-galaxy-sdk](assets/tile.svg)

The galaxy view of the knowledge lattice: levels, energy flow, convergence, what MUST happen (from below) and what COULD happen (from above), as a deterministic 3D scene.

> **Licensing.** Source-available, not open source. Free for personal use; free for registered small businesses (under US$1M revenue and valuation); everyone else needs a commercial license (see LICENSE; for a commercial license write to jasonblasiak.ai.mail@gmail.com). Patent pending. Draft licence text, not yet reviewed by an attorney.

Package: `vega_galaxy` (src layout). Depends on: vega-custody-sdk, vega-reasoning-sdk.

## Modules

| Module | What it does |
|---|---|
| `lattice` | Levels and kinetic energy; flow shared up the edges (never multiplied); convergence 1 - exp(-0.35 x flow); necessary conditions by removal; possibilities by beam search with the dropped probability reported. |
| `scene` | A deterministic scene (black hole at the centre, brightness, a future layer) with ids and numbers only, plus a hash-only record for the chain. |

## What it does NOT do (read this)

- The cosmology is a metaphor: the numbers mean only what the formulas say.
- The future layer shows possibilities with confidence, not predictions of what will happen.
- A lattice must be acyclic; a cycle is refused, not repaired.

## Status

See STATUS.md. Tests: 25 tests in 2 files, all passing.  See SECURITY.md for the threat model.

## Run the tests

Put `src` of this repo and of the repos it depends on on PYTHONPATH, then run each file in `tests/`.
