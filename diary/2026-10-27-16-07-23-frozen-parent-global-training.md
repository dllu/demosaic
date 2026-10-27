# Frozen-parent global RAW training checks

Recorded: 2026-10-27T16:07:23-07:00 (America/Los_Angeles).

The preceding goal turn made progress by publishing the completed V137 report,
native comparisons, score plot and independent receipts in dad7566. V137 learned
stronger matching but did not visibly recover the difficult real mesh; V120
remains the general recommendation. Broad quality/RawNIND superiority and
100MP/10s remain unproven.

V124's original worker has now finished all20,000 updates. Its checkpoint is
d562ae2fc4e9bf903501a3db1f2192b93e465a48f150eec6de5f232d510f0cc6;
320,000 target contexts,560,480 sensor observations and640 validation forwards
are recorded. V125's original controller is live and waiting for its unchanged
64GiB launch headroom. No old source, budget, data cohort or schedule changed.
The existing full endpoint quality chain still waits for both arms.

Implemented explicit raw_global_only training, early scope-resume rejection
and trainable-only EMA updates. V138 starts freshly from V120, trains only the
18 normalized global branch tensors at LR1e-3, and keeps all91 parent model/EMA
tensors exact. This is a combined freezing/learning-rate intervention against
V137 jointLR1e-5, not an isolated LR causal ablation. Same seed70/90782photos/
27regions/quota.5/256B16BF16/singleview/zeroPSF/warm100/original1k horizon.
The newer90778/34 data and existing33-region epoch jobs remain separate.

65 focused tests pass. The first run had one bad test fixture assumption about
the parameter count of the no-DINO test model; its failure log is preserved and
the corrected test verifies actual parameter identities. Genuine CPU128/B1/FP32
and CUDA256/B16/BF16 each completed16+2 updates. Twelve changed scope/operator
resumes reject before construction;109 model/EMA tensors and18 Adam states are
finite, all91 common tensors stay exact and all18 branch gradient maxima are
nonzero. Peak CUDA allocation is8,198,603,264 bytes. The checks end during warmup
and do not qualify peak-LR stability or trained image quality.

Independent no-neural verification checks263,530,104 finite state values,
263,237,680 exact parent-state values,162,944,388 exact prepared values and
4,259,840 exact initial output values against V137. All65 old modules outside
train.py remain byte-identical; removing explicit scope additions restores the
old joint-training AST. Per-phase flat output equality is tested after actual
adaptation for four CFAs in FP32/BF16; arbitrary-image color/detail remains open.

The original V138 controller waits for V125 completion before production. A
prospective102-input quality queue reuses408 saved V120/V129/V136/V137 controls,
with480 metric rows/120 summaries/64 native PNGs expected. Exact67-module source,
full1k lineage/18Adam/91frozenparent/all1000 inputs must verify before inference.
Both GFX pairs include foliage/fence and corrected extra3842/3835 mesh, with
qualitative ISO100/AHD/JPEG references rather than GT. The zero-neural faint
supplement fixes300 strata/160 decompositions/four shared40x displays in advance;
native viewing remains required after results arrive.

Quality preparation initially stopped because the selected training helper
clone did not contain the collector. It executed no review and created no
claim; missing analysis helpers were copied from the completed frozen V137
review before declaring the queue. The first CPU supplement watcher then raced
the primary status file creation and exited before any analysis. Preserve all
v1 files, owner/failure receipts and source. An explicit v2 owner finishes the
same one-analyze/one-audit budget, with the original absolute deadline retained
and missing-status handling fixed; no training/control/inference was repeated.

[Current guide](../docs/raw-global-only-training.md) and
[check/queue receipt](../docs/results/raw-global-only-pilot-setup-v1.json)
record the executable implementation without claiming quality gains. No new20k
global run or performance-history point was added. This goal turn makes
implementation/check/queue progress while the full requested goal stays active.
