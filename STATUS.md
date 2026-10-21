# STATUS 

## BUILT and tested

- lattice
- scene

Tests: 36 tests in 3 files, all passing. Every fix in `tests/mutations.py` was checked by undoing it and confirming a test fails; one mutant survives and is equivalent (the self-loop check, which cycle detection also refuses).

## DESIGNED ONLY (not built)

- The three.js viewer in Vega OS is not part of this repo.
- The zipper weight-layering idea is captured in the design register, not built.

## Release

Source-available under the LICENSE in this folder. Patent pending (U.S. provisional application 64/178,949 and others). The licence text is a draft that has not been reviewed by an attorney.
