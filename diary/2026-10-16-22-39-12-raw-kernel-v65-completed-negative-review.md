# Completed V65 warmup review and phase learnability diagnostics

Previous goal turn was progress: completed/pushed V63/V64 review and launched
bounded V65 after actual CUDA checks. This turn revalidated actual live owners,
then V65 completed original1000 budget and trainer exited. Independent full-state
check verifies SHA4cce53075921807ba15bc37717052aa0425ede752e4dcc5d9b40f6f6f9395d0a,
93model/93EMA/twoAdam finite, all91existing model/EMA tensors bitwise V60parent,
original1000/source32a/data/recipe/RNG/41logs. Reconstructed sourcebundle from
actual archived bytes matches. No model-source edit or schedule retiming.

Full quality review now completes. Photo27.83246/.821633, procedural29.00491/
.856454, knownCFA44.22499/unseen41.44299. Relative parent photo-7.83182dB,
known-9.98626/unseen-12.31726. All source intervals negative. Native noise stays
close to bilinear. Means in color fields are close toGT but residual RMS is
large; this is not a color+denoising improvement. Neutral highnoise spatial luma
RMS.01393; carrier gains.825/.917 are not useful recovery when noise remains.
All26new nativePNG triplets actually viewed. Eight unchanged native512x192PNGs
published: two exact-GT photo sources, four standingGFX regions, one weakcarrier,
one hue field. Every source/ROI/checkpoint/noise/display record retained. Real
references accurately labeled nonGT. No promotion or jointstage; V43 remains.

Primary50264cases/36savedcomparisons/nineclassicalwitnesses independently audited.
New grid1176arrays/7056Torch64fields/18groups216scalars. Old V60grid source records
match but old arrays not merged into changed-source report. SelectedCPU32arrays/
192fields. Analytic896cases/56groups/1504scalar arithmetic, max2.22e-16; first
private descriptive receipt accidentally retained historical3model counters,
corrected-v2 derives counts from checkedcollections with unchanged checks/bounds.
Original wrong-count receipt/source retained. No per-case analytic prediction
recomputation claimed. FullGFX101.996MP linear16/sRGB16 verified,50.670s/4.255GB
CUDAallocation.19primaryPNGs/23F32/twoTIFFs;4nativeTIFF/PNGmatches exact.18threecam
rerenders have2one-code differences under unchangedhistoricalpreviewbound.
All primary/statistics-hue/artifact owners terminal/exited. Protected-final unused.

New utility wiring preflight uses actual113094historicalcases,72computed
comparisons,60directpublishedcomparison replays exact,18witnesses; pending
owners rejected beforeoutput. First test assumed V62 retained V60full4k, but
its publication used V60first1k; corrected test uses24matchingV62+36V63 direct
replays, labels12additionalhistoricalcomparisons as newlycomputed, notreplays.
Originalfailedlog/source retained. Generalized artifact helper one/two-model
counts, and verified exact entire genuine V63/V64 oldresult plus19PNGs/23F32/
twoTIFF V62 path and actualseven-update93model/93EMA/twoAdam head fixture.
Prototype phase input is still future. Pendingstatshueowner rejects early.
No fullmodelCPU-suite rerun needed because modelsource32a unchanged; relevant
utility verification is these actual historical/state replays and ruff.

Read-only two-photo CPU diagnostic shows coefficient RMS.00366/.00295,
correction RMS.00249/.00401 and no tanh saturation. Production V65 weights remain
unchanged. Separate discarded standalone-head CPU probe: B4/native64/512steps,
new Poisson/read noisy constants [.12,.23,.47], MSE, trainseed2026101701,
independentscoreseed2026101702/64observations. Gainsvsbilinear: RGGB/zerofeatures
3.223dB; fourCFAs/zerofeatures1.036; explicit16CFA/nativephasecategories7.036 at
sameLR2e-4; sameexplicitcategories/LR2e-3 gives18.952. Cleanconstants exact.
No photo/evalgrid targets or productioncheckpoint used. This motivates a separate
matched direct-phase-conditioning trial, not a causal diagnosis or realquality
claim. Existing V65 frozen encoder already sees CFA indirectly. Next engineering
step: optional perCFA/nativephase coefficient offsets, defaultoff, preserving
old routes/RNG and allcleanconstant invariants; do not change LR simultaneously.

Public report docs/raw-kernel-warmup-v65-first1k-review.md with matchingJSON.
Goal remains full PROMPTquality/speed/16bit/SOTA; not achieved. No coldRAWreads,
source/manifests/standingselection substitutions or duplicatejobs. Downloader
continues. No new production variant has launched at this entry.
