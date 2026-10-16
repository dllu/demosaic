# Positive ADC-only consistency sample while the fresh models train

The no-context and DINO-S arms complete1000 updates with all41 logged
input/target hashes exact. The live DINO-B arm reaches775; all32 shared logged
positions are exact. Full paired/photo/procedural/GFX/RawNIND review remains
pending, so no learned-context/capacity conclusion or model selection yet.

On CPU only, test a fixed ADC-only consistency correction on the current V43
step2000 checkpoint: P+WB-aware-MHC((y-A(P))*valid), excluding near-black/clipped
samples. No fit, new weights, sweep or production integration. Reuse P within
each case. First8 frozen photos/all16 procedural sources, four CFAs,192 cases.
Photo sRGB improves1.74463dB[.29822,4.42683] and SSIM.004012. Procedural sRGB
improves1.42705dB[.01476,3.43347], but SSIM falls.005121 with an interval
including zero. Source-bootstrap intervals do not establish full427 behavior.
Maximum valid-CFA error is1.49e-8. These are CPUFP32 results, not canonical
GPUFP16 replay or real-noise evidence.

Eight verified native triplets show recovered fabric strands and a large repair
of selected pattern13's color bias. Fine colored edges/aliasing remain. Keep the
operator experimental; add a direct Malvar comparator and all427 photographs
before considering it. The existing local-mean correction remains rejected.
Actual Poisson/read-noise inputs cannot simply enforce noisy observations.

Added a standalone CPU/CUDA probe and six passing targeted CPU tests: all-CFA
fidelity, clipped/near-black measured predictions, exact zero-residual identity,
HDR retention, native code variation under autocast and invalid dimensions.
Production model code and the live frozen training source remain unchanged.
Queue the fullADC-only parent/projection/Malvar check after the actual fresh
capacity controller exits; no owned GPU overlap. Current V43/README aliases and
protected-final closure remain unchanged.
