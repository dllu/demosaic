# Complete the first32,000-example RAW review and isolate precision learning

Both fresh B4 RAW models remain unpromoted after their actual8,000-update
boundary (5% of the original160,000-update horizon). The complete frozen v2
review finished and its controller1100129/1792271282.32 and final child exited.
No quality continuation or production precision/architecture change is running.

Photo sRGB PSNR is 27.670870 for V71 without DINO and 27.765151 for V70 with DINO, compared with
bilinear27.554810, working V43 34.899343 and mature V63 35.933087. The matched
DINO gap is+.094281dB,95% source interval[+.086437,+.101443]. Known/unseen
measured-CFA scores remain far below mature controls. These comparisons do not
isolate architecture against the pretrained RGB models or establish convergence.

The full frozen protocol includes648 known,810 unseen,111636 full-panel and2240
analytic cases,128 selected CPU colors,4704 new hue predictions, six full GFX
restores/twelve RGB16 TIFFs, three cached cameras and supplementary neon/platform
crops.108 metric comparisons,27 classical witnesses and81 source sensitivities
completed. Artifact checks cover76 PNGs,32 F32 arrays, eight neural and four
RawNIND RGB16 files. The actual native visual review is a selected subset:
14 unchanged originals published with complete sidecars, plus six additional
viewed hue triplets. Fresh models retain heavy grain in photo/CPU/GFX foliage
and fence; mature references remove far more noise but still have detail/color
failures. GFX full-frame eager FP16 timings are51.03/53.64s for V71/V70;
V43/V63 are31.45/31.61s and RawNIND adapters14.60/12.88s in this run.

At bright saturated hue-grid settings, RAW color mean bias is lower but noise
is much higher: V70 centered RGB RMS.022387 versus V63.001839 at saturation.98,
peak.9/ISO12800. Do not interpret mean-bias improvement alone as useful denoising.
The protected final16 scenes/57 RAWs and private GFX scene/siblings remain outside
training/final scoring. README crops stay V43; the new negative report is linked.

The isolated CPU fixed-training-fixture check completed: actual V71 EMA copy,
one generated32px four-CFA example,128 fresh AdamW updates, MSE ratio.146292;
all852 parameter tensors changed. No learned weights saved. Its receipt/source
and fixed fixture remain under packed-isotropic-fixed-training-CPU-v1.

A frozen GPU diagnostic waited for the exact complete-review owner to exit,
then ran two independent actual V71 EMA copies on the same synthetic fixture.
FP32/BF16 MSE fell to2.2470345e-5/2.2139706e-5 from1.55947e-4. Initial EMA
BF16/FP16 maximum error versus GPU FP32 was1.25468e-4/1.74791e-5. Gradients and
outputs were finite; raw and EMA were both weak initially. This excludes a
universal BF16 failure on that fixture, not poor varied-photo/low-signal learning.
No held-out photo or benchmark fixture was optimized, no learned weights saved,
and original quality checkpoints remained exact. The diagnostic1681090/
1792272683.4 exited. Two earlier wrapper imports failed before operator execution:
resolving the venv symlink bypassed its packages; archive operator.py then
shadowed stdlib operator. Retained both failed launch logs; actual successful
launch used the absolute unresolved venv path and Python -P. No failed launch
initialized CUDA or trained. No automatic restarts or quality training reruns.

Public report: docs/packed-isotropic-first32000-review.md.
Public receipt SHA256: 7c511959d0028ebb6a84b80877f05e7f0cbbfab0fbce22f6c2a80dfe09a9b4ce.
The README, architecture status and pipeline report now reflect completed8k
boundaries and weak quality rather than still-running training. The requested
pipeline changes are already measured:4x/geometry/2x gives+.50990dB, selected-only
loading reproduces old logged observations, RGB B16 is faster than B4, while
this architecture's actual sweep selects B4.

The existing Commons downloader3989576/1792107890.18 remains alive; SSD free was
620.6GiB with the existing512GiB reserve. No duplicate downloader or new source
admission. No owned GPU job remains. Further work should test learning on varied
production-training observations before assuming more original-horizon training
or changing conditioning/architecture; this next experiment is not yet queued.
The SOTA/large qualitative RawNIND advantage/10s objectives remain unmet.
