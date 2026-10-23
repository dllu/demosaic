# Current real-camera quality

**V104 raises known-camera CFA PSNR and lowers the unseen-camera mean relative
to V102.** Its photographic gain is stronger and more consistent. The camera
panels remain small: three of four known scenes improve, versus two of five
unseen scenes. [Current model choices](current-model.md) ·
[V104 results and native photo triplets](v104-reviewed-corpus-quality.md).

| Panel | Method | Measured-CFA PSNR | Auxiliary AHD RGB PSNR | AHD SSIM |
| --- | --- | ---: | ---: | ---: |
| Known4 | V102 | 54.23709 | 40.07688 | .932273 |
| Known4 | V104 | **54.26606** | **40.10615** | .932371 |
| Unseen5 | V102 | **53.97177** | **38.84229** | .923933 |
| Unseen5 | V104 | 53.91700 | 38.78090 | .923041 |

The V104−V102 known CFA change is +.02897dB, with a scene-bootstrap 95% interval
[−.01271, +.06782]. The unseen change is −.05477dB [−.13994, +.01515]. These
intervals describe sampled scenes rather than training-seed uncertainty.

These matched CUDA IEEE FP32/B2 results cover all 72 known and 90 unseen
native512 crops: 8/10 noisy captures across 4/5 scenes. Means balance crops
within capture, captures within scene, then scenes. Primary references are
measured low-ISO CFA after shared registration/gain. Independently processed
AHD RGB is **not exact RGB GT**. RawNIND uses input-only CFA gain and signed,
unclipped publisher normalization. The independent 1,134-row audit rebuilds
all seven methods and reproduces every earlier V102 case metric exactly.
[Source means, case archives, intervals and hashes](results/v104-reviewed-corpus-primary-statistics-v1.json).

## Scene changes

| Panel / scene | V104−V102 CFA PSNR, dB |
| --- | ---: |
| Known / 2pilesofplates | +.08397 |
| Known / 7D-1 | −.03169 |
| Known / MuseeL-CopteArch-C500D | +.01938 |
| Known / D60-2 | +.04423 |
| Unseen / LucieB_3apples | +.04701 |
| Unseen / LucieB_Coulicoco | −.20550 |
| Unseen / LucieB_bedroom_tapestry | +.00085 |
| Unseen / LucieB_stick_figurine | −.01999 |
| Unseen / LucieB_top_of_Expedit | −.09624 |

Different training duration, seed and cohort prevent attributing the change
solely to the larger corpus. Known/unseen refer to this project's development
panels; RawNIND may have trained on development scenes. The
[publisher test reserve](paired-reserved-test.md) remains unscored and outside
selection. These results do not establish broad real-camera superiority.

## Native comparisons

Rows: noisy Malvar, V102, V104, RawNIND channel, independent AHD reference.
Each cell is an unchanged 160×160 sensor-pixel crop with matching coordinates,
WB, matrix and exposure ×1. Shared noisy/reference pixels match exactly.
All 20 camera-board cells were viewed at original resolution. V102/V104 remain
close, with soft fine surface/weave detail. The separate AHD reference retains
noise; its fluctuations cannot all be treated as scene texture.

![Known-camera plates and patches, native160 cells](images/quality-v102-v104-known/comparison.png)

[Known source/ROI/checkpoint/noise/display metadata](images/quality-v102-v104-known/manifest.json).

![Unseen-camera apples and cloth, native160 cells](images/quality-v102-v104-unseen/comparison.png)

[Unseen source/ROI/checkpoint/noise/display metadata](images/quality-v102-v104-unseen/manifest.json).

## Reproduction and earlier evidence

The original V102/V104 final 20k EMAs are evaluated without an intermediate
checkpoint search. Metrics use [32,32,448,448] interiors of prepared512 contexts;
display crops use [176,176,160,160]. Noise is per-capture input-only Haar fitting
or the disclosed ISO fallback, recorded with each triplet. No per-method
reference exposure fit is performed. The frozen runner is under
`.cache/current-quality-20261023-v1/reviewed-corpus-evaluation-v1/`; outputs are
`/mnt/external/demosaic/v102-reviewed-corpus-evaluation-20261023-v1/{known,unseen}/`.

The [V101/V102/V103 study](v102-v103-quality-review.md) preserves the earlier
camera gains, native comparisons and original evidence.
