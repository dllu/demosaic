# V169 fixed spatial balance isolates broad RGB displacement

Recorded: 2026-11-07T13:08:41-08:00 (America/Los_Angeles).

The previous goal turn completed and pushed V168 quality/evidence. This turn
tests a fixed Gaussian complement of the direct RGB correction to reduce broad
displacement while retaining fine detail and the existing spectral path. The
parent is not filtered. Sigma8/radius24 native pixels are fixed before this
quality pass. The control is V168 raw/EMA with exact original-output replay;
spectral-only and direct-only paths diagnose the split. This may sacrifice
coarse correction and gives no general flat-safety guarantee.

Implemented a separate module, preserving all90 older neural files and all47
state tensors/124909 weights.47 relevant CPU tests pass, including19 new tests;
six CPU/CUDA filter value/gradient cases and three autocast checks pass. Two
actual transferred endpoint states load strictly. No training or parent/DINO
calls, new sources or noise draws.822 fixed cases/1644 root calls; all metrics
and fingerprints retained, with full new arrays only for36 preselected native
cases. Planned48 boards/24 triplets preserve native coordinates and transforms.
[Protocol and limitations](../docs/balanced-spatial-correction.md).

Initial preparation admission assertion did not capture resource values; its
actual failing subcondition is unknown. It stopped before a plan/worker. The
next preparation passed, but worker4132541 stopped at an unavailable SciPy
import before its claim/CUDA/model calls. The versioned current worker uses
the same NumPy separable-convolution oracle as the tests and adopts the actual
CUDA admission receipt. Both failed sources/logs remain intact. Current root
is `.cache/quality-20261107/V169-balanced-spatial-v3`; no forward was repeated.
[Current admission](../docs/results/v169-spatial-balance-preparation-v2.json).

Originals and protected siblings stay read-only/excluded; `/mnt/dataz` remains
unused. Current quality work is not a completed gain or proof of the full goal.
