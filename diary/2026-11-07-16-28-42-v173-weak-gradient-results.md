# V173 amplitude-balanced gradient results

Recorded: 2026-11-07T16:28:42-08:00 (America/Los_Angeles).


The [completed V173 gradient-loss experiment](../docs/weak-gradient-matching.md) lowers
EMA quiet spatial RMS **0.32–0.68% versus V172**, improving all 32 inputs. Quiet
total RMS falls 0.27–0.52%, and native512 total-flat means fall 0.25–0.30%.
**Mesh response falls 3.95% to 3.724% of GT**; natural fine-band response falls
2.63–2.88% on all 128 inputs. Broad mottle and real fine crossings remain
unresolved. Retain this modest quiet/spatial-error option alongside V172's
stronger response and V171's stronger flats. V172 remains the balanced matching
baseline for further detail work; V120 remains the general recommendation.
Both endpoints, 822 cases, 60 actual native figures, 12 triplets and scoped audits
are complete. All 162 focused checks pass (161 CPU tests and one CUDA stream
guard); no matching core or native sampler runs in that guard. An offline
[native-pixel viewer](../docs/images/v173-weak-gradient-matching-v1/native-viewer.html)
adds click/F-key flipping; all 240 browser crops match their PNG pixels exactly.

Actual training owner 145153/create1794096654.5 and review owner153676/
create1794097675.54 are terminal. The final checkpoint SHA256 is
`628b46050aacefbd3bfcab0bbc17e8afcb216ce452c47c96dc32a31f15457836`.
The schedule completes900 updates/100 ADC skips/3,600 images and genuine step8
restoration. All141 final Adam states, both strict endpoints,900 NumPy FP32 totals
and900 inherited target-mask fingerprints pass. All1,644 V169 replays,144 ADC
identities and6,576 actual input fingerprints pass. Selected independent new-array
metrics/addition cover36 cases,72 RGB+72 residuals/430,196,736 bytes,not all822
full arrays. All60 figures/12 triplets were actually viewed in15 native sheets.
New matching calls total2,404 CUDA/0 CPU;frozen CUDA2,548. No parent/DINO,source/
noise or original/dataz work. Training/quality CUDA peaks remain6.279/2.786 GiB.

Quiet EMA RMS is4.012548/6.278894 DN16;spatial3.417869/5.540053,with all32 spatial
inputs improving versus V172. Mesh response falls3.954% to3.723868% of GT,with237
of256 cases lower. Natural fine-band response falls2.625–2.882% on all128 inputs.
Flat full means fall0.249/0.303%,while coarse changes−0.010/+0.020% versus V172.
V171 still has lower full/coarse-flat error. Real cab crossings stay incomplete;
main sky/building/foliage/coarse fence remain near V172,quiet/flat broad mottle
persists and the visual gain is subtle. Real ISO100/AHD/JPEG references differ
in capture/processing and remain qualitative,not exact GT or scoring targets.
Both scene families remain excluded;originals stay read-only and unused.

V173 is retained as a modest quiet/spatial-error variant. Keep V172 as the
balanced matching baseline for further detail work,V161 stronger learned mesh,
V171 standalone flats and earlier quiet options. README now retains8 native
triplets:V161 detail,V172 balanced mesh,V173 quiet andV171 flats. No significance
or promotion gate hides these actual gains/costs. The full goal remains active.

The focused suite has162 passing checks:161 CPU tests plus1 CUDA stream rejection
with a stub network,not162 purely CPU tests. That guard runs no real matching or
native sampler. Original broad labels remain unchanged;versioned narrative and
accounting helpers plus an additive scope receipt correct them. The preparation
AST import-order rejection and original work/logs remain preserved;two follow-up
initializers launched no worker. No scientific phase failed or restarted.

The reusable offline viewer keeps160px native crops and allowsA/B flipping
withF. It adds no inference. V172 andV173 browser checks exercise48 cases/240
crops each,and compare every screenshot RGB channel to its source PNG. The first
UI prototype had a JavaScript escaping/default-selection issue,found by the
browser check before publication;its source/log are preserved in.cache. Fixed
viewers use no resampling and retain accurate approximate-reference labels.

[Final report](../docs/weak-gradient-matching.md) ·
[Final evidence](../docs/results/v173-weak-gradient-matching-final-v1.json) ·
[Initial loss isolation](../docs/results/v173-actual-initial-loss-isolation-v1.json) ·
[Test scope clarification](../docs/results/v173-focused-test-scope-v1.json) ·
[Native viewer verification](../docs/results/v173-native-viewer-verification-v1.json) ·
[Publication verification](../docs/results/v173-weak-gradient-matching-publication-verification-v1.json).
