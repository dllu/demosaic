# Signed recent JDD exports: actual CPU/GFX comparison

Previous goal turn was progress: physical frontend check, final-review tooling,
queued owner1753053 and commit339b360. This turn revalidated actual training
owner1748140 and both waiting owners; no overlapping owned GPU workflow.
Control has reached its original4000 boundary, immutable checkpoint
a6e494a121b99e311c6be4d24794929f625c3690448588f7d3d1c1af3273dadc.
Wide resumes its own complete first1k state and continues its original schedule.
No source/data/loss/augmentation/schedule change to either running arm.

Primary-source follow-up: darktable5.6 uses RawNIND already covered here. Recent
ACKN continuous kernels use signed cross-color weights/L1 normalization; they
do not inherently guarantee constant-RGB preservation. Burst/nonuniform-sample
scope differs; no code/weights imported. 2-Shots motivates dark-frame spectral
noise synthesis but supplies no calibration for our GFX. Added source citations
and corrected stale mature-ConvNeXt/nonlocal-CUDA status in research.md.

Found RawForge's May28,2026 signed JDD release. Cached source79f17700c29765b28a4cf5bd1b6d90bc7e3eb7f2
and publisher JSON, two registered model artifacts/signatures, pinned RawHandler
0.2.2 wheel888b817669394ad190c5e2b9bc6905006b76e28423a3f5d987bb9e1f470a4e27.
Verified both GitHub SHA256s and actual publisher RSA-PSS/SHA256 signatures with
OpenSSL. No package installation/dependency stubs, HF credentials or source HDD
access. CodeMIT; separate weight license/training membership remain unspecified.
Weights stay external comparison assets, never bundled/defaulted/trained from.

JDD256 originalSHAe3ab1b52c14e10d77fbe41c4b3530de69d533be335c2f390c26f2de1650393fc;
JDD originalSHA77b9e403b4feb4579cf1eb677c7d8098cf2725dd6e433414ea8fc333e426d7dc.
Each11,319,924params/163parameter tensors,164 total state tensors finiteF32.
OriginalCPU backend passesF16 toF32weights and actually fails. TorchScript also
embeds CUDA0 in positional coordinates. ExplicitCPUport changes one sharedDevice
constant only, exactothergraphtext/all164tensors throughsave/reload. Finite64×80
rectangular forwards/repeats pass with noCUDA. First inspection attempt failed
only because its error-message guard assumed lowercaseFloat; retainedv1 source,
corrected actualerrorguard and completedcpu-port-v2. No fabricated success.

CPU pilot freezes two earlier saved256px photo observations and allfour saved512px
GFX contexts. Reconstructed integerADC, publisher phase-black/sparse/mask/clip/
F16quantization, expandedF32 arithmetic. Blind model gets noISO/shot/read. Its
nominal output conversion preserves published mean-black convention; noGT/input
gain fitting, newnoise, RAWdecode or referencewarp. GFXphaseblackvalues differ;
that nominal convention is documented, and ISO100 stays unscored/notGT.

Actual12predictions/36F32 arrays/12nativePNG. Independent auditor: all12 inputs
bitexact to publisher helper, ADCreconstructionmax7.53e-8, nominalunitconversion
max6.12e-8,8PSNR scalarchecks2.25e-6dB. All36nativepanels rerender exactly;
common noisy/reference pixels byteexact to earlier methods. FourCFA ×2black
fixture matches upstream at bothADCendpoints. Later linter/fixture-only changes
do not replace the archived actual executed pilot source.

Actually viewed12new triplets,2savedV43photo triplets and2native directGFX rows.
Parachute cords lost in both newmodels; building weak/blurry orgrainy. JDD's
fence/foliage better thanJDD256, but directV43mesh is morecontinuous/regular;
RawForge crossings weaker/grainier. Finefoliage stayssoft. Corrected commentary:
768 is registered serving tile size, not verified training crop size.

To compare withsavedV43/RawNIND, rescored newF32predictions onoriginal240px ROI,
separate from160px previews. No repeated unchanged network inference. Two
Malvarcontrol rows: oneexact, one2F32ULP chromaMAEdrift under inherited4ULPbound
fixed before these results. Sourceids/nullable support exact. Fabric/building:
V43 40.69080/35.20764dB; JDD25633.37561/29.72892; JDD35.04916/29.61016;
RawNINDchannel29.83785/26.17905. TinyselectedCPUcomparison, no broad ranking.

Queued original-exportGPU checker owner1784864 creation1792200897.58, actual
waiting/nochildren verified, behind1753053 actualsuccessfulexit. Frozen toolset
and CPUinputs; worker runs original signed files, no graph modification, in
no-enclosing-autocast and authorFP16 modes, retaining all24outputs. Captured
convolutionTF32 flags preserved, noIEEE-FP32claim. Predeclared no-autocast
CPU toleranceabs.002+rel.002, allmismatches retained; FP16drift descriptive.
Actual premature invocation rejects beforeCUDA/output. No GPUparity passed yet.

Published CPUreview/16nativeimage receipts/citations. V43 remains workingreference.
Final4k training/full evaluation/manualreview, originalGPUparity, SOTA/broad real
superiority, protected-final and10-second objectives remain unresolved. Goal
stays active. Downloads continue with512GiBreserve; foreign jobs untouched.
