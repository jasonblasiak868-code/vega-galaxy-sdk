# vega-galaxy-sdk — Capabilities

Each row says what the capability is, why a policy or prompt-level approach cannot give it, where this code enforces it, which test shows it, and the honest limit.

| Capability | Why a prompt cannot provide it | Enforced in | Test | Honest limit |
|---|---|---|---|---|
| Necessary conditions from below | A model can list plausible prerequisites; this finds the nodes whose removal cuts every path | `Lattice.must_pass` | `tests/redteam_1_graph_and_views.py` | Slow on very large graphs |
| Possibilities from above with dropped mass | A model's "likely outcomes" carry no count of what was left out; this reports it | `Lattice.could_happen` | `tests/redteam_1_graph_and_views.py` | Needs the reasoning kit; confidence is not prediction |
| Conserved flow | Prose cannot guarantee conservation; the formula shares energy and never multiplies it | `Lattice.flow` | `tests/redteam_2_math_and_scale.py` | Only as meaningful as the weights you give |
| Convergence score | A fixed formula gives the same number every run | `Lattice.convergence` | `tests/redteam_2_math_and_scale.py` | A metaphor with a formula, not a measurement of reality |
| Cycle refusal | A model may tolerate a loop; flow needs an order, so a loop is refused | `Lattice._topological` | `tests/redteam_1_graph_and_views.py` | Cycles must be fixed by the caller |
| Deterministic scene | The same input always draws the same picture | `scene.build_scene` | `tests/redteam_2_math_and_scale.py` | No renderer included |
| Picture-to-lattice proof | A hash of the scene shows a picture belongs to that lattice | `scene.scene_record` | `tests/redteam_1_graph_and_views.py` | Proves identity, not truth |
| No content in the scene | Ids and numbers only, so a scene can be shared without the records | `scene.py` | `tests/redteam_1_graph_and_views.py` | Ids themselves can carry meaning |

## Its part in the family loop

Records feed the memory and knowledge layers; the knowledge graph becomes a lattice; the reasoning layer forecasts over it; this kit shows the result as conditions from below and possibilities from above so a human can decide again. It computes and displays. It holds no authority and takes no action.

See [README.md](README.md), [SPEC.md](SPEC.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
