# Control replay reviewed; original long schedules prepared

Previous goal turn was progress: V56 trained/reviewed without promotion and an
identical-source V54 replay actually launched. Current turn confirms live owner
91971, follows its complete training/evaluation and verifies actual owner exit.

V57 SHA ace880de143572e4509b31e868447db77a869555450992909b46a9ab275f9f63.
Same b62c996 source bundle/model configuration, V43 EMA/fresh AdamW/EMA/seed52/
B16/LR3e-5/planned4000 and data. All41 logged observations and final Python/
Torch/CUDA RNG states match V54. Complete AdamW updates1000. Both records use
PyTorch2.14.1+cu130. Only2/71 portable model/EMA tensors remain equal; frozen
DINO tensors are outside portable restoration state. Different learned outputs
are observed despite the same configured recipe; cause is not isolated.

Replay−original: known primary−.059462dB[−.126466,−.006172], unseen+.003304
[−.018514,+.025122], photo−.043459[−.068214,−.019110], procedural−.277651
[−.652778,−.026769]. Photo SSIM slightly falls while procedural SSIM rises.
These source intervals condition on two fixed trained models, not training
replicates. One replay is not a variance estimate or proof that prior candidate
differences arise entirely from numerical variation. PyTorch2.14 primary docs
confirm benchmarking can select different algorithms across runs; that is a
plausible contributor without causal isolation. Original compute policy remains.

All86,828 suite cases complete.62,020 classical/RawNIND and12,404 original V54
neural cases replay exactly. Analytic448 Malvar and448 V54 neural cases also
replay exactly here. Replay carrier gain at level.18/contrast.02/high noise,
period4/8/16=.002516/.022727/.430946 vsoriginal.003324/.012822/.354528: weak
response can also change materially without an intentional intervention.

Visually inspected36 PNGs: original/replay/channel-RawNIND on ten standard
subjects and all six neural analytic examples. Controls look close; fabric
strands remain lost, foliage waxy and fence wires soft. No consistent native
winner. All46 triplets verify SHA/geometry/metadata/shared panels. Eight complete
GFX RGB16 files verify fullSHA/bytes/dtype/tags/sampled codes/ICC; ISO100 remains
an independent optical/time reference, never exact GT. No model/data promotion;
V43 step2000 README reference stays fixed. Replay report and full receipt saved.

Original fresh no-context/S/B3000 states retain complete model/EMA/AdamW/RNG
and original10000 schedules. Installed/stored PyTorch2.14.1 match. A guarded
continuation uses frozen8580a4e, same seed48/B16/LR1e-4/data/precision and
original paired32, with no reset. Newer paired83/weak/input policies do not
enter it. Native/full/analytic/102MP review follows original10000 completion.
The goal remains active; broad quality/SOTA, protected-final and speed evidence
are incomplete. Other users' GPU jobs remain untouched.
