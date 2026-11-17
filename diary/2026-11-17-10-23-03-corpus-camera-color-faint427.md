# Complete camera and588-color reviews expose scaling costs;427-source faint test running

Recorded: 2026-11-17T10:23:03-08:00 (America/Los_Angeles).

The previous goal turn was progress: completed20k training/native review and
calibrated ADC-bin utility. This turn completes two broader quality reviews,
launches the427-source faint study and retains/compares the actual long-run10k
state. The general weak-detail objective remains active.

The [complete camera review](../docs/full-corpus-control20k-camera-review.md)
binds20k EMA633053… against V120a9d9b6… over all4known/5unseen scenes,
18captures,72/90native crops per model. Known gains0.03284862dB; unseen loses
0.04067307dB,with4/5scenes worse. All324 model/crop rows pass independent
NumPy photometry/CFA checks within5.18e-6dB/2.23e-9;all54 V120 batches and
original metric rows are bitexact to closed CPU controls. Nine native boards
actually viewed;9triplets are exact subsets. Feathers/strands/edges remain soft.
Independent AHD references are auxiliary,not exact RGB GT. Original54-batch
collection used108roots/54DINOexec/54replays; neural seconds1536.390known and
1909.780unseen,excludingload/metrics. This audit/render adds0 learned/GPU/RAW/
noise/optimizer calls. Masked channel-DC/spatial decomposition reconstructs all
324 measured-CFA errors:84.4%of added unseen arithmetic MSE is channel DC;
spatial error also rises. This is not a fine-band/mean-PSNR or causal equivalence.

The observer first used2threads instead of the original4;its exact FP32 check
caught the reduction difference. Originalsource/log preserved;corrected observer
uses declared threads. Frozen renderer first refused an out-of-snapshot artifact
path; recovery uses fresh work/artifacts outputs without changing safety or the
live producer. The failed first board survives.

The [full588-color review](../docs/full-corpus-control20k-color-review.md)
changes the assessment of20k. Worst raw mean bias is765.656DN16 againstV120
55.525,and centeredRMS255.184against24.873. The earlier2-color spot check was
accurate but missed the much larger tail. Existing exact-Malvar repair reduces
20k maximum bias to17.325;ADC bins17.767. OnV120,bins improves aggregate worst
bias13.554→13.039,worst centeredRMS15.150→15.137,andmeanMSE2.15%versusexact
Malvar. On20k,meanMSE improves1.76%but both maxima slightly worsen versus
exactMalvar. Existingexact-sites retains573.366bias and292.747centeredRMS and
shows CFA checkerboards in enhanced errors. Measured-site fitting alone is
insufficient for correct RGB.

All588inputs/147colors/fourCFAs,all8 fixed policies,4704metric rows are closed.
Fresh matchedCPU neural collection1176roots/588DINOexec/588replays takes
3449.335s excludingload;weights/RNGunchanged;16 overlapping predictions bitexact
to previousnativecontrols. Physicalpostanalysis retains3528corrections and
adds0neural/GPU/RAW/noise/training. IndependentNumPy audits all4704rows/summary
identities,every1176ADC-bin output's encoding/GTfeasibility/siteerror,all8
actuallyviewed nativeboards and4exact-subset triplets. All numeric discrepancies
are zero. Native adverse cases are explicitly post-hoc raw-tail selections;
all588cases contribute to scores. Standardcolors look close;error32(red)/8(purple)
shows rawbroadgreen/blue drift andexact-sites checkers,withMHC/bins nearuniform.
No generalfine/noisy-image gain or defaultchange is claimed.

The original100k trajectory retains its10k fullraw/EMA/Adam/RNG state
`6cd409de7ac06d27e528fcd3c9e70944eb03fd75e74f1a59fb342359b5d765a2`.
91raw/91EMA,89finiteAdamstates at10k and100khorizon verified;hardlinked
retention,not a restart. All10000step/source/crop/data-seed rows match control10k
except the correctly different20k/100k order-header SHAfield. First160000order
positions,all40conditioningchunks,andCPU/CUDA/Python RNGstates match. Rawreceipt
truthfully records5038Commonsrow differences;addendum verifies only that declared
identity field differs. Initialnormalizer assumed every sourcekind had thatfield;
its sourceand later explicitlylabeled failure-observationreceipt are preserved.
Native/paired individual IDs remain unlogged; fullGPU sample witnesses remain
in the livephase until it closes. No all-noise-tensor or learned-weight equality
is inferred. The original100khorizon and learning-rate schedule continue.

The new [427-photo faint protocol](../docs/full-corpus-control20k-camera-review.md)
uses all427fixedphotoIDs/fourCFAs in428B4/B3groups/1708imageobservations permodel,
fresh matchedCPU2V120/20kEMA. AllIDs areval/disjoint current90778train;no lifetime
noveltyclaim. Legacyphysicalfunctions reproduce all16oldtargets/inputs exactly
before newforwards. Sourceoriginalmasks/240interior/DCT16annulus[1/8,1/3) and
fixedraw/exactMHC/sites/binpolicies are frozen. An explicit pre-analysisaddendum
clarifies renderedlinearRGB eligibility where initial metadata saidcameraRGB;
originalplan and executedpreparersnapshot remainunchanged. No newpredictions
were inspected to make thatclarification. No standard427score/result is claimed.
Genericcollector now records declared batchsizes rather than calling every jobB1;
no neural operation or liveworker/source was changed.

Latestidentity+progress check: controlprimary318/3162,sceneprimary559/3162,
faint75/428;all live with matched PIDcreationtime. Longrun15500optimizersteps,
original100khorizon. Both588collection andphysicalanalysis are terminal-complete,
withanalysisreturn0;fullfaint and primaryphoto jobs still run. No training signal,
restart or frozenplan mutation. Full427 plus broad96075-block analysis/history
remainpending;camera/color completion does not fill those missing scores.
V120/V131 remain lastcomplete three-panel history;general recommendationV120.
README stays concise/unchanged;currentmodel/experiments/research/index/training
andGFX reviewmaps link completed camera/color evidence. Both standing fences
remain the previously actuallyviewed20k outputs,sameEMA/conditions;ADC helpers
bypass their positive priors exactly.

Publications preserve636(camera/progress)+946(color)exact evidencefiles and
18+12originalnativePNGs,with independent audits and executedsource bytes.
Largeweights/arrays remain local with hashes. Oldarchives/receipts are untouched.
A useful next throughput task is a separately admitted IEEE-FP32 GPU evaluation
qualification against exact retainedCPU inputs/outputs under strict numerical
bounds and a small memorycap. Existing CPU workers remain live;no GPUneural
qualification or migration has happened in this turn. Faster broad evaluation
would let the100kmilestones guide model changes sooner while preserving exact
source/conditioning/metric contracts.
