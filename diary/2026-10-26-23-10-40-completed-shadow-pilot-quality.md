# Complete matched shadow pilot and inspect both train scenes

Recorded: 2026-10-26T23:10:40-07:00 (America/Los_Angeles).

Both matched1,000-update V126/V127 arms completed from V120, on90783 sources/
23ROIs at50% reviewed quota. The only arm difference is reviewed shadow fraction
0versus.5. V127 selected1,367 of16,000 targets. Both checkpoints retain finite91
model/EMA tensors and89 AdamW states at1,000; each has64 validation forwards.

Each endpoint ran86 new IEEE-FP32 calls on64 fixed shadow inputs,16 ordinary
materials, four main-GFX512 contexts and two extra-mesh768 contexts. V120's64
new shadow observations were already complete, with old controls reused. No old
inference, RAW decoding or noise resampling was repeated.

The policy has no useful measured gain here: mean shadow sRGB PSNR is25.89500dB
for V127,25.89620 for matched V126 and25.90197 for V120. V127−V126 is−.00121dB;
ordinary-material change is−.00356dB. Sixteen shadow groups are four sources with
multiple conditions/CFAs, not64 independent photographs. No full427-photo or
all-camera claim is made.

Actually viewed all28 comparison boards through seven unresized native sheets.
Fine fur and foliage remain soft; the extra green mesh remains largely erased
under nominal conditioning and weak/irregular under the fixed nearby profile.
The corrected extra pair isDSCF3842/DSCF3835, separate from3879/3880; ISO100
captures remain independent qualitative references, never exact GT.

An independent channelwise FP64/FFT audit verifies400 metric rows,100 summary
groups and6,625 scalar fields. All32,256,000 cell channel values across112 PNGs
match exactly. Published twelve native images, including two noisy/restored/GT
triplets per arm, and updated README/current policy/data/GFX docs. V120 remains
the recommendation and reviewed shadow exposure remains off by default.

V123's explicit7,751-update continuation now waits for its original56GiB launch
headroom after pilot evaluation finished; its original checkpoint, update/LR
horizon and absolute worker deadline remain preserved. No continuation update
has yet run at publication.

[Completed comparison and crop metadata](../docs/reviewed-shadow-pilot-quality.md) ·
[Training/evaluation/audit receipts](../docs/results/reviewed-shadow-pilot-quality-v1.json).
