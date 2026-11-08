# Implement local phase-evidence matching with the same parameter budget

Recorded: 2026-11-07T22:50:52-08:00 (America/Los_Angeles).

Implemented V180 `LateLocalPhaseEvidenceMatchingDetail` as a separate new source
file, preserving all 97 earlier neural files. It uses V178's global one-green
phase selection, the same zero 80→39 adapter and matching network, but supplies
local affine-projected complex coefficients. Defaults are a 65-packed-sample
box and 32-sample stride with the final pixel included. FP64 moments include
the fitted-plane noise terms; normalized coefficients interpolate at actual
integer centers. Finite windows and interpolation still spread support, and
interpolated powers are not calibrated SNR. These choices follow V179 training
evidence rather than blind validation.

All 112 focused CPU tests pass, including 24 new layout, reference, interpolation,
support, contract and test-double gradient/parity checks. The first run passed
23 tests and failed one exact off-grid interpolation expectation because two
floating-point expressions were grouped differently. Its source/log and the
unchanged first neural source are preserved. Only that off-grid expectation
now allows 4e−15 rounding; center equality and reference tolerances remain fixed.

The frozen CPU profile passes all six retained cases: four training RAW batches,
the protected main overcast sky and fine green cab mesh inputs. Twelve Torch
feature calls cover 36 images; 18 independent NumPy image calculations check
85,196,800 FP64 feature values and 21,152 center powers. Maximum errors are
1.05e−12/1.28e−13. All selected bins match the old verified selections; all FP32
feature bits equal the FP64 cast. Single-call CPU feature times range roughly
0.10–0.74 seconds, with local moments internally FP64. Peak RSS is 1,349.67 MiB;
this is not model throughput or CUDA performance.

One old V172 CPU checkpoint load verifies raw and EMA initialization: 188 old
tensors exactly retained, one zero 3,120-weight adapter, 142 trainable tensors
and 2,092,026 trainable parameters. Corresponding V178/V180 tensor hashes are
identical at initialization despite different feature operators. Future state
provenance must include class/configuration/source. Adam restoration for the
new variant is not established. Frozen imports resolve inside the new snapshot.
No actual matching/frozen/parent/DINO/sampler forward, optimizer update, new
noise, RAW decode or CUDA initialization occurs in this profile; RNG is unchanged.

At 22:54 PST the original V175 owner is still running at total row 8,090 with
7,279 total updates. Its completion watcher and both V178 waiting controllers
match their original PID/create-time identities, with no failure receipts.
No V180 GPU job is queued. Existing source snapshots, recipes and old evidence
remain untouched. RAM/local/external free space is about 76.09/60.48/113.93 GiB.
No originals or `/mnt/dataz` are accessed; cached protected input arrays are
used only for feature geometry, and both scene families remain out of training.

Updated the README and documentation to expose the implemented prototype and
its remaining CUDA, training, interpolation and quality questions. No new RGB
comparison or quality gain is claimed. Measured V120/V172/V161/quiet/flat choices
and existing native triplets remain available. The numerical report and source
bindings are in `docs/results/v180-local-phase-preparation-v1.json`.
