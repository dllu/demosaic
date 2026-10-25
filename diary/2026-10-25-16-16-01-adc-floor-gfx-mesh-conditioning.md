# Correct ADC-floor noise diagnostics and compare fixed GFX mesh profiles

Recorded: 2026-10-25T16:16:01-07:00 (America/Los_Angeles).

The corrected green-mesh reference remains **DSCF3835**, ISO100 f/5.6 2.5s,
46s before DSCF3842 ISO6400 f/1.7 1/300s. The main DSCF3879/3880 standing case
is unchanged. No originals or source-drive files were modified/read again.

The nominal prior's read variance is6.5536e-6. The already established nearby
DSCF3879 profile has shot.0014635775921166604/read1.0715704128646712e-6.
Its exact coefficients appear in the October17 receipt, before this new case.
The archived DSCF3842 input-Haar bins are more consistent with that fixed profile:
median absolute relative mismatch.98%, versus15.56% for the nominal prior.
This is not known camera-noise truth or output/reference fitting.

A real bug emerged: flat-patch calibration rejected >=1% values below
black-subtracted zero, although read_raw intentionally retains negative read
noise. The actual normalized ADC floor is phase-dependent -black/(white-black).
Metadata-backed fits now use that floor plus half a code of floating tolerance;
no-metadata calls retain the legacy convention. Actual ADC censoring, high
clipping, texture rejection and identification thresholds remain. The CLI,
new real-pair preparation, RAW-pair reporting and automatic DNG noise path pass
metadata; new receipt labels distinguish ADC-floor-v2. Existing source archives,
profiles, training caches, queue code and executed receipts stay intact.

The actual saved768px mesh has2–11% negative samples per phase and none at its
actual ADC floor. Legacy accepted51 patches; corrected accepted2,134. The
accepted intensity span is still only.004957, so no shot/read fit is accepted.
The nominal/nearby profiles' median input-bin mismatches here are69.38%/5.81%.
These overlapping patch diagnostics can contain texture/correlation/selection
bias and do not replace dedicated calibration.

All240 prior known-noise arrays were reused/hash-checked, not regenerated.
Both versions accept192 cases and reject all48 narrow-span cases. Corrected
worst tested in-support variance error.6257dB (legacy.4405dB); none exceed1dB
inside support. Across all six fixed probes50/192 exceed1dB (legacy55), with
unchanged worst7.0425dB in deep-shadow extrapolation. No threshold was tuned;
the independent Python math audit reproduces all scalar errors/masks exactly.
This fixes censoring semantics, not all calibration weaknesses.

Exactly two new CPU FP32 root/DINO forwards were executed: V114 and V115 on
the same retained768px mesh context using that one external profile. A
prospective fixed plan was recorded before outputs; no strength sweep, new
RAW decode, noisy observation, training, early endpoint or repeated control
inference occurred. Nominal controls are their original saved F32 arrays.
The profile changes only coefficients and the variance map (median ratio.6344).
Both models retain more diagonal mesh texture, especially at the right ROI;
the lattice remains soft/weak/irregular against the independent ISO100 reference.
Residual grain/detail ambiguity and a blue point persist. This is a limited
qualitative conditioning gain, not a trained-model/PSNR/full-frame/speed result.

All four matched boards and four native noisy/restored/independent-reference
triplets were actually viewed. Each cell is160×160, unchanged pixels, shared
+4EV, identical coordinates. Rendering forbids neural module calls. Independent
NumPy transforms reproduce all24 board cells (1,843,200 uint8 samples) exactly;
all12 triplet cells match their board counterparts. README and current GFX/noise
guides now document this gain and its limits instead of retaining only the
nominal failure. Original five-method/nominal evidence remains intact.

Validation:34 calibration/conditioning/DNG tests passed (16.77s), plus a new
signed-RAW CLI integration test (1.75s); Ruff/format and diff checks pass.
[Calibration receipts](../docs/results/noise-calibration-adc-floor-v2.json) ·
[Mesh receipts](../docs/results/gfx-green-mesh-profile-transfer-v1.json) ·
[Current mesh guide](../docs/gfx-green-mesh.md).

V119's original training/queues remain unchanged. Last observed19,075/20,000,
finite loss, about70GiB available; all six exact owner identities remained live.
Its full endpoint and queued comparisons remain pending. The better-quality,
broad real-photo and100MP/10s goals remain open.
