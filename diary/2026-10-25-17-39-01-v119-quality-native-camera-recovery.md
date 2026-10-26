# V119 complete quality review and retained native-camera recovery

Recorded: 2026-10-25T17:39:01-07:00 (America/Los_Angeles).

V119 completed all eight endpoint stages, independent NumPy audit, three
full saved-output contrasts/local-band analyses and both complete RGB16 export
checks. The [current report](../docs/v119-quality.md) and
[bound evidence](../docs/results/v119-quality-complete-v1.json) replace pending
status in the README/current guides. V119's independent photo mean37.03831dB
improves .06131 over V115 on420/427 sources, but known-camera mean54.10063 loses
.22342dB, including .55996 on D60. Unseen54.00742 is nearly unchanged. Weakest
high-noise photographic gain .36422→.36523 is small. The largest ADC-only color
bias is2526.70DN16 in a bright yellow BGGR fixture; the smaller magenta case is
not the maximum. V114 general, V115 known-camera and V117 photo choices retain
useful strengths. This combined cleaned90791/paired83/additional20k trial does
not isolate a corpus or paired-data cause.

Nine matched material/GFX boards, two new bark/egret exact-synthetic-GT
triplets, four measured-camera triplets and two highlight triplets were viewed.
Fine feather/foliage/neon structure remains soft, and the separately completed
DSCF3842/3835 green-mesh review has no clear gain over V115 under either matched
profile. The corrected ISO100 source is DSCF3835; main3879/3880 remains the
standing pair. All independent ISO100/AHD references remain labeled not GT.
The private render plan's informal bark/canopy wording was wrong for its second
fixed ID, which is egret; source/ROI/input bytes were unchanged. Public text
names the actual photo.

The original native-camera collector saved960 joint predictions, then failed
before any RawNIND call: expected wrapper hash3304... was compared with bare
network94a3.... A CPU check verifies all46 bare network state tensors exactly
against genuine checkpoint3d8d.... Correct the hash scope, retaining the check.
A separate recovery freezes the same numerical library, verifies/relinks all960
completed predictions, and runs only the missing240 reference calls. Original
failed sources/logs/receipts/arrays are preserved. Hooks bind per-method state;
new per-method receipts precede final collection serialization. Recovery and CPU
analysis completed, without new joint forwards/noise/RAW/training.

The [native-camera comparison](../docs/native-camera-development.md) now covers
all20 contexts/11 withheld captures, three added-noise priors and four CFAs for
five methods. All12 native boards (420 cells) were actually viewed. Joint
outputs retain much finer grass, rail grain, mortar and lettering than RawNIND;
high-noise foliage still softens. V119 improves slightly over V115 but stays
below V117's three condition means. High-noise camera-RGB gain over RawNIND is
3.69779dB, specific to these binned low-noise reference estimates plus added
noise, not exact scene GT or a real high-ISO superiority claim.

[Publication verification](../docs/results/v119-quality-publication-verification-v1.json)
checks235 artifact bindings, primary reaggregation,132 core native160 panels,
all32,256,000 channel values in420 native-camera board cells, and ten triplets
exactly against those boards. The two new photo triplets independently agree
within one DN8 at only four of460,800 values (floating render rounding), with
noisy panels exact. Full RGB16 verification retains460,800 exact channel values.
The52-endpoint PSNR history adds V119 while preserving all51 earlier points and
all earlier registry/receipt bytes; the updated graph was viewed. Its dashed
reference remains the useful V114 general choice. Nineteen recovery/archive
checks and eight version-history tests pass (27 total), Ruff passes, changed
Markdown local links resolve and git diff whitespace checks pass.

An author-source release check pins DFENet commit6a3c3c5... (2025 preprint,
later journal release). MIT source is present, but the inspected tree/README
provide no genuine checkpoint and test pretrain_network_g is null. No neural
comparison or training is claimed. File hashes are retained in the
[release-availability receipt](../docs/results/dfenet-release-availability-v1.json).
The prepared90787-source/14-ROI future bank and opt-in source-loss observer
remain available for further quality trials. Overall state-of-the-art quality,
broad real-capture superiority and100MP/10s remain unmet; this is concrete
completed review/recovery progress, not goal completion.
