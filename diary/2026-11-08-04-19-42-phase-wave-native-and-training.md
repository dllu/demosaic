# Phase-aware readout native proofs and isolated training

Recorded: 2026-11-08T04:19:42-08:00 (America/Los_Angeles).

The previous goal turn is progress: V183 completed quality review, native viewing,
strict exports, browser verification and publication, committed/pushed9ef5b505.
It recovers6.95% EMA mesh response versus V181 at0.39–0.67% higher quiet spatial
RMS. Real fine crossings and broad colored mottle remain unresolved, so the
joint goal stays active. No completed scientific work was repeated here.

V184 changes the architecture rather than another loss weight. The 80 local
wave coordinates currently enter the39-channel matching adapter and shared
network. A new shared6→16→12 contextual readout mixes two measured complex
waves into each camera-RGB color and explicitly transports native subpixel phase.
All eight selection direction/rank fields contribute equally. Only316 new
parameters/four tensors train; all189 inherited V183 EMA tensors stay frozen/eval.
The final204 weights/biases start at zero; hidden112 context parameters have a
fixed local seed18401. Global RNG stays unchanged. Local zero variance preserves
the inherited output exactly. Neither that identity nor zero-wave output proves
noisy-flat safety, because a noisy flat has nonzero measured waves. Aliases,
selection bias, support spreading and interpolation remain limitations.

All36 focused CPU model/state checks pass. The native CPU proof compares
12,779,520 readout values across six cached RAW/variance/CFA cases with independent
NumPy. Maximum absolute difference is2.317370711324429e−6 in head units, within
the fixed combined tolerance. All189 inherited tensors load strictly;193total
tensors and316new trainables are verified. The old neural Module path is
forbidden; no matching/frozen/sampler forward, optimizer or target/reference read
occurs. Cached protected sky/cab geometry is used for inference-feature correctness
only. The original profiling helper's seven lint findings are import/literal-dict
style; its frozen v1 code/plan/output remain exact and successful. Canonical
cleanup changes no numerical formula. No native work is repeated for formatting.

CUDA admission owner PID983491/create1794140085.47 is terminal and passed.
All seven initial native outputs are bit-exact with V183 EMA. Six nonzero
head CPU/GPU comparisons have maximum difference2.86102294921875e−6. Two real
four-image updates, mesh then mixed, compare all316 parameter gradients each;
maximum difference4.5299530029296875e−6. First-step context gradients are zero
because the final layer starts at zero; all four tensors have nonzero gradients
at update2. Both complete nine-term FP32 loss totals match independently.
All189 inherited tensors remain exact. Model/Adam/EMA/CPU-CUDA RNG restoration
between updates is exact with zero prefix replay. Counts16wrapper/frozen,
14network/projection,70sampler include seven old-component comparisons. Peak
CUDA allocation is about6.233GiB. Only mesh/mixed training inputs optimize;
protected inputs are parity-only. Probe checkpoints never initialize training.

Independent CPU inspection passes four raw/EMA loads,756 inherited-tensor
comparisons and four Adam states at clocks1/2. No forward or CUDA initialization
occurs. The new isolated training run starts from the published V183 EMA export,
with fresh head Adam/EMA, never the probes. Original owner
PID984348/create1794140356.75 is verified live and advancing. It uses the same
1,000 cached rows,900updates/3,600 noisy images/100ADC skips,nine terms,clean
mask and domain weights. Head LR.001 uses the same warmup/cosine schedule and
clipping1; head EMA starts at0. The frozen network/adapter retain historical
1,800/900 clocks. This adds training/capacity and freezing together, not a
same-total-budget loss-only comparison. Genuine row8 restore and five checkpoints
remain required. Fourteen independent training-audit CPU checks pass, and the
actual live-owner rejection occurs before Torch or checkpoint import.

Full quality remains unmeasured. The upcoming review must compare both new
endpoints on all822 cases, preserve V183/V181/V180/V178 and earlier strengths,
and independently verify all inherited V183 EMA outputs plus new wave additions.
Sequential FP32 additions must be audited in their actual order; regrouping
V169+old correction+wave need not be bit-exact. Both protected GFX families,
main sky/building/foliage/coarse fence and both fine cab ROIs/profiles/JPEGs
remain required. ISO100/AHD/JPEG references stay qualitative, not exact GT;
aperture/exposure/processing/moving subjects differ. Captures,JPEGs,siblings
remain excluded from training. Any quality report needs actual native viewing
and at least two unresized noisy/restored/exact constructed-GT triplets.

Storage recovery is explicit and separate from science. Across nine completed
V171/172/173/174/175/178/180/181/183 trials,47 launch owners were checked terminal.
Full hashing covers1,440 native output arrays. The plan selects300 duplicate
native paths and26 explicit private/public receipt-copy paths. Each replacement
has a full equal hash and same filesystem/owner/mode; atomic hardlinks retain
every original path and byte. Previous duplicate allocation is0.361801GiB local
and0.451988GiB external. Post-recovery free space is48.920654GiB local and
112.145180GiB external; concurrent activity can affect observed free change.
An independent postcheck rehashes all326 pairs and verifies shared inodes.
No source, checkpoint, training input, capture/JPEG, original or dataz path is
modified. Earlier deduplications are not rerun. Original inode/mtime metadata
remains in the frozen inventory; only storage identity changes. The new model
forecasts.52GiB external and.30GiB local above111.5/48.5GiB reserves, avoiding
old frozen-backbone optimizer copies because they no longer train.

All work uses cached data in the repository/external SSD. No new sensor/source
draw, parent/DINO call, RAW decode, original or unavailable dataz access occurs.
V183/V181/V180 and earlier completed quality remain current; V120 Small stays
the general recommendation. Fine-crossing recovery without false sky texture
is still unproven, and the full objective remains active.

[Architecture and native proofs](../docs/phase-wave-readout.md) ·
[Exact preparation evidence](../docs/results/v184-wave-readout-preparation-v1.json) ·
[Storage receipt](../docs/results/v184-completed-copy-storage-v1.json) ·
[Current completed quality](../docs/coherent-pair-evidence-comparison.md).
