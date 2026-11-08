# Measure unknown frequencies across separate green CFA samples

Recorded: 2026-11-07T19:22:28-08:00 (America/Los_Angeles).

V177 follows the exact-template V176 result with an input-only frequency
selection diagnostic. On the same307 retained noisy mesh batches/614 pairs,
each member is processed separately. One green phase selects four principal-
band FFT peaks using only its own RAW and noisy variance proxy; the other is
measured at those fixed bins. Both directions are retained,8records/observation.
All4 observations' selections are journaled/fsynced per batch before target or
pair-index values are interpreted. No coupled noisy difference is used.

The primary statistic fixes rank1 in the lower-index green phase. Other-phase
nominal power>=16 occurs in170/614 present and0/614 matched absent cases. At>=4,
counts are231/6;considering all8 records gives303/71. Thus multiple candidates
and weak evidence can admit noise peaks. Selection-phase median power alone
is11.646 present/10.570 absent,versus other-phase medians1.713/0.666. The higher
cutoff also misses204/374 cases whose V176 conditional green SNR>=5. No cutoff
is deployed or presented as calibrated confidence or safe restoration.

Twenty of980 present peak records above16 have negative principal-band phase
agreement despite clean spectral power>=1. Native aliases can reverse the sign
or make a carrier vanish in one phase. Continuous separate-sample evidence is
a possible future model input;one signed statistic or a global sinusoid is not
a substitute for phase/spatial-support modeling or actual quiet/sky controls.
No new model,RGB restoration or real-photo quality gain is claimed.

All33 CPU tests pass(new11 plus existing22),including selection independence
from the measured phase. An independent orthonormal-QR/FFT/sorted-search reference
checks384 selected bins/1,920 scalars and384 direct complex DFT rows/covariances;
max scaled difference1.13e-14. All9,824 input-only peak bindings survive scoring,
307npz hashes/1,535 used array fingerprints pass,and scientific RSS peaks144.9MiB.
No neural,parent/DINO,sampler,checkpoint,noise,source-render or RAW-decoder calls;
no Torch/rawpy import. Parent arrays and protected real captures are not read.

Planv1 and its exact source/preparation log remain preserved. Before run.claim,
owner or scientific selections,the v2 source corrects import ordering and adds
an explicit --plan argument. Both plans preserve identical selection/scoring
rules and inputs. There is one successful scientific run,no prefix replay.
The final chart was actually viewed;all public figure bytes and1,228 points,
8 edge summaries/16 table cells and local links pass independent verification.
Machine summaries retain code/plan/full-record hashes and external journals.

V175's same original training owner remains live. Its96 neural sources and all18
completion helpers are unchanged;the watcher remains armed. The fixed recipe
and candidate-quality review are unaffected. Model recommendations/native crops
remain those already published;V175 quality is still pending. No /mnt/dataz or
original-photo access.

[Report](../docs/phase-frequency-evidence.md) ·
[Full source/points/audit summary](../docs/results/v177-phase-frequency-holdout-v1.json) ·
[Publication verification](../docs/results/v177-publication-verification-v1.json).
