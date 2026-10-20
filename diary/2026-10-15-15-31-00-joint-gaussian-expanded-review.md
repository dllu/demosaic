# Fixed joint Gaussian prior: expanded development review

Previous goal turn was progress: implemented and tested physical variance
stabilization and frozen Gaussian comparators, completed gray full panels and
RGB16 GFX outputs, and started an expanded fixed Joint8 evaluation after its
two-scene pilots. The old tool session was missing at turn start, but process
3613960 was authoritatively live, so it was monitored rather than restarted.
It has now exited; all three completion lines and summaries are present.

Joint8's frozen schedule is eight logarithmic strengths 4→0.5 with weight .05.
It uses verified pretrained RGB DRUNet, IEEE FP32 neural inference and float64
physical forward/inverse, explicit shot/read priors, no reference gains or
per-image parameter fitting. The recipe was frozen after the first-two-scene
pilots and before expansion. Protected final scenes remain untouched.

Complete known4/unseen5 measured-CFA PSNR is 53.81110/53.84615, compared with
RawNIND 54.06860/53.56220. The unseen mean gains .28395 dB, with scene-bootstrap
95% interval [−.04577,+.60362]; known cameras still trail by .25750 dB. AHD RGB
PSNR is 39.40695/38.43221, SSIM .921144/.915720. Unseen SSIM is lower than
RawNIND's .918380. Six of nine scenes improve primary PSNR, three regress.
The pilot's larger unseen win did not survive expansion at the same magnitude.

The 16-photo + 4-procedural screen (all four CFAs / seven conditions) completed
3,920 rows. Photo PSNR/SSIM: Joint8 34.23888/.954308, V16 32.41824/.937421,
RawNIND 27.70768/.826958. Joint8 minus V16 photo PSNR +1.82064 dB,
bootstrap [+1.39089,+2.33632]. Six of seven condition means improve; ADC-only
Malvar fallback loses 1.74000 dB. Procedural PSNR/SSIM 32.52197/.955809.
This is a small development screen, not the full 427 or protected final.

Published `docs/stabilized-gaussian-review.md` and its numerical receipt,
including separate gray64 and Joint8-16 synthetic scopes, complete real means,
scene deltas/bootstrap intervals, both earlier pilots, exact-GT native triplets,
matched real AHD references, and GFX foliage/fence. Every copied PNG hash and
512×192 geometry was checked; each contains three unscaled 160px panels. For
each source/ROI, noisy and reference panels are byte-identical across methods,
and conditioning/coordinates/display transforms match. Attribution retained.
GFX remains evaluation-only; original RAFs untouched and cached locally.

Native inspection: Joint8 preserves considerably clearer GFX mesh and leaves
than V16/RawNIND and removes most gray-phase checkerboard, but leaves remain
soft and isolated colored sky/shadow dots survive. Synthetic building boundaries
are strong; cloud/fabric fine texture is still smoothed. No promotion/SOTA claim.
Existing 214-test pass and Ruff pass remain applicable; no model source changed
in this turn. Metadata/image integrity and all report links were checked.

Started full 101.996 MP Joint8 GFX comparison with V16 and RawNIND, at 22:30 UTC:
session **21388**, Python PID **3616786**, script
`.cache/run_joint8_gfx_full.py`, log `.cache/gfx-gat-joint8-v2-full.log`, output
`/mnt/external/demosaic/evaluation/gfx-3879-3880-gat-joint8-v2-full/`.
Verify this specific live process before restarting anything. A completed report
will require RGB16 geometry/tags/ICC/code checks and full-frame native review;
context results do not prove full-frame quality/timing. Startup receipt is
`docs/results/joint8-expanded-review-and-full-startup.json`. No other process
was stopped; around 75 GiB available at startup, over the 12 GiB reserve.

Quality remains short of PROMPT.md; 10-second speed remains unmet. Next evidence:
full-frame output/timing, then the full photographic development comparison and
using this stronger prior to inform a faster trained DINO restoration model.
