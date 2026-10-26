# Fixed GFX conditioning and V121 ADC-tail inspection

Recorded: 2026-10-26T15:14:47-07:00 (America/Los_Angeles).

Confirmed the corrected additional train reference is DSCF3835 ISO100, not a
second DSCF3842. The config, cached RAF/JPEG, published green-mesh comparisons
and standing holdout already use the corrected source. DSCF3879/3880 remains
the main six-region qualitative test. No source disk was opened or modified.

The completed V120/V121 nominal-profile main-GFX outputs cannot isolate model
changes against older Haar-profile outputs. The current ADC-floor-aware
estimator legitimately reports insufficient intensity span here; reverting its
physical clipping treatment just to reproduce an older fit would conceal this
difference. Added an explicit fixed-profile option to `report_raw_pair.py`,
supporting restore-CLI wrapped/direct JSON profiles, early reliable/finite/
nonnegative validation and optional camera/ISO checks. Supplied profiles skip
estimation and archive exact bytes/hash with separate provenance. The effective
three-field conditioning object remains compatible with strict comparisons.
Default automatic estimation/fallback and existing outputs remain unchanged.

The collector now validates all five model arguments before every forward
against a declared witness, including optional shape/dtype. GFX stage plans can
bind a noise profile. Numerical target/context checks remain in place. Active
training/evaluation/report/mesh frozen code was not edited or restarted.

Prospectively froze a new V120/V121 historical-Haar full-frame operator with
shot .0014635775921166604 and read 1.0715704128646712e-6, copied from V119's
original input-only receipt. This is a distinct input operator, not a repeat of
the completed nominal-profile experiment. The fixed budget is 130 B4 root and
encoder calls per endpoint, 520 native tiles each, two shared cached RAW decodes,
zero estimator calls, zero training or optimizer work. All 130 complete five-
argument inputs must match V119 before NN execution. No parameter sweep or
reference fitting. Neural physics is byte-identical to the original V120/V121
quality workspace; outputs stay inside the new internal frozen work directory.

Preserved the first launch, which stopped before loading any checkpoint or RAW:
its old shared checkpoint-cache path was outside the new frozen safety root.
No root/encoder/noise/RAW work occurred. Created v2 with a cache inside its own
work/artifacts, keeping the original failed source/plan/claim/log intact. There
is no automatic retry. Run roots are
`.cache/current-quality-20261023-v1/V120-V121-fixed-Haar-full-GFX-v{1,2}`.
The v2 plan SHA256 is
`1f9d0defd5564f17cc9df3761fe706cbafcf6a8e81e2725fdc217194f6b5b387`.

Also inspected two retained analytic ADC cases, selected after the complete grid
as each model's worst channel-mean bias. This is adverse development evidence,
not representative selection. On saturated yellow BGGR case1017, V121's green
mean error is +1645.36449DN16; 98.194% of RGB squared error is in channel-mean
shifts. Green pixel-error 1st/99th percentiles are +1002.228/+2077.332DN16.
Original observed-CFA phase means stay within .395DN16. This is broad model
bias, not an isolated hot pixel or quantization-sized input error. V120's maximum
channel-mean error on the same case is36.02153DN16. V120's own worst pink RGGB
case792 is55.52459DN16; V121 is18.47590 there. This does not identify a training-
source cause or justify applying a new output correction.

Actually viewed the native eight-cell ADC board. Clipped sRGB8 previews look
similar, without an obvious large blotch; the linear measurements reveal the
error the preview can hide. All source/prediction/supervision hashes, selected
metrics and encoded native pixels verify. Published four native triplets plus
the board and immutable receipts, without Torch import, NN, RAW or new noise:
`docs/results/v120-v121-ADC-tail-v1.json` and
`docs/results/v120-v121-ADC-tail-native-review-v1.json`. Original pending-view
receipt bytes remain unchanged; the separate review receipt closes viewing.

Fixed remaining V114-as-general-default wording in usage/README setup and the
ADC guide, while retaining its measured optional ADC export. V120 remains the
general choice and active V122/V123 retain their controlled V115 parent.

Validation: 75 focused profile/report/collector/material tests and 55 related
full-frame/reference/frequency-queue tests pass. The latter first failed during
collection without the documented scripts PYTHONPATH; rerunning with
`PYTHONPATH=.:src:scripts` passed. Ruff checks and formatting checks pass on
changed Python code (the collector retains its existing formatting).

The v2 run subsequently completed its exact finite budget: 260 root and encoder
calls,1,040 tile observations, two cached RAW decodes and zero estimator calls.
Every input fingerprint equals the archived V119 sequence for both endpoints;
both model hashes equal their completed nominal-profile operators. Stage result
SHA256 is`0585cb5f37662f1511f617835b7b1b2b19af9ed0264211cefb25e9e8ceee34a0`.
The separate CPU review imports no Torch, performs no inference/RAW/noise work,
and verifies four full-frame TIFF hashes/types/shapes and921,600 exact native
linear-camera FP32→RGB16 values. Original sRGB quantization is not independently
recomputed. Inference observations329.42/263.45seconds overlap live V122 training
and are not a controlled speed comparison.

Actually viewed all ten native boards: three matched model contrasts
V115→V120,V119→V120,V120→V121 and the two same-weight nominal/Haar contrasts.
Differences remain subtle: larger fence/building geometry is coherent and sky
quiet, but foliage is painterly and neon markings smear. Neither model/profile
shows a clear large recovery of the missing fine detail. Separate ISO100 f/5.6
AHD exposure remains approximate, never GT or a PSNR target.

Published byte-identical boards, four native foliage/fence triplets, the fixed
historical profile and immutable CPU/export/native-view receipts. All132 native
cells /10,137,600 encoded channel values verify exactly. Original pending-view
machine receipts remain unchanged; the separate publication receipt records
actual viewing. Updated README real-GFX examples to V120, the main gallery and
current model/training/experiment/review guides. Matching-profile full-frame
review is complete; current automatic calibration stays unchanged, with the
historical profile disclosed as a comparison convention rather than new camera
calibration. The V120 selection/checkpoint and all PSNR/history values are
unchanged. Its fixed selection-basis snapshot still records what was known at
the original decision time; current guides record the later completed review.

Public receipts:
`docs/results/v120-v121-fixed-Haar-GFX-v1.json` (byte-exact CPU result),
`docs/results/v120-v121-fixed-Haar-GFX-native-review-v1.json`
(SHA256`2915817f199ce9febc50b67398123c693b19af00bc0fb5b1d68a349d5cf49ca4`).
CPU review SHA256 is
`ff663a6baa52e2b1c55a12022c8ab319e4e226e881149c801d0e7b9cc3117c36`.

No primary/analytic benchmark, old control, nominal operator or additional
DSCF3842/3835 mesh inference was repeated. Live V122 training and its original
V123/evaluator/audit/report/mesh dependencies continue without signals or source
changes. Broad real-photo superiority and the100MP/10s target remain open.

Final publication verification checks80 new public/original file bindings and
393 local links across the ten edited current documents. Every copied asset
remains byte-identical; all focused130 tests passed. Receipt:
`docs/results/v120-v121-fixed-Haar-publication-v1.json`
(SHA256`d167d311fa2f70cbab5e334a6734aa6102d4f7464d6d953c63f53ac8c3438254`).
At the final live-job check, V122 was at step19,200; its original controller,
quality/audit/report/mesh owners were still in their expected states. Available
RAM was58.3GiB; internal/external free space655.5/222.9GiB, above the declared
reserves. V123 had not started. Future90784/20-region data remains untrained.
