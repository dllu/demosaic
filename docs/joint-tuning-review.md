# Joint tuning versus refiner-only continuation

V18 and V19 start from identical V16 step5000 EMA weights and use the same
architecture, seed 43, data proportions, original losses, LR 3e-5 and planned
5000-step schedule. V18 updates restoration and fine RGB correction; V19 updates
only the fine RGB correction. DINO backbone weights remain frozen and the coarse
branch is disabled in both. No protected test or GFX qualitative scene training.

At the first 1000-step review, all 41 logged observation/target SHA256 values
match, as do checkpoint CPU, Python and CUDA RNG states and archived training
source hashes. These are sampled input checks, not a claim that every batch was
hashed. [Trace and RNG evidence](results/joint-control-observations-1k.json).

| Method | Known CFA PSNR | Unseen CFA PSNR | Known AHD sRGB PSNR | Unseen AHD sRGB PSNR |
| --- | ---: | ---: | ---: | ---: |
| Parent V16 step5000 | 53.27466 | 53.07857 | 39.15836 | 37.65963 |
| V18 joint step1000 | 53.17999 | 53.08643 | 39.08880 | 37.59780 |
| V19 refiner-only step1000 | 53.28990 | 53.07817 | 39.15998 | 37.64375 |

Joint tuning is worse on known-camera measured PSNR and nearly tied on unseen
cameras. Auxiliary SSIM is also nearly unchanged: V18 0.921574/0.907133 versus
V19 0.921416/0.907073. Four/five development scenes are not sufficient evidence
for broad quality claims.

The same 64-photo synthetic screen favors V18: sRGB PSNR/SSIM
31.99174/0.925095 versus V19 31.97042/0.924121. Eight procedural sources give
29.24301/0.912242 versus 29.22507/0.911088. This is not the full 427-photo panel.
The exact flat target at scene level 0.01 also does not improve: camera residual
sigma is 0.00023305 for V18 and 0.00022969 for V19, versus parent 0.00023195.

Neither first 1000-step candidate is promoted. V16 remains the fully reviewed
model. Both trials are resuming the original schedule to step5000 to assess
convergence; no inference default or quality target is changed by this review.
RawNIND still leads real quality, and final test targets remain unused.

Fixed native 160×160 crop triplets at identical locations and display settings.
Left: noisy Malvar; middle: candidate; right: calibrated low-noise AHD reference,
not exact RGB GT. Open original PNGs at 100%. V18:

![Noisy, V18, AHD reference: plates](images/joint-v18-1k-plates.png)

![Noisy, V18, AHD reference: structure](images/joint-v18-1k-7d.png)

V19 at the same inputs:

![Noisy, V19, AHD reference: plates](images/control-v19-1k-plates.png)

![Noisy, V19, AHD reference: structure](images/control-v19-1k-7d.png)

[Complete evaluation/crop/weight receipts and flat diagnostic](results/joint-control-1k-review.json).
The source report directories also contain exact synthetic-GT triplets.

Sources: Benoit Brummer and Christophe De Vleeschouwer, *Raw Natural Image Noise
Dataset (2025)*, [dataset](https://doi.org/10.14428/DVN/DEQCIM),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), with additional
scene permissions (`7D-1`: Peter Wemmert, CC0). Modified by registration,
calibration, demosaicing/restoration, crop and shared display.
