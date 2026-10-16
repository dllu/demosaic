# Full427 ADC-only evidence and optional inference policy

The frozen full-sample follow-up completed after the original fresh-DINO
controller exited:5316 cases across427 photos/all16 procedural sources/four
CFAs/parent+projection+Malvar. Photo+.52882dB [+.45370,+.61337], SSIM+.003923;
355 source means improve and72 worsen, median+.45716dB. Procedural PSNR
+1.42739 but SSIM−.005119; chroma/edge tradeoffs remain. Published12 verified
native triplets with exact GT, source/ROI/noise/display/checkpoint hashes.

Moved the predeclared physical operator into cfa.py and shared it with the
standalone probe. Added default-off adc_cfa_projection to the stabilized RGB
model. Only explicit shot=read=0 profiles select it, independently per image;
variance maps cannot silently trigger it. Positive shot or read bypasses it.
Clipped/nearblack measured channels retain the prediction; no HDR clamp or
learned state is added. Frozen training source/recipes remain unchanged.

V52 is an inference-only copy of unchanged V43 step2000 EMA, only this flag
different. Sixteen operator/integration tests pass. Full CPU suite387 pass,
eight CUDA checks skip; five subsequent exporter tests pass separately.
Genuine pinned-weight CPU preflight passes both shapes/allCFAs/FP32+BF16,
mixed/scalar/noisy priors and tiled16-bit ramps. CFA errors below6e−8;
CUDA never initialized. Source/weight/export hashes are archived.

The fresh three-arm continuation is live from1000→3000 with original whole
optimizer/EMA/RNG and10000 schedule, immutable first1000 copies, source8580a4e.
Initial uv launch exited before imports/training; retry pins the installed
shared venv and frozen PYTHONPATH. No overlapping owned GPU benchmarks.
The new policy's actual CUDA/all-condition/paired/full-GFX check must wait for
that controller's actual exit and success. No alias/README promotion or
real-noise quality claim. Goal remains active.
