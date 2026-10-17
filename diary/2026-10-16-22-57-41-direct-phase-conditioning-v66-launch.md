# Direct phase-conditioning implementation, checks and matched V66 launch

V65 complete negative quality review committed/pushed0f88b3e, reportSHA
48c152008963baad4a97e6c15376eef010af6ea982351b4bef6638825247f843.
Working V43 unchanged. No SOTA/quality/speed completion claim.

New optional raw_kernel_phase_conditioning defaultFalse adds4CFAx4nativeposition
coefficient-logit vectors:5184parameters with default3supports. These offset
kernel logits beforetanh, never addRGBoffset. Existing67feature coefficientmap
retained; same-color-centeredRAW differences retain cleanconstantRGB. New zeros
consume no globalRNG.94restorationtensors/threeheadtensors;27216trainableheadparams.
Sourcebundlefc0297db08d659523fdcefe1ef0e7a4da12ae97f648e95b1579db65de93d268a.
Frozen candidate package is authoritative; do not edit it or running recipes.

35targeted tests pass; complete CPU543passed/9CUDA-relatedskips75.31s. Tests
address all16CFA/nativepositioncategories with distinct independentexpected
coefficients, arbitrarystrongcleanfieldinvariance/BF16, checkpointgradients,
headonlyoptimizer/frozenEMA and RNG/statekeys. Genuine-parent CPU B1/native64/
FP32/workers0/forcedsmoothCommons/val2: defaultoff exactlyreproduces prior32a
fourupdate model/EMA/optimizer/Python/Torch/CUDARNG/step/best andnumericlogs/input
hashes; model_config adds defaultFalse, semanticallynormalized ratherthanraw
metadataexact. ActualV65 twofull256CPUphotoarrays bitwiseexact. Enabled7updates
match3+4resumed all9statefields andlogs. Matchedcontrol/phase all7inputhashes,
domains,LRs exact. All94model/94EMA/3Adam finite, all91oldmodel/EMA tensors
bitwiseV60parent,3stateoptimizerrestoreexact, allmanual/portableEMA tensors
includingactualDINO and2photos exact. Oldmodelsource/checkpointsuntouched.

Actual discarded CUDAfixture7B16/native256/BF16,workers0/forcedrealCommons/val2,
original1000/LR2e-4/warm50/seed49: all7inputhashes/domains/LRs EXACT to original
V65GPUfixture. All94model94EMA3Adam finite; all91parenttensors unchanged; portable
FP16/BF16photos andcompleteoptimizer/RNGreconstructionexact. ActualDINO frozen.
All3headgradients finite/nonzero, restfrozen/gradientfree.64cleanconstantcases
(4colors4CFAs2conditions2precisions) pass3e-7bound, no addednoise. Peakallocation
16.709GB, notUMAorproductionthroughput. IndependentCPUsavedGPUstate/source/
guard/log/controlhashcheckpasses. No deterministicCUDAoptimization orqualityclaim.

V66 freshmatched1000-update phaseheadwarmup STARTED, controller2517880 creation
1792216430.60. FrozenCUDAcandidatepackagefc0, parentV60EMA/freshAdamWEMA, only
phaseflag/run/notes differfromV65 originalrecipe. LR2e-4/warm50 NOT changed;
sameB16/native256/BF16/seed49/original40170Commons/native128/paired32/fractions/
widepalette/geometry/noise/validation/workers. Startup27216trainableparams,
productionupdates observed. NoV65resume,jointstage,autopromotion,outputfitting,
protectedfinalscore,raworiginalreadordatasubstitution. All41loggedproduction
observations/domains/LRs mustmatchV65at1000. Trainer guards fullstate andfreezes
models/dino-convnext-raw-kernel-phase-warmup-b16-v66-step1000.pt thenstops.

Primaryqueue2518363 creation1792216468.00 waits exacttrainerexit/finite94/94/3,
frozen91parent andall41matchedlogs. Original50264primarycases/analytic/fullGFX/
threecachedcameras/selectedCPUcolor use frozenfc0sourceandtestedpaneloperators.
Status paths /mnt/external/demosaic/runs/raw-kernel-phase-warmup-v66[-review]-workflow-v1.json.
Plans/logs /mnt/external/demosaic/benchmarks/raw-kernel-phase-warmup-v66[-review]-workflow-v1/.
Inspect actualPID/creation/child beforeacting; no duplicate/restart on observationtime.

NEXT REQUIRED WHILE V66 TRAINS: adapt review_raw_kernel_results.completed_primary
and audit_raw_kernel_artifacts.audit_head_state for phase94/94/3 with legacy93/93/2
stillvalid. Add retained V65review as MATCHED comparator (currentlyscorehelper
onlyV60/V58/V43; V66needs48comparisons/12witnesses including12V66-V65). Existing
V65reviewJSON schema uses artifact_integrity.runs. Validate actualcompletedV65
legacygate andstate plus genuinephaseCPU7state; genuineV65self-comparisoncan
checkadditional-registry arithmetic withoutnewinference. Then queue statistical/
hue/artifact followups after exactprimaryowner. Generic hueengine supportsone
new1176array/7056field/216groupscalar run underfc0; no legacyarraymerge. Actual
nativeviews andreportneed2exactGTphoto+4GFXregionsaccuratelynonGT. ExistingV65
privatefollowups can be adapted but oldtensor-countgate MUST NOTbeclaimed valid
for94phasevariant. No further modelsourceedit duringthisfixedmatchedtrial.

Public docs/raw-kernel-phase-v66.md, results/raw-kernel-phase-preflight.json and
raw-kernel-phase-v66-launch.json. CPUfixture .cache/preflight_raw_kernel_phase_cpu.py
archivedexternally; CUDA .cache/preflight_raw_kernel_phase_cuda.py archivedin
benchmarks/raw-kernel-phase-CUDA-preflight-v1. Fullreference/standingconfig/cold
originals unchanged, Commonsdownloadercontinues. Goal remainsactive.
