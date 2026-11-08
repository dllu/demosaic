# Flat spatial loss passes native checks and starts a matched trial

Recorded: 2026-11-08T02:15:28-08:00 (America/Los_Angeles).


The previous goal turn made progress: completed V178 and V180 training/reviews,
actual native inspection, exports and final independent publications are now
committed and pushed. V180 local fields retain a 15.93% EMA mesh-response gain
versus global V178 at higher quiet spatial error on 31/32 inputs. The original
fine-cab/clean-sky objective remains incomplete. This turn changes the next
training objective while retaining the useful local architecture.

Read the current loss sources and actual V180 traces. The existing clean-flat
mask already covers mean 69.0% of mesh, 50.3% of weak, 52.2% of photo, 90.8% of
mixed and 68.9% of flat batches. It is not absent from the relevant training
stream. Existing absolute flat/paired-common/DC terms mix or emphasize color
bias, while the weak-gradient experiment also pressured textured weak edges.

Add a separate spatial-error term in exactly the existing truncated 17px clean
neighborhoods (at most 1 DN16 range per target channel). The new loss is the
whole-image mean of mask times sqrt(1+local error variance)-1, in fixed 4-DN16
units, weight 0.25 times the unchanged domain weight. Per-channel mean error
is removed; existing absolute/DC/common losses remain necessary. Actual weak
target gradients are retained. FP64 centered separable moments avoid large
bias cancellation/materialized windows; FP32 output loss preserves the old
seven-term FP32 total before the addition. No inference target/mask/gate or
architecture changes. All 98 neural source files remain exact.

All 55 focused CPU checks pass, including 25 new independent value/derivative,
truncation, coverage, weak-signal descent, false-texture descent and constant
bias cases. All seven old terms and the mask stay exact. The first run had
24 passes/one test failure because pytest tried to convert a requires-grad
result to NumPy; .item fixed only that comparison. Loss code/tolerances stay
unchanged. Original test/log remain preserved.

The first preparation dependency check stopped before Torch/root/output work:
it resolved a canonical wrapper whose source guard requires the sealed entry.
That source/log are preserved. The corrected dependency check runs V180's
actual completed gate in a separate process with its frozen import paths.
No successful scientific work was repeated.

Actual new-loss probe owner PID 851930/create 1794132670.82 is terminal. Two
four-image native updates, mesh then mixed, start from real V172 Adam900 and
zero adapter/no history. New spatial losses are 0.1575498134 and 0.1955458224.
CPU/GPU new losses and all 6,291,456 output-gradient coordinates have zero
observed difference. Both eight-term FP32 totals reproduce independently.
All 142 trainable tensors have finite/nonzero gradients. Two wrapper/frozen/
matching/projection calls and ten sampler calls occur, without new source,
noise, parent/DINO, RAW decode or protected optimizer inputs. Peak allocation
6,743,250,944 bytes (about 6.28 GiB). The existing sampler atomic warning remains.

Model/Adam/EMA/CPU-CUDA RNG genuinely restore between updates without replay.
Independent CPU inspection strictly checks both saved raw/EMA/frozen states
and network Adam901/902, adapter1/2. The probes are not training initializers.
The original seven helper bodies are exact; the bound training body changes
only its objective import. Preparation verifies that source relationship.

Actual V181 trial owner PID 852882/create 1794132873.37 is running. It starts
from the same V172 raw/Adam/EMA checkpoint and zero adapter as V180, adds
900 updates/3,600 images over the same 1,000 cached rows with 100 ADC skips,
and preserves LR/domain weights/EMA/sampler. Row8 strict model/Adam/EMA/CPU-
CUDA RNG restoration passed and continued at row9 without replay. The original
737-source snapshot is immutable. New artifacts go to the external SSD to
preserve local reserve; originals and unavailable dataz are never accessed.

A separate eight-term auditor passes all 42 CPU corruption/lifecycle/grid
checks. Its actual frozen entry rejects the live owner before Torch/checkpoint
work. A recorded current prefix independently checks eight-term FP32 totals
and exact source/mask/LR bindings against completed V180; it is not a full
terminal training or quality audit. Full 822-case raw/EMA review, 36 native
cases, both protected GFX scene families/JPEGs and actual native crop inspection
remain required. There is no trained V181 detail or flat-safety claim yet.

[Loss and rationale](../docs/flat-spatial-evidence.md) ·
[Actual sources, probe, CPU inspection and launch evidence](../docs/results/v181-flat-spatial-preparation-v1.json).
