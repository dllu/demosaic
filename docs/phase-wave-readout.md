# Direct phase-aware wave readout

**V184 has completed training, both endpoint reviews and actual native inspection.**
The [completed comparison](phase-wave-readout-comparison.md) finds **9.60% raw /
15.96% EMA higher mean mesh response versus frozen V183 EMA**, reaching4.865% /
5.148% of GT amplitude. Quiet spatial RMS rises **0.76–0.94% raw / 1.81–2.35%
EMA**, with extra false striping. Raw has the lower quiet cost. Real fine
crossings and broad mottle remain unresolved. Retain this stronger-response
path alongside [V183's intermediate](coherent-pair-evidence-comparison.md),
V181's quieter and earlier useful options; V120 Small remains the general choice.

V180/V181/V183 route 80 local wave coordinates through a 39-channel adapter
and the shared matching network. V184 adds a direct readout from the same
measurements. A shared pointwise 6→16→12 MLP conditions complex mixing weights
on the six nonoscillating power/cross/frequency coordinates. It mixes both
measured complex waves separately for each camera-RGB color, then explicitly
transports their phase to each native 2×2 subpixel. Both selection directions
and all four ranks use the same 316 parameters and contribute equally. This
uses the principal-band frequencies; it does not resolve their native aliases.

The readout's final 204 weights/biases start at zero. Its 112 hidden-context
parameters use a fixed local seed without changing the global RNG. All 189
inherited V183 EMA tensors stay frozen and in evaluation mode. Native local
noise RMS scales the added residual; local zero supplied variance retains the
inherited output exactly. Zero wave coordinates give no RGB residual even
after contextual biases change. These algebraic identities do not protect
an actually flat noisy field, whose wave measurements are nonzero. Interpolated
coefficients are features, not calibrated confidence or SNR.

Freezing the inherited model prevents new flat supervision from updating its
detail parameters. It does not establish that the new path can recover a weak
crossing, distinguish a selected noise wave, or improve quiet regions. Global
selection, local-window support spreading, coarse-grid interpolation and aliases
remain limitations. Shared readout parameters can still trade detail against
false structure. This is a hypothesis to test with trained outputs.

All **36 focused CPU tests** pass: 31 transport/derivative/routing checks and
five optimizer/EMA/state checks. An independent NumPy implementation checks
every native subpixel, both complex mixing components, rectangular/negative/
Nyquist bins, all four Bayer layouts, rank permutation and finite-difference
parameter derivatives. Tests also check exact zero initialization, all inherited
parameters frozen/eval, mixed local ADC routing and genuine state restoration.

The native CPU proof uses six cached RAW/variance/CFA cases: training mesh,
photo, mixed structure, flat, protected main sky and protected cab geometry.
It checks **12,779,520 readout values** against independent NumPy with maximum
absolute difference 2.32e−6 in unscaled head units, within the fixed combined
absolute/relative tolerance. All 189 inherited tensors load exactly, with 193
total state tensors and only four trainable tensors. Old Module forwards are
forbidden; no matching/frozen/sampler inference, optimizer or target/reference
interpretation occurs. The canonical profiling helper later receives only
literal-dictionary/import formatting cleanup; its actual frozen v1 source,
plan, output and earlier lint log remain preserved.

The real CUDA admission completes **seven bit-exact initialized output
comparisons** against V183 EMA and six nonzero standalone readout CPU/GPU
comparisons (maximum difference 2.87e−6). Two four-image updates, mesh then mixed,
verify all 316 parameter-gradient coordinates against CPU at each update;
maximum difference is 4.53e−6. The first hidden-layer gradients are zero as
expected from the zero final layer; all four tensors have nonzero gradients
at the second update. Every nine-term FP32 loss total matches independently.
All 189 inherited tensors stay exact. Model/Adam/EMA/CPU-CUDA RNG restoration
between updates is exact, with zero prefix replay. Peak CUDA allocation is
about6.23GiB. Counts are16 wrapper/frozen,14 network/projection and70 samplers,
including the seven old-component comparison forwards. Protected sky/cab inputs
are parity-only; only mesh and mixed training batches can optimize.

Independent CPU inspection strictly loads both raw/EMA probe states: four
strict loads, 756 inherited-tensor comparisons and four Adam states at clocks
1/2. No Module forward or CUDA initialization occurs. Probe checkpoints never
initialize training.

The original full run completes from the published V183 EMA export, with fresh
readout Adam/EMA and the same 1,000 cached rows, 900 updates/3,600 noisy images,
100 ADC skips and nine losses/clean mask/domain weights. Head LR is .001 with
the same rowwise warmup/cosine schedule and clipping1; its EMA clock starts at0.
The inherited network/adapter remain at1,800/900 historical updates. Additional
training, capacity and freezing change together, so this is not a matched
same-total-budget loss comparison. Genuine row8 restoration resumes at9 with
zero prefix replay. The terminal independent audit passes all900 nine-term
FP32 totals, masks/LR/EMA bindings and five strict checkpoints, including1,890
inherited-tensor comparisons and final head Adam900. Peak training CUDA allocation
is6,682,433,024bytes. Fourteen CPU audit checks and actual live-owner rejection
before Torch import remain preserved.

Full quality review completes all822 cases at both endpoints:1,644 wrapper/frozen,
1,500 network/projection/readout and7,500 sampler calls. Every inherited V183 EMA
output and every V169 frozen output replay exactly, with144 ADC identities.
Independent audit checks6,576 input fingerprints,72 native RGB+72 wave arrays,
53,772,288 ordered addition channels,510 ordinary metric scalars plus72 wave-RMS
scalars (582 total),278Decimal means and750 exact raw/EMA input-evidence pairs.
[Scalar-count clarification](results/v184-native-scalar-count-clarification-v1.json).
The new output is inherited RGB plus wave; regrouping V169's older correction
would change FP32 rounding. Twelve quality-audit CPU checks cover that order
and the new replay/counter contracts. No spectrum/confidence calibration follows.

Reduction retains21 methods/17,262 rows/38 contrasts/1,386 cells,2,869Decimal
means and13,896 paired checks. Both primary contrasts use frozen V183 EMA;
36 contextual contrasts preserve all19 older methods. The marked full structural
fixture uses old EMA values and establishes no V184 quality. Its15,336 paired
checks include shared old correction-RMS fields that are not comparable to the
actual new wave-only RMS. Fifteen comparison tests pass after correcting two
stale raw-role test labels; first source/log remain preserved. Reducer v2 changes
two display titles and its seal filename only, with numerical bodies exact.

All60 native figures/12 triplets in15 original-detail sheets were actually viewed.
Constructed mesh modulation strengthens, but weak crossings remain missing.
Both fine cab windows/profiles remain soft/incomplete. Quiet step/bar/stripe
ROIs show extra false regular structure, sometimes faintly at normal contrast;
broad colored mottle persists. Main sky at exposure4 looks smooth. Ordinary
boundaries and exact ADC output survive. These costs keep the joint goal open.

Two strict193-tensor CPU exports bind training checkpoint
`b99b2c72f0db0026cdbe9d8f1709e4fffd40b4412e1d9b5280874cb5b6e03576`:
raw `faf7efba78da5e6e3df13a48819c6659fb082cf3f42ae5b7e2de7fb4e1f6a51e`,
EMA `d454a04c7c3e090912592d0ff34036e54741c956f84b894363f2eba399c11d8b`.
The actual twelve-state viewer preserves all ten older method entries and defaults
V183 EMA/V184 EMA. All480 browser crops/36,864,000RGB channels match source PNGs
exactly;96 raw/EMA metadata pairs,click/F flipping,navigation and no JS errors pass.
[Exact completed evidence](results/v184-wave-readout-final-v1.json) ·
[Browser verification](results/v184-wave-readout-native-viewer-verification-v1.json) ·
[Publication verification](results/v184-wave-readout-publication-verification-v1.json).

Both protected GFX families, all main sky/building/foliage/coarse-fence views and
both fine cab ROIs/profiles/JPEGs remain in the report, with12 unresized noisy/
restored/exact constructed-GT triplets. Real ISO100/AHD/JPEG references are
qualitative, not exact GT. Captures,JPEGs,siblings stay excluded from training;
originals and unavailable `/mnt/dataz` remain unused. The reused development
suite supplies no blind or seed-uncertainty estimate. No new source/noise,
parent/DINO or RAW decode runs, and no successful scientific prefix is replayed.

Publication initially stops at its space guard before exports/output creation.
[Verified completed PNG sharing](results/v184-completed-render-copy-storage-v1.json)
preserves1,416 original/public paths and bytes from21 completed publications,
with69 launch owners terminal and345.203MiB duplicate allocation recovered.
[Readmission](results/v184-publication-storage-readmission-v1.json) rehashes all
pairs and current worker sources before successful publication. The two failed
space checks remain preserved. Public V184 receipt/PNG paths share closed private
artifacts; no redundant data copies or scientific reruns are introduced.

[Implementation](../src/demosaic/late_phase_wave_readout.py) ·
[Native CPU profile](../scripts/profile_phase_wave_readout.py) ·
[Readout state management](../scripts/phase_wave_training_state.py) ·
[CUDA admission](../scripts/admit_phase_wave_readout.py) ·
[Training](../scripts/train_phase_wave_trial.py) ·
[Training auditor](../scripts/audit_phase_wave_training.py) ·
[Exact preparation evidence](results/v184-wave-readout-preparation-v1.json).
