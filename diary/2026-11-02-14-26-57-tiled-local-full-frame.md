# Tiled local harmonic refinement reaches full GFX frames

Recorded: 2026-11-02T14:26:57-08:00 (America/Los_Angeles).

The fixed local phase-harmonic correction now works on complete images through
`demosaic infer --phase-harmonic`. Its package implementation preserves the
historical experiment scripts and receipts. The source tree now has70 modules;
the old69-module model/training snapshots remain unchanged. The new module and
CLI were copied into a frozen execution tree; all70 current files still match
those executed bytes. Neural model and checkpoint loading equations did not change.

The regular256-pixel correction grid uses even sensor coordinates, including the
final covering patch, with default native stride128. Odd/small borders repeat
complete Bayer cells. Each patch retains the fixed sigma32/shrink4/cap3/apron32
policy. Tapered corrections are averaged with inactive windows in the denominator;
the exterior image retains its fade. Fits are float64; full-image accumulators and
output are float32. This is optional and does not change default inference.

The larger-context probe found clear window dependence. Strides192/128 both
retain some mesh, with no universal winner. Main building windows can also
activate, so the centred-patch statement that building/foliage remain unchanged
does not extend to all other origins. The package port matches2,359,296 patch
values exactly and twelve whole512/768 context results within float32 rounding
(max5.9516e-8 normalized). Four-CFA seam/odd-boundary/known-wave tests plus prior
inference/export/operator checks pass45 tests. Twelve1024x1536 uniform cases
have924 windows and zero changed parent pixels. The three physical Poisson–Gaussian
noise realizations are shared across four CFA labels; these are not twelve
independent draws, and the parent is the exact constant field, not a neural output.

Three actual complete8746x11662 GFX frames finish with canonical V1435k EMA
SHA256 `96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`:
main DSCF3879 fixed historical Haar, DSCF3842 nominal and DSCF3842 nearby-Haar.
Each uses neural512/B4/overlap64/IEEE FP32 and6188 correction windows. Actual
counts:390 root/DINO forwards,1560 native neural tiles, three locally cached RAF
decodes, zero control forwards/training updates. Models/backbones remain unchanged;
all input arguments are unchanged by inference. All130 complete main input batches
exactly match the previous V120 full-frame witness, without rerunning V120.

Neural/CPU correction/CLI seconds were164.21/109.73/309.36 main,
163.92/90.81/289.01 nominal mesh and165.59/107.95/309.95 nearby mesh. These are
instrumented shared-device observations, including input witnesses and float-array
copies; CLI includes RAW/model load and exports. This is not a speed ranking or
the10s target. Active correction windows are1103/133/1111 respectively. The
method is now practically usable on100MP, with substantial extra CPU cost.

Both mesh priors show clearer soft diagonals, especially the right crop. The
crossing family is still weak; response is patchy and origin-dependent. Main
V120/V143/local differences are small and foliage stays painterly. Full correction
changes foliage/building/larger-fence by0.066/0.552/0.693 DN16 RGB RMS; these are
added fields, not exact-GT errors. A2.88MP sky box selected from the input-only
locator before inspecting full outputs retains every parent pixel. Three additional
native sky views are quiet. The strongest main added-field160 crop is a bright sign
at[2720,1760],678.41 DN16 RGB RMS; max single-pixel change5032.09 DN16. A shared−2EV
view reveals its unclipped detail. Lettering stays soft and edge changes do not
establish correct recovery. The original partial-texture spill remains a limitation.

All917,962,668 linear RGB16 channel values verify exactly against saved FP32
clip/round/orientation. Complete sRGB16 files agree with independent float64
rendering within1 output DN;16-bit/ICC tags verify. Independent direct rendering
and unchanged-native-cell checks cover6,220,800 PNG channels. All21 published
boards were actually viewed on six native contact sheets: both main scenes/priors,
both camera JPEGs, strongest fields, wider sky and two reused active/inactive
procedural exact-GT triplets. The real ISO100/AHD/JPEG references remain explicitly
not exact GT; crop pixels never resize. README now displays the actual full-frame
nearby-prior mesh/JPEG comparisons, with the two V143 faint photographic triplets
retained. Documentation covers the optional CLI, useful gains, cost and remaining gaps.

Preserved unsuccessful preparation work: first parity limit was tighter than
float32 rounding in bright pixels; second audit passed an extra noise metadata key;
first frozen CLI output path was outside its local safety root and was rejected
before RAW/model loading; first triplet script iterated a method dictionary as rows.
Corrected versioned operators/receipts retain those failures. They add no neural
forwards or RAW decodes. The execution tree writes within its own permitted root.

Evidence root: `.cache/quality-20261102/phase-harmonic-inference-v1/`.
Public report: `docs/phase-harmonic-inference.md`;21 PNGs and complete source/ROI/
checkpoint/noise/WB/matrix/display provenance are in
`docs/images/phase-harmonic-inference-v1/manifest.json`. Byte-preserved execution,
input witnesses, exports, contexts/flats and publication receipts are in
`docs/results/phase-harmonic-inference-*-v1.json`.

The improvement goal remains active. Stable weak-detail recovery across origins,
the missing crossing family, reduced partial-texture spill, broader V143 full427/
camera quality and speed remain unresolved. No source DAS access or original-file
modification occurred.
