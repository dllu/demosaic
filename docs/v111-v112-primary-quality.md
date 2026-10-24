# V111/V112: completed primary photo and camera panels

**Both continuations improve full-photo PSNR by about .10dB over V104.**
V111 reaches 36.90367dB and V112 reaches 36.90238dB. V112 has higher known/unseen
camera means than V111; their photographic difference is small and mixed.
Fine high-noise detail remains unresolved. The [complete color/GFX review](v112-quality.md)
now selects V112 as the working baseline; this page retains primary-panel scope.

[Completed panels, original checkpoints and independent source/scene statistics](results/v111-v112-primary-quality-v1.json) ·
[Matched recipes and execution](loss-scale-training.md) ·
[Native material comparison](v111-v112-material.md).

## Complete primary panels

| Final20k endpoint | Full427 photo sRGB PSNR | Known4 CFA PSNR | Unseen5 CFA PSNR |
| --- | ---: | ---: | ---: |
| V102 | 36.67951 | 54.23709 | 53.97177 |
| V104 | 36.80085 | 54.26606 | 53.91700 |
| V111, epsilon .001 | **36.90367** | 54.25270 | 53.93706 |
| V112, epsilon .0003 | 36.90238 | **54.26914** | 53.95378 |

The photo panel covers all427 fixed sources, seven noise/exposure conditions
and four CFAs, with native256 contexts and 240-pixel scoring interiors.
Sixteen synthetic sources are reported separately. Camera panels cover all72
known and90 unseen crops, with 448-pixel interiors and source-balanced measured
CFA scoring. “Unseen” concerns our training; external training overlap remains
unproven. Independently demosaiced RGB references are not exact GT.

V111 gains **+.10282dB** over V104, source-bootstrap 95% interval
[+.09778,+.10790], with424/427 source means improving. V112 gains
**+.10154dB**, interval[+.09671,+.10635], with425/427 improving. All seven
condition means rise for both. V111's largest source regression is −.32335dB;
V112's is −.30271dB. Mean SSIM, chroma error and gradient error also improve.

| Condition | V111 − V104, dB | V112 − V104, dB |
| --- | ---: | ---: |
| ADC-only | +.21724 | +.21409 |
| ISO100 prior | +.13539 | +.13370 |
| ISO1600 prior | +.08253 | +.08202 |
| ISO12800 prior | +.04113 | +.04062 |
| Shadows | +.02843 | +.02703 |
| Highlights | +.15685 | +.15608 |
| Legacy noise | +.05821 | +.05722 |

V112 minus V111 is −.00129dB, interval[−.00292,+.00048], improving167/427
photo source means. Its known/unseen CFA means rise **+.01644/+.01672dB**
over V111, improving4/4 and4/5 scene means. Both improve all five unseen scenes
over V104. V112's known mean is only+.00308dB above V104, with2/4 scenes rising.
These source/scene intervals describe the fixed evaluation set, not training
repeat uncertainty. Both recipes use one matched seed and fixed budgets.

## Native100% triplets

Noisy Malvar → restored → exact synthetic GT. These are the original selected
bark/canopy observations, not examples selected from the new source regressions.
Each panel is native160 at[48,48,160,160] in a native256 context, without resizing.
Shared WB=[2,1,1.5], matrix, display exposure×1, ISO100 shot2e-5/read variance1.6e-9
match across versions. These images illustrate the separate selected material
panel; the table above uses all427 photographic sources.

**V111:**

![V111 bark: noisy, restored, exact GT](images/v111-early-material/iso100-prior/crop-5c9cfe7a56e7eadf.png)

![V111 canopy: noisy, restored, exact GT](images/v111-early-material/iso100-prior/crop-f8f123bdd99f51b9.png)

**V112:**

![V112 bark: noisy, restored, exact GT](images/v111-v112-material/iso100-prior/crop-647b560234a48ad7.png)

![V112 canopy: noisy, restored, exact GT](images/v111-v112-material/iso100-prior/crop-277f4c06ef24083e.png)

[V111 source/ROI/checkpoint/noise/display metadata](images/v111-early-material/iso100-prior/manifest.json) ·
[V112 bark metadata](images/v111-v112-material/iso100-prior/crop-647b560234a48ad7.json) ·
[V112 canopy metadata](images/v111-v112-material/iso100-prior/crop-277f4c06ef24083e.json).
V111 SHA256 is `97ab9ca5f1f182ff42a4245c630bba810607a3d13b61cf8aae5842192a18da15`;
V112 is `21c3cca8370df21e3412f9ccbf441c35afcfad8fd03174c7727f4f88874783b1`.
The material review finds small native differences; high-noise feather/fur
structure remains smoother than GT.

## Remaining tradeoffs and work

V111's [complete analytic review](v111-early-quality.md#complete-weak-texture-and-flat-color-panels)
finds improved high-noise color/coarse carriers, but raises worst ADC flat bias
to2,143DN16; finer carriers remain weak. The matched V112 color/GFX diagnostics
are complete: worst ADC bias falls to50.89DN16. [Current review](v112-quality.md). Its slightly lower photo mean is considered alongside its higher
camera means; neither a small difference nor an old study promotion gate hides
useful results.

The [stronger RawNIND reference](rawnind-variants.md) remains close on measured
camera means and has a [complete GFX comparison](rawnind-fullframe.md).
Broad real-camera superiority is still unachieved. The [Small transfer](small-feature-transfer.md)
now uses V112; matched Tiny/Small continuations passed actual CPU updates and
are [queued](small-aligned-training.md). No trained Small quality result is claimed.

The scalar review runs no neural inference. Original nine-method coverage and
summary arithmetic pass; all24,808 earlier V102/V104 case-metric rows replay
exactly. Independent aggregation rebuilds photo-source and camera-scene means
and contrasts. Full float photo predictions were not retained, so this is not
an independent reconstruction of metric definitions from new float arrays.

Photo attribution: [Derek Ramsey, bark](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA2.5](https://creativecommons.org/licenses/by-sa/2.5/), and
[Grendelkhan, canopy](https://commons.wikimedia.org/wiki/File:Forest_covered_hills_on_Yakushima.jpg),
[CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/). Modifications:
8× binning/cropping, synthetic noise, restoration and common display conversion.
