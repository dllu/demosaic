# V120/V121 completed primary results

**V120 is a useful balanced Small continuation.** Restoring corrected paired32
keeps V119's photo score while recovering most of its known-camera regression
and removing its large tested ADC color outlier. The further cleaned-source/
fourteen-region V121 arm has a small photo/known-camera change, lower unseen
mean and a large remaining ADC outlier. These are single-run observations.
Full saved/local-detail comparisons and the selected native review are complete,
including all six main GFX regions and both fine-mesh profiles. Matching-profile
full-frame comparison against older models and detailed ADC-outlier visual
diagnosis remain open. The primary panels and independent audit are complete.
It is now the [current general recommendation](current-model.md); active
controlled trials retain their original V115 parents.

| Model | Photo sRGB PSNR | Known CFA PSNR | Unseen CFA PSNR | Largest ADC mean-RGB error, DN16 |
| --- | ---: | ---: | ---: | ---: |
| V114 Tiny | 36.97973 | 54.28627 | 54.00290 | 51.73 |
| V115 Small parent | 36.97700 | 54.32405 | 54.00417 | 65.64 |
| V117 photo option | 37.04408 | 54.27303 | 53.97339 | 63.89 |
| V119 expanded paired set | 37.03831 | 54.10063 | 54.00742 | 2526.70 |
| **V120 corrected paired32** | **37.04008** | **54.31272** | **54.00872** | **55.52** |
| V121 cleaner90787 /14 regions | 37.04157 | 54.32184 | 53.98947 | 1645.36 |

Photo means balance427 fixed sources over seven conditions/four CFAs. Camera
means balance captures within4/5 known/unseen scenes (72/90 crops), using measured
CFA samples. Independently demosaiced RGB is not exact GT. ADC maxima describe
588 fixed analytic cases, not all possible colors. All models here use single-view
FP32 evaluation; budgets, architecture and data histories differ across versions.
[New audited means, hashes and provenance](results/v120-v121-primary-v1.json) ·
[Publication and history checks](results/v120-v121-publication-v2.json) ·
[Parent comparison](v114-v115-quality.md) · [V117](v117-v118-quality.md) · [V119](v119-quality.md).

V120 versus V119 changes photo by+.00177dB, known by+.21209dB and unseen
by+.00130dB. Against V115 it gains+.06308dB on photos with a−.01133dB known
and+.00455dB unseen change. V121 versus V120 changes photo by+.00149dB,
known by+.00912dB and unseen by−.01926dB. These differences alone do not establish
repeatability or a real-photo ranking. The paired-data intervention's stronger
camera/color balance is useful even while that broader review continues.

Both completed their original20,000 updates from V115 Small EMA with the same
Small architecture, seed65 and quality recipe. V120 uses90,791/six regions;
V121 uses90,787/fourteen regions. [Exact recipe/accounting](paired32-weak-detail-training.md).
V120 SHA256: `a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
V121 SHA256: `40fb6369064aaf82d513728110a6823ed72be50e79394988303c392b3a02f077`.

## Native exact-GT triplets

Each cell is160×160 pixels at100% with identical coordinates and display
transform: noisy Malvar → restored → exact synthetic GT. These use the saved
ISO12800-prior observation (shot.00256/read2.62144e−5), RGGB, native256 context,
ROI `[48,48,160,160]`, shared WB/matrix, exposure×1 and clipped sRGB display.
No crop pixels resize. Full source/ROI/checkpoint/input/conditioning metadata
is in the [native manifest](images/v120-v121-primary-v1/manifest.json).

![V120 bark: noisy, restored and exact synthetic GT](images/v120-v121-primary-v1/crop-801b668c1c29105a.png)

![V120 raccoon fur: noisy, restored and exact synthetic GT](images/v120-v121-primary-v1/crop-881399e7a68af49a.png)

![V121 bark: same observation, display and exact GT](images/v120-v121-primary-v1/crop-e82d6dfea31b1720.png)

![V121 raccoon fur: same observation, display and exact GT](images/v120-v121-primary-v1/crop-52f8eac2aad5b961.png)

Actually viewed at native resolution: bark structure is coherent; fine raccoon
fur remains softer and less irregular than GT. These examples show no clear
large V120/V121 detail difference. All921,600 published panel channels match
their original audited pixel hashes exactly; no new model/noise/RAW work occurs.

Sources: [Derek Ramsey, Kentucky Coffee-tree](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA2.5](https://creativecommons.org/licenses/by-sa/2.5/), and
[Korall, Racoon clinging to a tree](https://commons.wikimedia.org/wiki/File:Racoon_clinging_to_a_tree.JPG),
[CC BY-SA3.0](https://creativecommons.org/licenses/by-sa/3.0/). Modified by binning,
cropping, synthetic sensor noise, restoration and display conversion.

## Completed local and native review

All four contrasts complete14,190 matched numerical observations each. The local
analysis uses427 photos/5,124 source-noise-CFA cases and96,075 unique GT blocks.
For the weakest high-noise group, source-balanced projected detail gain is
.36422(V115), .36523(V119), .36476(V120) and .36575(V121); V117 is.36629.
The small changes leave substantial weak-detail attenuation. V121's photo
change from V120 has a paired-source95% interval of[−.00080,+.00401]dB;
187/427 source means rise. This does not establish repeatable improvement.

Both linear/sRGB full101.996MP exports have verified hashes/types/shapes.
921,600 native linear-camera values match exact FP32 clip/round quantization;
native sRGB quantization is not independently recomputed.
[Completed comparisons, local statistics and actual viewing](results/v120-v121-native-review-v1.json).

The matched nominal-profile main GFX boards below show noisy → V120 → V121 →
independent ISO100 reference. All cells are native160 pixels at shared+2EV.
Fence/building edges remain coherent and sky quiet; foliage is painterly and
saturated sign detail is smeared. No clear large V121 real-detail gain appears.
The separate ISO100/f5.6 exposure remains **not GT**.

![V120/V121 building, larger fence and neon at matched nominal conditioning](images/v120-v121-review-v1/V120-V121-matched-gfx-1.png)

![V120/V121 foliage, platform and sky at the same matched conditioning](images/v120-v121-review-v1/V120-V121-matched-gfx-2.png)

## Real-photo limits and remaining work

V120's [matched two-profile fine green mesh review](gfx-green-mesh.md#v120-after-correcting-the-paired-data-mix)
shows no clear lattice-recovery gain over V115/V119. The
[completed V121 mesh review](gfx-green-mesh.md#v121-after-adding-the-fourteen-region-bank)
also shows no clear gain over V120 under either matched profile. Separate ISO100 captures remain qualitative
references, not exact GT.

The completed new main-GFX outputs use nominal ISO conditioning; older outputs
use the Haar-fit profile. The [report repair](endpoint-quality-review.md#material-selection-and-gfx-conditioning)
labels both profiles explicitly and preserves all RAW/reference/display checks.
These saved pipeline boards cannot isolate a model-only gain. Matching-profile
full-frame comparisons against older models and detailed ADC-outlier visual
diagnosis remain to finish. No broad real-photo superiority,10-second102MP
runtime or overall final model ranking is claimed here.
