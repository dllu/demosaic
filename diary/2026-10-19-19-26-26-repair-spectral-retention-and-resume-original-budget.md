# Repair final checkpoint retention and resume the original spectral trial

The preceding goal turn made progress: it implemented and tested the optional
spectral branch, closed the context review and launched the fixed88508-source
comparison. This turn revalidated the exact live owners and observed control
update225 before preparing its final review. PROMPT quality/speed requirements
remain unproven or unmet; the goal remains active.

Inspection found an avoidable bug in my new retention wrapper. At the original
4000 boundary, scheduled validation saves last.pt and stop_after saves it again;
the wrapper asserted the retained copy did not exist each time. The second
identical save would fail after completing training. Earlier16-update checks
did not enter the retention branch at1000/4000. This is a wrapper defect, not a
recorded nonfinite-training or image-quality failure.

Fixed only the experiment driver: repeated retention requires matching SHA256,
while changed bytes still fail without overwriting the retained copy. A real
PyTorch checkpoint-writer regression passes. Corrected genuine CPU and CUDA
control16/spectral16/8+8 preflights pass; all six original-versus-corrected endpoint
pairs have exactly matching model/EMA/AdamW/RNG/best/step/model-config fields
and saved observations. All46 training-core modules remain unchanged.

An exact-owner watcher preserved the verified original1000 checkpoint, SHA256
2388c26b26767f0dd60c466b385bdaa93c7ca52543e1639310540898c184ab9c.
All91 model/91 EMA/89 AdamW states are finite, counters1000, second moments
nonnegative. It retained all56 source/actual-forward/actual-loss observations
and the metric prefix. It stopped only original controller533083/1792461642.08
and worker533376/1792461711.09, controller first, with creation/session identities
and exits verified. Originals, logs and frozen code/plan remain intact. Some
unretained post1000 computation may be discarded; it is not part of the retained
trajectory or represented as an equal total-hardware-compute comparison.

A separate fresh CPU process resumes an external step8 state and prefix. Its
final16 model/EMA/AdamW/best/RNG and all observations exactly match uninterrupted
training. A tiny CUDA serialization fixture additionally tests repeated retention
with an interleaved best.pt save and rejects a changed state. Its4000 label
exercises serialization only; it performs one optimizer update, not4000 training.
GPU checks start only after the original owned GPU worker exits.

Separately froze the explicit recovery:288 files/796 inputs, plan SHA256
459509319574527cd651b0905a04b99613eec5089899bfd6b8d05999800b20dc.
Control resumes full original1000 state and performs only remaining3000 updates;
spectral still starts from genuine V63 original20k EMA for original4000 updates.
Source membership, losses, noise, seed55/B16/BF16, original warmup/cosine4000
and full quality/native criteria remain fixed. Control retains13462 active
seconds of its original14400 after938 consumed seconds. No optimizer reset,
held-out selection, automatic retry or schedule extension is introduced.

Recovery controller544254/1792462947.40 and worker544572/1792463016.96 are exact
live owners. The actual start header reports1000/original4000,88508 Commons,
106 native groups and32 paired scenes. The first resumed forward verifies all
model tensors equal the saved checkpoint and genuine DINO remains unchanged.
The published snapshot verifies update1025; subsequent direct observation reaches
1050. Prefix observations are preserved and new actual inputs/loss fields match
their declared batches. The spectral arm remains queued in the same controller.

Published repair/probe/state/source/launch evidence and current operational root
in docs/spectral-retention-recovery.md. Current training root is
/mnt/external/demosaic/experiments/spectral-v88-v89-retention-recovery-v1/.
Full final photo/camera/analytic/ADC/hue/highlight scoring and actual native crops
remain pending. V43/README/PROMPT stay unchanged, GFX3879/3880/siblings stay out
of training, and no source HDDs or original photos are opened or modified.
