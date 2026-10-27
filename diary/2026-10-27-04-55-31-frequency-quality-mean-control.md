# Complete frequency-adapter quality review and start the mean-loss control

Recorded: 2026-10-27T04:55:31-07:00 (America/Los_Angeles).

V122/V123's original full evaluation, primary/analytic audit, saved comparisons
and four extra-mesh endpoint forwards completed. V124 then started automatically
under its existing controller/plan, after the exact declared dependency chain.
The previous goal turn made progress: completed/published V130 and the48-call
faint-ADC panel, with matched inputs, independent reductions and actual crops.

Closed the selected native frequency review without new inference. Actually
opened five material boards, ten main-GFX comparison boards and four two-profile
extra-mesh boards. Retained the preceding four exact-GT bark/canopy triplet views
and twelve full-frame GFX triplet views. The additional mesh still uses corrected
DSCF3842 ISO6400 / DSCF3835 ISO100 f/5.6, plus both camera JPEGs. Main3879/3880
remains in use. Fine foliage is painterly, neon/platform edges soft, the broad
fence coherent; nominal conditioning mostly erases the fine lattice. Nearby3879
conditioning leaves weak irregular texture. Neither arm supplies a large recovery.

Quantitative final results, original FP32 reporter:

| Model | Photo | Known CFA | Unseen CFA | ADC maximum DN16 |
| --- | ---: | ---: | ---: | ---: |
| V122 |36.97786184 |54.32375367 |54.00029627 |65.63843 |
| V123 |37.03279048 |54.32306300 |53.97248336 |4190.02216 |

Independent float64 scoring agrees within roughly2e-6dB. Matched V123 versus
V122 full-photo gain is0.05492862dB,411/427 sources rising, source-bootstrap95%
interval[0.04935,0.06130]. Unseen-camera change is-0.02781368dB. Positive-noise
color maximum improves103.48→89.88DN16, while the ADC maximum regresses greatly.
V120 remains the useful general balance. No promotion gate hides the gains;
the actual weak-detail and color tradeoffs guide the choice.

Both original20k arms use V115 Small/90786 sources/fourteen regions/seed66,
zero optical blur and geometry before final downsampling. V122 trains only its
3,264-value adapter/five tensors, preserving all91 common model/EMA tensors.
V123 also trains the common path, with94 Adam states. Its preserved12,249 prefix
plus exact7,751 continuation remain intact. No training prefix, check or old
inference was repeated. Existing receipt/checkpoint hashes retain their bytes.

The full local-photo audit covers427 sources,5,124 paired observations and96,075
unique eligible16px blocks. Source-balanced weakest0–2% ISO12800 projection:
V1150.36421786→V1220.36464960→V1230.36500309; V123 band-error RMS falls
0.00318511→0.00318046 against V122. The eight-pixel2%-contrast carrier gain rises
0.15217→0.15883 for V122, with higher noncarrier residual; V123 reaches0.15263.
Independent cosine/FFT differences stay below1.85e-14. These small changes do
not resolve the photographic attenuation.

Both complete101.996MP linear/sRGB TIFF pairs have verified dimensions/type.
The retained-FP32 linear quantization audit checks921,600 RGB16 values at six
native ROIs per endpoint; it does not independently recompute sRGB16 quantization.
Older V115/V117 main-GFX outputs use a different fixed Haar profile from the
new nominal V122/V123. Those boards retain explicit labels; they cannot isolate
a model effect. V122/V123 itself is matched. No matching-profile replay was added.

Independent NumPy64 mesh display checks1,843,200 channels, with only four
one-DN8 differences from FP32 rounding. Both variance maps are exact and inputs
otherwise identical.160 material/GFX panel hashes match12,288,000 channels.
Published23 PNGs unchanged, checking19,226,304 channels exactly. Both models have
two native exact processed synthetic-GT triplets, correct sources/attribution,
ROI/checkpoint/noise/exposure metadata and both qualitative GFX scenes. Real
ISO100/AHD references remain approximate, never exact GT.

Final public results: `docs/v122-v123-quality.md`,
`docs/results/v122-v123-quality-complete-v1.json`,
`docs/results/v122-v123-quality-publication-verification-v1.json`, and
`docs/images/v122-v123-quality-v1/manifest.json`.
The actual native review and independent pixel audit are retained under
`.cache/current-quality-20261023-v1/V122-V123-final-publication-v1/`.

Updated the source-bound version plot to56 full primary endpoints, adding122/123
and preserving every field of the54 earlier points. Previous canonical plot,
SVG/PDF, history page and executed plot script are byte-exact archived copies
of gitHEADd9a44d0 under `previous-history/`; old JSON/CSV registries stay intact.
The new registry is `docs/results/version-PSNR-history-v123-current-v1.json`.
Actually viewed the rebuilt plot. V120 remains the plotted reference.

Current README/method/research/requirements/data/training/GFX pages now distinguish
completed frequency results, live mean-loss control and the still-untrained
90781/29 cohort. Active/frozen cohort bytes were not changed. Corrected stale
queued/unmeasured descriptions in the current docs rather than changing history.

Verified V124 worker2025028/create1793101753.04 live under controller1945904.
The original frozen90784/twenty-region two-noise-view control has started;
at the retained snapshot step400, loss and gradient norm are finite. This is
not a finite-state endpoint audit or quality claim. Both simulated views use
16 unique targets/32 observations; real paired batches retain their original
single-observation path. V125 follows at mean weight0.25 with its original20k
budget. Four CPU/CUDA16+2 check receipts are adopted; no check was rerun.
Original48h worker deadline,24GiB CUDA cap,64GiB launch headroom,32GB runtime
floor and disk reserves stay unchanged. The progress snapshot is
`docs/results/v124-control-training-start-v1.json`.

Final checks pass701 local links and14 preserved plan/receipt bindings. Eight
existing version-history tests pass in0.09s with `PYTHONPATH=src:scripts`;
the first collection attempt omitted that path and ran zero tests. Ruff and
whitespace checks pass. Documentation/history/source verification is in
`docs/results/v122-v123-final-documentation-verification-v1.json`.
The broad quality objective and100MP/10s target remain open; quality remains
more important than speed.
