# PSNR history

V114 is the working quality reference, with 36.97973 dB photographic PSNR and 54.28627/54.00290 dB known/unseen measured-CFA PSNR. Its photographic change from V43 is +2.08 dB. Training histories differ; current strengths, tradeoffs and native comparisons are in the [model guide](current-model.md). A version names an experiment, not a training step.

![PSNR versus model version](images/version-PSNR-history.png)

Selected fixed primary endpoints, chosen by study scope, never by highest score. Each plotted metric has a completed primary panel; pending metrics remain blank. Version numbers are experiment labels; architectures, data, initialization, training budgets and recorded compute precision differ. This is descriptive history, not a controlled ranking or training curve. Missing versions lack a selected comparable primary report here. Camera references are measured CFA samples; independently demosaiced RGB references are not exact GT. Small camera panels have scene uncertainty. The plot describes checkpoints with unequal budgets and data; use the linked comparisons to assess particular gains and weaknesses. Dashed lines show V114's measured means. There are 52 completed photo endpoints and 52/52 known/unseen camera endpoints. The lower panels omit V72/V73 RAW-native prototypes only to show the mature RGB range more clearly.

All photo points use the full fixed427-source panel, seven conditions and four CFAs. Known/unseen points balance captures within scenes, then scenes (4/5 scenes,72/90 crops). Precision, checkpoint hashes and per-source results remain in the source reports.

V98/V99 use common ADC-only inference projection; only V99 trained through it. Their original V43/V95 references retain their checkpoint policies. The [completed ADC study](v95-adc-training-quality-review.md) improves ADC color but retains positive-noise color/detail weaknesses. Study-specific statistical gates do not prevent showing progress or choosing a stronger development baseline.

| Version / endpoint | Photo sRGB | Known CFA | Unseen CFA | Report |
| --- | ---: | ---: | ---: | --- |
| V32 / step-1000 | 33.95672 | 54.22962 | 53.76552 | [Review](geometry-corpus-v34-v36-review.md) |
| V34 / step-1000 | 34.46662 | 54.24658 | 53.78664 | [Review](geometry-corpus-v34-v36-review.md) |
| V35 / step-1000 | 33.84007 | 54.25055 | 53.80858 | [Review](geometry-corpus-v34-v36-review.md) |
| V36 / step-1000 | 34.47578 | 54.24577 | 53.77059 | [Review](geometry-corpus-v34-v36-review.md) |
| V37 / step-2000 | 34.81064 | 54.22979 | 53.77653 | [Review](native-corpus-2k-review.md) |
| V39 / step-2000 | 34.78920 | 54.27380 | 53.65415 | [Review](native-corpus-2k-review.md) |
| V43 / step-2000 | 34.89934 | 54.23332 | 53.80606 | [Review](native-corpus-2k-review.md) |
| V63 / V63-control-original20k | 35.93309 | 54.20366 | 53.84298 | [Review](long-commons-v63-v64-original20k-review.md) |
| V64 / V64-expanded-original20k | 35.95907 | 54.18217 | 53.84652 | [Review](long-commons-v63-v64-original20k-review.md) |
| V68 / V68-normalization-control-original4k | 35.96596 | 54.20920 | 53.86301 | [Review](normalization-v68-v69-original4k-review.md) |
| V69 / V69-normalization-augmented-original4k | 35.98628 | 54.21955 | 53.86247 | [Review](normalization-v68-v69-original4k-review.md) |
| V72 / V72-no-dino-mixed16-quarter160000examples | 28.70933 | 49.46916 | 45.56826 | [Review](packed-isotropic-mixed16-quarter-review.md) |
| V73 / V73-dino-mixed16-quarter160000examples | 29.05806 | 49.74359 | 45.94882 | [Review](packed-isotropic-mixed16-quarter-review.md) |
| V74 / V74-first1000 | 35.94016 | 54.20562 | 53.83642 | [Review](reconstruction-objective-first1k-review.md) |
| V75 / V75-first1000 | 35.96041 | 54.27080 | 53.87060 | [Review](reconstruction-objective-first1k-review.md) |
| V76 / V76-first1000 | 35.94163 | 54.20499 | 53.84358 | [Review](camera-supervision-first1k-review.md) |
| V77 / V77-first1000 | 36.10174 | 54.17786 | 53.92456 | [Review](camera-supervision-first1k-review.md) |
| V78 / V78-original4000 | 36.21099 | 54.19247 | 53.83875 | [Review](directional-interval-original4k-review.md) |
| V79 / V79-original4000 | 36.20938 | 54.18654 | 53.83875 | [Review](directional-interval-original4k-review.md) |
| V80 / V80-original4000 | 36.21129 | 54.18538 | 53.82029 | [Review](directional-bank-original4k-review.md) |
| V81 / V81-original4000 | 36.24146 | 54.19135 | 53.83501 | [Review](directional-bank-original4k-review.md) |
| V82 / V82-original4000 | 36.24146 | 54.19135 | 53.83501 | [Review](bank-detachment-original4k-review.md) |
| V83 / V83-original4000 | 36.23795 | 54.18305 | 53.83417 | [Review](bank-detachment-original4k-review.md) |
| V84 / V84-original20000 | 36.43996 | 54.17122 | 53.92823 | [Review](native-data-original20k-review.md) |
| V85 / V85-original20000 | 36.43574 | 54.17942 | 53.93069 | [Review](native-data-original20k-review.md) |
| V86 / V86-original4000 | 36.19663 | 54.18758 | 53.89443 | [Review](training-context-original4k-review.md) |
| V87 / V87-original4000 | 36.19762 | 54.17295 | 53.90475 | [Review](training-context-original4k-review.md) |
| V88 / V88-original4000 | 36.18923 | 54.18227 | 53.89214 | [Review](spectral-original4k-review.md) |
| V89 / V89-original4000 | 36.19699 | 54.17855 | 53.89400 | [Review](spectral-original4k-review.md) |
| V90 / V90-original4000 | 36.18643 | 54.19441 | 53.88461 | [Review](late-rgb-original4k-review.md) |
| V91 / V91-original4000 | 36.18861 | 54.18871 | 53.88604 | [Review](late-rgb-original4k-review.md) |
| V92 / V92-head-only-original4000 | 35.77085 | 54.20873 | 53.49849 | [Review](late-rgb-head-only-original4k-review.md) |
| V93 / step-20000 | 35.24714 | 54.28970 | 53.70392 | [Review](v43-curated-original20k-review.md) |
| V94 / step-20000 | 35.25352 | 54.30619 | 53.62349 | [Review](v43-curated-original20k-review.md) |
| V95 / step-20000 | 35.29553 | 54.33307 | 53.76990 | [Review](v43-curated-original20k-review.md) |
| V96 / step-4000 | 35.27828 | 54.32564 | 53.76643 | [Review](v95-flat-palette-quality-review.md) |
| V97 / step-4000 | 35.28321 | 54.32529 | 53.76365 | [Review](v95-flat-palette-quality-review.md) |
| V98 / step-4000 (ADC-projected) | 35.37252 | 54.33003 | 53.73025 | [Review](v95-adc-training-quality-review.md) |
| V99 / step-4000 (ADC-projected) | 35.40133 | 54.31940 | 53.72165 | [Review](v95-adc-training-quality-review.md) |
| V100 / step-10000 | 36.47264 | 54.17846 | 53.89614 | [Review](v84-curated-quality-review.md) |
| V101 / step-10000 | 36.50347 | 54.17404 | 53.92334 | [Review](v84-curated-quality-review.md) |
| V102 / step-20000 | 36.67951 | 54.23709 | 53.97177 | [Review](v102-v103-quality-review.md) |
| V103 / step-20000 | 36.68091 | 54.22003 | 53.96410 | [Review](v102-v103-quality-review.md) |
| V104 / step-20000 | 36.80085 | 54.26606 | 53.91700 | [Review](v104-reviewed-corpus-quality.md) |
| V111 / step-20000 | 36.90367 | 54.25270 | 53.93706 | [Review](v111-v112-primary-quality.md) |
| V112 / step-20000 | 36.90238 | 54.26914 | 53.95378 | [Review](v111-v112-primary-quality.md) |
| V114 / V114-step-20000 | 36.97973 | 54.28627 | 54.00290 | [Review](v114-v115-quality.md) |
| V115 / V115-step-20000 | 36.97700 | 54.32405 | 54.00417 | [Review](v114-v115-quality.md) |
| V116 / V116-step-20000 | 36.97478 | 54.28701 | 53.99497 | [Review](v116-quality.md) |
| V117 / V117-step-20000 | 37.04408 | 54.27303 | 53.97339 | [Review](v117-v118-quality.md) |
| V118 / V118-step-20000 | 37.03982 | 54.27562 | 53.97449 | [Review](v117-v118-quality.md) |
| V119 / V119-step-20000 | 37.03831 | 54.10063 | 54.00742 | [Review](v119-quality.md) |

[CSV](results/version-PSNR-history-v119-current-v1.csv) · [Source records, checkpoint hashes and evaluation metadata](results/version-PSNR-history-v119-current-v1.json) · [SVG](images/version-PSNR-history.svg) · [PDF](images/version-PSNR-history.pdf). Rebuild from the shipped JSON with `source scripts/env.sh` then `.venv/bin/python scripts/plot_version_history.py`; `--refresh-sources` additionally audits and recollects the original local report archives. `--data docs/results/NAME.json` chooses another recorded registry. These figures reuse completed reports and perform no model inference. Native noisy/restored/reference crops remain in each linked review and the README.
