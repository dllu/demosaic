# Separate the fixed spectral innovation with diagnostic GT

The preceding goal turn made progress: the complete seven-condition photo/GFX
pilot and independent array/native review finished, rejecting unconditional
unit gating. Commit365b2e5 is pushed. V43 remains working. The complete PROMPT
objective stays active; SOTA, decisive real-photo superiority and100MP/10s
are unmet/unproven.

This turn takes the next available evidence-producing action without another
training job. The frozen plan binds the genuine V89 saved arrays, all46 original
model modules and66 source/helper/input files. Keep its base and observed
spectral mask fixed. Split the unit innovation into L(A(target)-A(base)) and
L(observed-A(target)), where L is the same Fourier mask and signed/WB Malvar.
Both isolated outputs explicitly use GT and are labeled ORACLE. Neither can
be used for inference. The discrepancy includes noise/ADC and, for highlights,
the physical-to-canonical-target mismatch; it is not universally pure noise.

The new independent FP64 NumPy MHC implementation passes24 signed CPU fixtures
across all four CFAs and two WB settings, maximum difference2.93e-8 versus the
original FP32 module. All seven original conditions/two sources prepare without
new quality scores. Decomposed innovation/unit replay against the saved genuine
outputs has maximum error4.50e-7/4.59e-7, below the fixed5e-6 bound. No learned
model, original capture, source HDD, GPU or protected-final source is used.

I actually viewed both fixed native boards before computing new component
scores:20 triplets/28 unchanged160px cells. High-noise grid and canopy-edge
banding appear in the discrepancy-only oracle, while the target-only oracle
largely removes those patterns but still misses the radial cords. Highlights
give a materially different result: target-only creates strong pink casts and
discrepancy-only green/cyan casts; their sum partially cancels. The actual-view
receipt SHA256 is
d4794503a67d9e3323e6aeadab58185eb4e31c58d284ee023ec874599dd18337.

The target term reduces unclipped camera RGB MSE on all14 evaluation fields,
but its mean sRGB PSNR loses in five of seven conditions. At highest noise,
target-only versus base averages-.15357dB, discrepancy-only-3.45710dB and
unit-2.62327dB. Discrepancy energies are3.84/2.72 times target energies on the
two sources; their incremental MSE after target is positive and dominates the
target-term reduction. All cross terms are retained; this conditional algebra
does not estimate independent noise variances or identify a unique causal share.

In highlights, target-only loses14.9041dB and discrepancy-only12.8167dB versus
base; unit loses6.3140dB. Better raw camera MSE and measured-CFA agreement do
not guarantee displayed color fidelity. The complete-field target oracle
contracts measured-site L2 error on all14 observations, as A*Malvar=I and mask
weights lie in[0,1]. That property does not cover local ROIs/unmeasured RGB or
the WB/matrix/display metric. The current result rules out a simple claim that
removing only stochastic noise would make this fixed unit innovation reliable.

An independent Torch CPU auditor checks98 original array fields byte-for-byte,
the Fourier/measured-site arithmetic within5.00e-16 and original FP32 MHC within
1.24e-7. It checks224 MSE terms plus420 metric scalars: largest MSE difference
2.78e-17 and original FP32-rendered PSNR difference.00000241dB. All84 previous
PSNR witnesses replay within.00000751dB; the full MSE identity closes within
1.39e-17. All20 triplets/28 native cells pass metadata/pixel checks. CPU RNG
remains unchanged and CUDA uninitialized. All three diagnostic phases and
the independent audit exit0; there is no pending worker.

Artifacts remain in
`/mnt/external/demosaic/experiments/spectral-innovation-split-v1/`.
Plan SHA256be3c54af418e3b98ff07febf26fe957ad52265d79555778ce3c3c35413836d3d;
final-review SHA2566ae64b6194baf26a2da81078bea844517dcabf48edf0c3bced1608985b9c3101.
Arrays total135.67MiB. Documentation publishes both boards and20 native
triplets with complete source/ROI/checkpoint/noise/display bindings. The
requirements/experiment index link the completed diagnosis. README V43 and
standing real-GFX evidence remain; no false GFX GT oracle is constructed.

Ruff lint/format, git whitespace,259 local links and22 public PNG byte copies
pass. At06:55UTC external space is529.38GiB and root113.01GiB, above the
500/64GiB reserves. No more download is started. There is no training update,
serving/default change or quality promotion. A next quality experiment should
learn joint RGB reconstruction and noise/semantic selectivity; a matched
late-DINO refinement hypothesis needs its own fixed plan, engineering and
actual trained/native quality evidence. Increasing the fixed Malvar correction
is not justified. The full project objective remains open.
