# V174 spread sample initialization results

Recorded: 2026-11-07T17:11:53-08:00 (America/Los_Angeles).

V174 completed the matched V172 schedule with only five offset bias vectors
changed at initialization. All seven actual initial losses and the mask exactly
reproduce V172; the 183 other state tensors and all 96 existing neural sources
are unchanged. The real step-8 model/Adam/EMA/CPU+CUDA RNG restoration passes.
The 1,000 cached rows yield 900 optimizer updates, 100 ADC skips and 3,600 images.
Both strict endpoints and 141 final Adam states pass. No new source/noise,
parent/DINO or original/dataz work occurred.

EMA quiet total RMS falls 0.12–0.17% versus V172, spatial RMS 0.04–0.08%, DC
color error 0.36–0.43%. These are small gains. Mesh response falls 0.25% to
3.868% of constructed GT amplitude, and natural band response falls
0.016–0.023%. Full-flat means change +0.008/−0.072%; coarse means worsen
0.020/0.004%. Raw quiet total RMS instead rises 0.12–0.19%. Native crops look
close to V172, with missing mesh crossings and broad quiet/flat mottle. Keep
V172 as the balanced matching baseline; V173 quiet/spatial, V171 standalone-flat,
V161 learned-detail and V120 broad-photo strengths remain useful.

The six captured primary EMA inputs retain coarsest p90 sample distances about
90.7 native pixels, versus 12.04 in the earlier V172 probe. All 30 saved FP32
pre-tanh fields and their input/prediction bindings pass independent checks.
These are reconstructed positions, not causal distant-information measurements.
The initialization also changes tanh conditioning. Wide positions did not yield
a useful detail gain in this single-seed, 900-update experiment.

All 822 cases complete at both endpoints: 1,644 compositions, 1,500 actual
candidate matching calls, 7,500 nested samplers, 1,644 exact V169 replays and
144 exact ADC identities. All 6,576 input fingerprints pass. Posthoc full-array
checks cover 36 selected cases, 72 RGB and 72 residual arrays; other cases keep
streamed scores/fingerprints and in-process checks. Actual training plus native
admission plus review totals 2,404 candidate CUDA matching calls. The six V172
probe calls bring new matching work to 2,410, with zero CPU matching calls.
All four matching-phase owners are terminal; no scientific phase failed or
prefix repeated. The focused selection has 133 CPU tests, including ten new
geometry/state/RNG/invalid-initializer cases.

All 60 figures were actually viewed in 15 original-detail sheets, including
12 native noisy/restored/exact-constructed-GT triplets. Main DSCF3879/3880 sky,
building, foliage and coarse fence and extra DSCF3842/3835 cab windows remain
qualitative tests. Aperture, depth of field, motion and independent processing
prevent treating their references as exact GT. Capture families/JPEGs/siblings
remain excluded and originals read-only. The offline viewer retains native
160×160 pixels, with all 240 browser crops checked exactly.

A separate V175 preparation diagnostic removes the entire matching path at the
last fusion for six selected V174 EMA inputs, evaluating only six head and six
tail convolutions. No matching/frozen/sampler/parent forwards or training occur.
The difference is 18–84% of the full added correction's RMS; that correction is
only 0.20–0.22 DN16 RMS. Six saved local corrections and FP32 compositions pass
independent checks. This rejects complete bypass on these inputs, without
isolating far samples or proving why detail is missing. No V175 model or
all-case ablation is claimed. Its 12 convolution calls are separate from V174's
matching counts. Future work should test useful correspondence and correction
amplitude with paired detail/absent controls, rather than assume wider positions
or longer training solve the remaining loss.

The README now keeps the representative comparisons and useful model choices
in 175 lines; detailed history remains in docs and this diary. All old receipts,
experiment evidence and frozen sources are preserved.

[Completed report](../docs/spread-sample-matching.md) ·
[Exact evidence and checkpoint exports](../docs/results/v174-spread-matching-final-v1.json) ·
[Native viewer](../docs/images/v174-spread-matching-v1/native-viewer.html) ·
[Browser pixel verification](../docs/results/v174-native-viewer-verification-v1.json) ·
[Publication verification](../docs/results/v174-spread-matching-publication-verification-v1.json) ·
[V175 functional probe](../docs/results/v175-local-shortcut-diagnostic-v1.json).

The broader goal—fine low-contrast detail without false sky structure—remains
open. No new full-frame/100MP timing or combined quality claim is made.
