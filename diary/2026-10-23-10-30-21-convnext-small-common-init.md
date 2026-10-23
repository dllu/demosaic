# Larger ConvNeXt compatibility and common initialization

Recorded: 2026-10-23T10:30:21-07:00 (America/Los_Angeles).

Checked official DINOv3 ConvNeXt-Small as a future capacity candidate while the
original V104 and incoming-source CPU scan remain live. HF access succeeds.
Pinned revision421020015aa4266363db803b6049a529999afb1e; model.safetensors LFS
SHA2568182492b73345ceb449ed6be0de486d778a73afb273ba2684de785a71ef1da9d.
License bytes exactly match the already bundled DINOv3 license. Tiny and Small
share96/192/384/768 feature widths; third-stage depth changes9→27.

The current pyramid accepts genuine Small weights without a production-code
change. Actual97×131 FP32 CPU features preserve the expected padded native stage
and cropped offset shapes. Exported three read-only inference-only derivatives
from V102 EMA:Small-swap,Tiny-zero and Small-zero. All91 learned EMA tensors
transfer exactly for blind swap; gate-zero derivatives change only3 gate tensors
(128/256/512 channels). Inherited checkpoint step20000 describes base restoration
history; these derivations have zero new training updates. Full derived file
hashes and actual backbone numeric hashes accompany every crop.

Four cached bark/canopy low/high-noise cases reproduce V102 scores and display
panels exactly. Blind Small swap loses2.17674dB at ISO100 and.57030dB at high
noise,with slight bark chroma and visibly faceted/smeared canopy. It is not a
trained Small result and does not establish a capacity ranking. The gate-zero
pair produces bit-identical FP32 outputs on all four cases; Tiny-zero versus
original has a small mixed mean effect:+.00689/−.01929dB. Actually viewed all24
native160 board cells; published16 unchanged triplets and two explicit native
Small-swap high-noise triplets. Public PSNR history/current selector stay fixed.

Both zero-gate variants then passed eight discarded actual CPU64/B1/FP32 mixed
Commons/native/paired updates on the original20k LR horizon and same seed61.
All91 initial EMA tensors match their derived initializer. The first training
prediction/loss are exact across backbones; all8 batch hashes match. All89 Adam
states and model/EMA tensors are finite; official backbones remain frozen and
unchanged(Tiny numericSHA370a84c2...,Small691963f0...). This is actual training
integration and common-function proof,not a trained quality endpoint or GPU
qualification. A later capacity comparison should rebind the best completed
initializer and fully reviewed corpus,with explicit per-backbone identities;
existing Tiny-specific study wrappers must not silently assume one DINO hash.

Actual source review also advanced:14 additional identities selected from the
192-source prefix were viewed across3 sheets/28 native256 source-target panels.
All14 are retained,including elephant wrinkles,horse fur,grass,weathered metal,
physical stained glass/sculpture and photoelastic plastic. This brings arrival
native inspection to86 unique identities. The one earlier flower future-withhold
remains pending a later corpus freeze; active V104 inputs are unchanged. Full
2395-source ranking and original20k training continue with their existing owners.

The first availability command omitted the script import path and stopped before
network access; the archived corrected driver uses PYTHONPATH=src:scripts.
No model or dataset mutation resulted. Published raw transfer and CPU-smoke
receipts retain their recorded bytes. Source/code/input guards and native pixel
hashes pass; all new Markdown local links resolve before commit.

[Capacity report](../docs/convnext-small-capacity.md) ·
[Machine proof](../docs/results/convnext-small-transfer-CPU-v1.json) ·
[Additional source decisions](../docs/results/incoming-source-loss-prefix192-native-review-v1.json).
