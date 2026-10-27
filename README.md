# demosaic

Joint Bayer demosaicing and denoising in linear camera RGB, with physical noise
conditioning, frozen DINOv3 features and tiled16-bit output on NVIDIA GB10.
**V120 Small is the current general recommendation**, using V84's pretrained
DRUNet RGB trunk and official DINOv3 ConvNeXt-Small pyramid. It reaches
**37.04008dB** on the full427-photo panel, with known/unseen measured-CFA means
**54.31272/54.00872dB** and tested ADC maximum55.52DN16. It recovers V119's
camera/color regression while keeping its photo score. Fine detail remains weak.
[Results, native comparisons and explicit GFX profile limits](docs/v120-v121-primary.md).

**V114 Tiny** offers lower tested ADC maximum51.73DN16. **V117 Tiny** has a
slightly higher single-view photo mean37.04408dB, with lower camera means and
higher ADC bias than the current general choice. V120's numerical/native review
and complete102MP RGB16 checks are done. Foliage, neon, fine mesh and dark-field
mottling still need work. [Current choices](docs/current-model.md) ·
[GFX gallery](docs/gfx-qualitative.md) · [Camera comparisons](docs/native-camera-development.md).

Training uses geometry before final downsampling and zero optical blur. The
[latest source review](docs/repetitive-material-source-review.md) prepares90,778
photos/34 regions, including faint feather barbs. V134/V135 keep their33-region
data; all existing jobs retain declared inputs. [Data pipeline](docs/training-pipeline.md).
An optional [photographic epoch order](docs/photographic-epoch-order.md) covers
all prepared photos within 20k steps; its trained quality remains unmeasured.

| Current quality work | Evidence and next comparison |
| --- | --- |
| [V122/V123 frequency features](docs/v122-v123-quality.md) | Both20k reviews complete: joint training gains0.05493dB photo PSNR over adapter-only, with lower unseen-camera PSNR, a worse ADC tail and little weak-detail recovery |
| [V124/V125 conditional-mean loss](docs/conditional-mean-training.md) | [V12414k progress](docs/v124-progress14000.md): noisy/shadow PSNR+.008–.033dB, faint ADC−.350dB, no clear fine-mesh recovery. Original20k control continues; V125 follows on90,784/twenty regions |
| [V131/V132 spatial attention](docs/raw-spatial-training.md) | Four genuine CPU/CUDA checks pass;20k per arm queued on90,781/29 after V125's admission. An early102-input comparison waits for their retained1k progress snapshots |
| [V133 photographic quota](docs/reviewed-quota-training.md) | CPU/CUDA checks pass; 5% versus V131's 50% is queued at the same 20k budget. Early and full photo/camera/color/GFX reviews are queued with saved controls reused; quality remains unmeasured |
| [V134/V135 cleaned data and photo epochs](docs/photo-epoch-training.md) | All four real 16+2 checks pass on 90,778/33. Matched 20k replacement/epoch runs and full native/GFX reviews are queued after V133's automated review; quality is unmeasured |
| [V136 global RAW attention](docs/v136-global-attention-quality.md) | Matched1k review complete: +.0003dB ordinary, +.0007–.0026dB shadow and +.0131dB faint ADC over V129; mixed local detail and no clear new fine-mesh recovery. Native crops and independent audits published |
| [V137 conditioned global attention](docs/raw-global-conditioning.md) | Saved-state/branch diagnostics find almost uniform V136 matching. Normalized matching passes genuine CPU/CUDA16+2 checks; matched1k training runs with V136 controls reused. Quality is pending |

Shadow, feature-loss and curated-data pilots show no useful large recovery.
The [FP32 pilot](docs/training-precision-pilot.md) slightly improves selected
weak fur/grass/wood [faint-ADC bands](docs/faint-adc-precision.md), with a0.01720dB
lower panel mean and no clear large real-mesh gain. Measured strengths and
weaknesses guide the baseline. [Research and complete studies](docs/research.md) ·
[Historical diary](diary/index.md).

Optional [V114 eight-view inference](docs/v114-eight-view.md) improves the selected
material/camera support with a color-bias tradeoff; full panels/frame remain
unmeasured. [ADC sample fidelity](docs/adc-consistency.md) improves its ADC-only
photo panel by0.236dB with higher spatial variation; positive-noise inputs bypass it.

![PSNR versus model version](docs/images/version-PSNR-history.png)

[PSNR history and full values](docs/performance-history.md). Versions have unequal
training budgets and data; this describes available models rather than an
isolated architecture ablation.

## Current 100% crops

Photo cells are unchanged160×160 crops at the8×-binned evaluation resolution,
with shared coordinates/transforms. ISO12800-prior noisy observation →
**V120 Small, single view** → exact synthetic GT. Bark remains coherent;
fine raccoon fur remains softer than GT.
[Audited results and current review limits](docs/v120-v121-primary.md) ·
[Source/ROI/checkpoint/noise/display metadata](docs/images/v120-v121-primary-v1/manifest.json).

![V120 bark: noisy, restored and exact synthetic GT](docs/images/v120-v121-primary-v1/crop-801b668c1c29105a.png)

![V120 raccoon fur: noisy, restored and exact synthetic GT](docs/images/v120-v121-primary-v1/crop-881399e7a68af49a.png)

Sources: [Derek Ramsey](https://commons.wikimedia.org/wiki/File:Kentucky_Coffee-tree_Gymnocladus_dioicus_3264px.jpg),
[CC BY-SA2.5](https://creativecommons.org/licenses/by-sa/2.5/), and
[Korall](https://commons.wikimedia.org/wiki/File:Racoon_clinging_to_a_tree.JPG),
[CC BY3.0](https://creativecommons.org/licenses/by/3.0/), modified by binning,
cropping, simulated noise and restoration.

Real GFX100S: DSCF3879 ISO6400 → **V120 Small, fixed historical Haar profile** → DSCF3880 ISO100 f/5.6.
Native160×160 sensor-pixel crops from complete102MP outputs share +2EV display.
The independent ISO100 exposure is an approximate qualitative reference,
**not GT**. Fine foliage remains painterly; fence geometry is coherent.
[All six regions and other useful models](docs/gfx-qualitative.md) ·
[Metadata](docs/images/v120-v121-fixed-Haar-GFX-v1/manifest.json).

![V120 GFX foliage: noisy, restored and separate ISO100 reference](docs/images/v120-v121-fixed-Haar-GFX-v1/V120-foliage-fixed-Haar-triplet.png)

![V120 GFX fence: noisy, restored and separate ISO100 reference](docs/images/v120-v121-fixed-Haar-GFX-v1/V120-chain-link-fence-fixed-Haar-triplet.png)

The additional **fine green mesh beside the red train's cab** remains difficult:
the nominal ISO6400 prior largely erases its lattice. A fixed nearby-capture
profile makes more diagonal texture visible, with substantial fine detail still
missing in V120. Below: DSCF3842 camera JPEG → noisy Malvar → V120 nominal
→ V120 nearby profile → DSCF3835 ISO100 AHD → ISO100 camera JPEG. Both ISO100
references are **not GT**. Native160px cells share +4EV display; camera
processing/aperture differ. [Matched comparison and limits](docs/gfx-green-mesh.md).
The [matched V115/V119/V120 mesh check](docs/gfx-green-mesh.md#v120-after-correcting-the-paired-data-mix)
shows no clear V120 lattice-recovery gain at the same conditioning. The
[V119 report](docs/v119-quality.md) adds native material triplets and matched
foliage/fence comparisons alongside its measured gains and regressions.
The [RAW green-phase diagnostic](docs/green-phase-spectrum.md) finds matching
diagonal frequency peaks that remain strongly attenuated in the saved outputs.

![V120 fine green mesh, left native crop](docs/images/v120-green-mesh-v1/V120-fine-green-mesh-left-4EV.png)

![V120 fine green mesh, right native crop](docs/images/v120-green-mesh-v1/V120-fine-green-mesh-right-4EV.png)

The [stronger RawNIND full-frame reference](docs/rawnind-fullframe.md) and
[current Tiny/Small Q2/Sony/GFX50R comparisons](docs/cross-camera-qualitative.md)
show additional real-camera limitations. Broad real-photo superiority remains a goal.

## Setup and inference

Linux, Python 3.12+, `uv` and a CUDA 13-compatible NVIDIA driver are required for
the lockfile. DINOv3 requires approved Hugging Face access through `HF_TOKEN`.

```bash
source scripts/env.sh
uv sync --extra dev
uv run demosaic infer /mnt/external/demosaic/models/v120-final20000.pt photo.raf \
  /mnt/external/demosaic/output/photo-linear.tiff \
  --preview /mnt/external/demosaic/output/photo-srgb.tiff \
  --shot 0.001 --read 0.000001 \
  --tile 512 --overlap 64 --batch-size 4 --precision float32 --cudnn-benchmark
PYTHONPATH=.:src:scripts uv run pytest -q
```

Noise values are examples; use suitable camera/input priors.
[Linear DNG + full-resolution JPEG batch export](docs/dng-export.md) preserves
camera RGB and adapts existing darktable XMP edits. Add `--hot-pixels` to repair
isolated Bayer defects before restoration.
`--hot-pixel-clusters` also handles paired same-color defects; see the
[native crop investigation](docs/hot-pixel-clusters.md).
[Usage](docs/usage.md) · [current training](docs/quality-first-training.md) ·
[data pipeline](docs/training-pipeline.md) · [experiments](docs/experiments.md) ·
[documentation guide](docs/index.md). Quality takes priority. State-of-the-art
quality and 100MP within 10s remain project goals; full-frame timing is
checkpoint-specific.
