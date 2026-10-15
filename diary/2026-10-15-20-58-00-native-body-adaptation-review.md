# Completed native-target body-adaptation review

V22/V23 reached the predeclared1000-step review and stopped. No restart or
promotion. They repeat V20/V21 seed44 schedules with body+fine correction
trainable (4,819,236), DINO frozen. All41 sampled hashes match the corresponding
fine-only arm, all34 shared V22/V23 draws match,7 native substitutions differ.
Initialization and CPU/Python/CUDA RNG states match. Training/model/data code
matches; prior preparation/report changes are isolated from AST-equal runtime
native dataset/noise functions. These are sampled, not exhaustive batch proofs.

Known/unseen primaryPSNR53.28997/53.07098 native versus53.26375/53.08593
control. Native effect+.02622/−.01494dB, intervals[+.01381,+.03529]/
[−.02869,−.00102] over only4/5 scenes. AuxiliaryRGBPSNR improves+.0643/+.10185dB;
SSIM.922003/.907244 versus.921299/.906940. Synthetic64photoPSNR31.96588
versus32.01470 (native−.04881dB), eightprocedural29.24892/29.26336. Mixed
primary results and loss on photo screen do not establish an improvement.
V16 remains reviewed model, finaltest untouched, quality/speed goals open.

Published two native160px AHD-reference triplets per candidate, source/weights,
metrics/bootstrap/ROI/noise/display receipts and 2x2 fine/body comparison.
Visually inspected all four crops: fine-detail loss and color speckling remain.
No claim of exactAHDGT or new GFX outputs for these trials. New GFX standingpair
is explicitly DSCF3879/3880, with fourregions, excluded fromtraining.
