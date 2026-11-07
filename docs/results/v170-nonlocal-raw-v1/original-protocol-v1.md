# V170 learned RAW matching comparison

The [April2026 NLFeMF paper](https://arxiv.org/abs/2604.17453) describes learned
matching and filtering on noise-conditioned RAW. We are testing its released
checkpoint alongside our DINO-based parent, using the [pinned upstream release](https://github.com/MIA-UIB/nonlocal-matchfilter/releases/tag/v1.0.0).
Its external RAW training data differ from our freely licensed image pipeline;
this is a pipeline comparison, not an isolated architecture or training test.
Quality measurement and native review are in progress. No gain is claimed yet.

The released model has141 tensors/15,282,866 parameters. Seven selected original
class definitions match upstream ASTs exactly. All network state keys load
strictly. We build the pinned upstream sampling kernels for GB10 rather than
changing their interpolation. Four independent NumPy sampling fixtures match
CPU/CUDA kernels. Original and copied full networks match bit-for-bit on CPU;
the CUDA parity output differs by at most2.24e-8 normalized. This admission uses
two CPU and one CUDA full-model calls, separate from the quality comparison.
All13 Bayer/conditioning/consistency CPU tests pass.

The frontend flips native Bayer geometry to RGGB, then uses the release's RGBG
channel order. It supplies clipped noisy RAW and the square root of the same
noisy-input variance used by our existing models. Output RAW clips to[0,1] as
in upstream evaluation. No target/reference enters inference. Two fixed returns
share one network call: Malvar demosaicing; and `parent + Malvar(denoised RAW -
CFA(parent))`. The second retains the DINO parent's interpolation residual while
changing measured sensor samples to the RAW estimate, up to FP32 rounding.
Both can introduce error; neither is a calibrated detail detector.

The fixed822 cached cases include present/absent procedural mesh, natural
faint/dark photographs, quiet neighbors, native512 flats and ADC controls. The
two GFX scenes and both cab noise priors use existing caches. ISO100/AHD/JPEG
references are qualitative, not exact GT, and are not pixelwise scored. The
checkpoint's training data are external; we make no blind split-matching claim.
No new source/noise, training, parent/DINO or original/dataz reads are required.

Each case runs once:822 quality network calls, with4110 nested sampling calls.
The processing order starts with512 and768 native contexts, retaining those
results rather than repeating admission inference. All1644 RGB method rows get
streamed metrics and fingerprints. Full outputs are retained for36 fixed native
cases:72 RGB arrays and36 denoised RAW arrays,projected .234GiB. The native report
uses48 boards and12 noisy/restored/GT triplets at unchanged160px ROIs, display
transforms, exposures and noise conditioning. Pixels are never resized. This is
not a complete new prediction archive.

The bounded comparison declares52GiB local/114GiB external reserves plus.5GiB
projection margin,32GiB runtime RAM and12GiB CUDA. Prior study guards and receipts
remain unchanged. Source/kernel/weight downloads are pinned and verified. The
restricted tensor loader uses inert objects for unused OmegaConf metadata;
arbitrary checkpoint code is not executed. The MIT notices and embedded Caffe
kernel notices are retained. All91 existing neural source files remain unchanged.

Preparation initially assumed optional shape metadata existed on every inherited
case; it now reads actual NPY headers, with original failed sources preserved.
The first worker then stopped at a missing frozen helper import before a claim,
CUDA setup or any held-out call. The verified helper is added through a separate
prepared receipt. All listed frozen files and the inference-function AST remain
unchanged; the same plan is used by the corrected initialization. No completed
scientific inference has repeated.

[Immutable preparation and exact sources](results/v170-nonlocal-raw-preparation-v1.json)
· [Runtime dependency correction](results/v170-runtime-dependency-preparation-v1.json).

To reproduce dependency preparation on this machine:

```bash
source scripts/env.sh
uv sync --extra nonlocal
PYTHONPATH=src:scripts .venv/bin/python scripts/fetch_nonlocal_raw.py
```

The optional model uses the released weights and a local native kernel build;
the project's general model recommendation remains unchanged while quality is
under review.
