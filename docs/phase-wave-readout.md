# Direct phase-aware wave readout

**V184 has passed native CPU/CUDA checks and is training; image quality is
unmeasured.** The completed [V183 comparison](coherent-pair-evidence-comparison.md)
remains the current quality evidence. V183 recovers response lost by V181 while
adding quiet spatial error. The next architecture tests a separate path for
measured weak signals, with every V183 EMA tensor frozen.

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

The original full run starts from the published V183 EMA export, with fresh
readout Adam/EMA and the same 1,000 cached rows, 900 updates/3,600 noisy images,
100 ADC skips and nine losses/clean mask/domain weights. Head LR is .001 with
the same rowwise warmup/cosine schedule and clipping1; its EMA clock starts at0.
The inherited network/adapter remain at1,800/900 historical updates. Additional
training, capacity and freezing change together, so this is not a matched
same-total-budget loss comparison. Genuine row8 restoration and five checkpoints
remain required. Fourteen CPU audit checks pass, and the actual live-owner gate
rejects a premature audit before Torch import.

Full quality review must verify the inherited V183 EMA replay on all822 cases,
then reconstruct each new native output as inherited RGB plus its added wave
residual. V169's older RGB remains separately recorded. The three sequential
FP32 additions need not equal a regrouped two-term sum; the new audit must
respect that arithmetic. Both new endpoints, earlier useful models, the complete
quiet/absent/ADC controls and both protected GFX scenes remain required. Real
ISO100/AHD/JPEG references are qualitative, not exact GT; captures, JPEGs and
siblings remain excluded from training. Originals and unavailable `/mnt/dataz`
remain unused. No trained improvement is claimed before review, actual native
inspection and unresized noisy/restored/exact constructed-GT triplets.

[Implementation](../src/demosaic/late_phase_wave_readout.py) ·
[Native CPU profile](../scripts/profile_phase_wave_readout.py) ·
[Readout state management](../scripts/phase_wave_training_state.py) ·
[CUDA admission](../scripts/admit_phase_wave_readout.py) ·
[Training](../scripts/train_phase_wave_trial.py) ·
[Training auditor](../scripts/audit_phase_wave_training.py) ·
[Exact preparation evidence](results/v184-wave-readout-preparation-v1.json).
