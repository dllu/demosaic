# V103 material detail and fixed V104 endpoint queue

Recorded: 2026-10-23T09:55:31-07:00 (America/Los_Angeles).

Completed the original V10320k material comparison alongside V102 using current
source-frozen CPU FP32 code. Regenerated all12 observation tensor hashes exactly
to the original panel and verified all four IDs absent from90,872 training rows.
All12 V102 numerical cases and triplet PNGs replay exactly. V103 improves all12
PSNR,SSIM,chroma/gradient cases versus V101,but has slightly lower condition
means than V102:ADC39.24499 vs39.24687,ISO10040.62445 vs40.63881,high-noise
33.46767 vs33.46901dB. V103 wins4/12 PSNR cases,loses8; SSIM splits6/6.
No baseline change follows; these four selected sources complement full427 and
camera/flat-color/weak-carrier/GFX evidence,not replace it.

Actually viewed48 native160 cells across three four-source boards. Low-noise
bark and canopy are close; both still soften high-noise feathers,canopy and hairs.
Published24 unchanged triplets and two V103 ISO100 examples in the detail guide.
The source-and-condition key is required for parent PNG matching; publisher-v1
stopped before copying after source-only keys conflated conditions. Corrected
v2 verifies all12 original PNGs before publication. Raw receipts/inference remain
unchanged; there was no inference retry.

A one-shot CPU queue now waits on the exact original V104 production owner and
all three phase receipts,then compares only its original20k EMA with V102 on
these same12 observations. It uses current frozen loader source,checks resolved
architecture/model/EMA shapes and parent lineage,requires exited owners and
48GiB RAM/32GiB root/256GiB external headroom. Actual boundary checks reject
failed,wrong-plan,missing-phase,dead-nonterminal and terminal-live-owner states.
It performs no checkpoint search or automatic promotion. Source-frozen inputs
avoid the old interim reporter's loader-field mismatch.

Started an independent CPU-only V102 difficulty scan of2,395 new eligible
Commons training photos. Its four-source/eight-case actual probe passed with
finite outputs,unchanged model/config/RNG/inputs and no CUDA. Full ranking runs
on fixed native256 centre targets,ADC/high-noise priors and two CPU threads;
it leaves V104's original manifests unchanged. The reference-white screening
objective selects visual review candidates; high loss is not an exclusion rule.
Full scan and actual tail review remain pending at this entry's creation.

[Material report and native review](../docs/results/V103-final20000-heldout-detail-CPU-v1.json) ·
[Incoming source-scan readiness](../docs/results/incoming-source-loss-V102-CPU-readiness-v1.json).

Subsequent initial tail review:from the first64 completed sources,actually
viewed11 selected contexts,22 native256 source/target panels and one additional
native1024 flower view. All11 are new relative to the previous61 arrival-native
identities,for72 total. Retain10 hard sources,including two physical stained-glass
windows,underwater grain,hazy forest,sunset and architecture. Record the flower
03c499ad996e118d32cda5c50c22c8bae78610f6 as a future quality withhold for flattened/
smeared petal surfaces and conspicuous edge contours. This is an observed
source-quality decision,not an identified processing algorithm. Active V104
inputs and the earlier admission receipt stay exact. Full2395 ranking and
remaining tail review continue; freeze later decisions separately.
[Actual first64 tail review](../docs/results/incoming-source-loss-first64-native-review-v1.json).
