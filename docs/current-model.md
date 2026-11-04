# Current model choices

The new [supported-amplitude option](supported-wave-amplitude.md) keeps the
original positive global gate as selection and restores contrast only inside
unchanged reciprocal support. Fresh mesh response rises 26.4% and image RMS
falls 1.0% versus cross; mean/worst added blank RMS rise 42.1%/28.4%. All 256 absent
cases and 64 new photographic controls retain their parents. Full GFX mesh
contrast improves under both priors; nonperiodic texture, support seams, boundary
spill and highlight color remain unresolved. The explicit `detail` mode has
53 inspected native comparisons and complete RGB16 checks. V120 remains the general model recommendation. Detail is now the default
inside the explicitly enabled periodic stage.

The earlier [reciprocal green-support review](cross-phase-support.md) cuts fresh mean
added blank RMS 89% and its worst case 92% versus wide context, with 9.5% lower
response and 0.8% higher image RMS. Both full-frame mesh priors retain much of the
lattice. The known detached false patch is removed; weak/partial detail and
boundary spill remain. All 256 fresh absent neural cases retain parent values.
The explicit `cross` mode has 37 viewed native comparisons and complete RGB16
audits; it is a stricter support option, not a broad model-quality claim.

The [guarded wider-context option](wide-phase-context.md) uses actual 512-pixel RAW
contexts and measured higher harmonics on V143. Fresh 64-recipe response rises 14.4%
versus sparse support and image RMS falls 1.2%; mean added blank RMS rises 17.3%,
with a 17.4% lower worst case. All 256 absent neural cases and 5,120 ideal-flat
matched/mismatch executions retain parent values. The first unguarded version
failed the mismatch control and is archived. The explicit `wide` mode adds a
conservative variance floor; detached tail stripes, boundary leakage and very
weak recovery remain.

The [connected support/refit option](sparse-phase-support.md) gives stronger mesh
contrast on V143 and 12.8% higher fresh response with 34.0% lower mean blank spill
than refined TV. Worst-case blank RMS rises 39.2%; a known isolated stripe failure
is removed, while boundary leakage remains. Use the explicit `sparse` envelope;
Grid-TV is retained explicitly; Detail is the current optional-stage default. The wider sky, final absent inputs
and fixed photo/uniform checks retain parent values. Learned weights are unchanged.

The additional [continuous frequency option](offgrid-phase.md) gives modest,
placement-sensitive mesh changes on the same V143 parents. Fresh 64-recipe response rises 3.7% versus
fixed-bin TV with slightly lower texture error and 8.5% higher added blank RMS.
The tested wider sky and all 256 absent inputs stay unchanged; 4,096 new pure-flat
noise draws select no waves. Add `--phase-harmonic-refine-frequency` to the optional
TV stage; fixed-bin TV remains the default without that extra flag. Highlight
changes, partial spill, window sensitivity and runtime remain limitations.

The earlier [TV phase fit](edge-phase-envelope.md), available as explicit
`edge`, gives clearer crossing mesh on complete V143 frames and
unchanged wider sky. Fresh 64-recipe validation finds 48.8% less mean added blank
structure versus the Gaussian complex envelope, slightly higher texture error
and some blank regressions. Highlight color and runtime remain limitations.
Both `complex` and `scalar` remain available. General inference still disables
correction by default; weights are unchanged.

The earlier [scalar phase-aware correction](local-phase-harmonic-patch.md) on V1435k
patches gives stronger fine diagonals in both mesh windows/priors. In the active
new validation recipe, added structure in complete-patch blank regions falls62%
versus the first harmonic correction, with stronger response and lower error.
Spill remains measurable; tested96-photo/48-flat parent values are unchanged.
The [optional tiled inference path](phase-harmonic-inference.md) now processes
complete102MP RGB16 outputs. Regular window placement can weaken the centred-patch
gain, and CPU correction is slow. V120 stays the validated general recommendation.

The [completed V1435k review](v143-final5000-quality.md) gains0.26493dB faint
ADC PSNR and4.64% lower noisy-flat spatial RMS over V120 on fixed support.
Coarse noisy error remains2.63% higher and ADC-only spatial RMS12.85% higher;
training alone still lacks clear new mesh recovery. The read-only endpoint is
`/mnt/external/demosaic/models/v143-final5000.pt`. Its faint/shadow gains are
useful for further quality work. [Complete-frame GFX inference](phase-harmonic-inference.md)
now covers the main scene and both fine-mesh priors; full427/camera evaluation
remains open.

The [completed V1411k loss comparison](v141-gradient-epsilon-pilot.md) gains
.01528dB faint ADC PSNR over matched V129, with mixed weak-band changes and no
new fine-mesh recovery. Both continuations have about5.8% more coarse noisy-flat
error than V120, which remains the general choice. The completed
[V142 crossed-line/empty data trial](v142-crossed-line-pilot.md) adds.05212dB
faint ADC PSNR and4.55% lower noisy-flat spatial RMS versus V129. Coarse error
remains5.08% above V120, selected ADC-only DC bias worsens and mesh remains weak. The October V125/V131 workers and their dependents stopped;
the [V140 execution audit](v140-standalone-pilot.md) preserves their receipts.

**V120 Small is the general restoration and quality-development recommendation.**
Its completed 427-source photo mean is 37.04008 dB, known/unseen measured-CFA means
are 54.31272/54.00872 dB, and tested ADC maximum color bias is 55.52 DN16.
It retains V119's photo gain while recovering its camera/color regressions.
Full panels, saved-output audits, native comparisons and 102MP RGB16 exports are
complete. [Primary evidence and matched-profile full frames](v120-v121-primary.md).
Fine foliage, low-contrast texture, saturated signs and the green mesh still need work.

Architecture follows measured strengths rather than historical promotion gates.
V120 keeps the V84-family pretrained DRUNet RGB trunk, physical noise/camera
conditioning and official frozen DINOv3 ConvNeXt-Small pyramid.
[Implementation and pinned encoder](research.md#foundation-features-and-the-new-objective).

| Use | Useful choice and measured tradeoff |
| --- | --- |
| General RAW and quality development | **V120 Small**: photo37.04008 dB; known/unseen54.31272/54.00872 dB; ADC maximum55.52 DN16; real fine detail remains soft |
| Slightly higher single-view photo mean | **[V117 Tiny](v117-v118-quality.md)**: photo37.04408 dB; known/unseen54.27303/53.97339 dB; higher ADC maximum63.89 DN16 |
| Tiny alternative / lower tested ADC maximum | **[V114 Tiny](v114-v115-quality.md)**: photo36.97973 dB; known/unseen54.28627/54.00290 dB; ADC mean/maximum7.08/51.73 DN16 |
| Slightly higher known-camera mean | **V115 fitted Small**: photo36.97700 dB; known/unseen54.32405/54.00417 dB; ADC maximum65.64 DN16. Its transfer initializer changes along with encoder size |
| Optional eight-view inference | [V114 fixed 24 pilot](v114-eight-view.md) improves all 12 material cases and two selected adverse camera crops, with a selected color-bias tradeoff. Full panels/frame remain unmeasured; eight evaluations per tile |
| Optional ADC observed-sample fidelity | [V114 sites export](adc-consistency.md) improves427-source ADC photo PSNR37.78013→38.01575 dB and worst color bias51.73→37.82 DN16, with higher flat-field spatial RMS. Positive-noise profiles bypass it |

These finite comparisons do not establish a universal ranking. Tiny/Small
weak natural-detail response is nearly unchanged on the same 427-source support;
encoder size alone does not resolve it. [Full local diagnosis](local-material-detail.md).
The [fixed V115/V117 output mean](fixed-tiny-small-mean.md) gives an intermediate
tradeoff without a clear visible GFX improvement.

## Run the current model

[Inference, hot-pixel repair and linear DNG/JPEG usage](usage.md) reads the
[explicit current selector](../configs/current-model.json).
V120's checkpoint is `/mnt/external/demosaic/models/v120-final20000.pt`, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.

Available alternatives retain exact identities:

| Checkpoint | SHA256 |
| --- | --- |
| `/mnt/external/demosaic/models/v117-final20000.pt` |`f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0` |
| `/mnt/external/demosaic/models/v114-final20000.pt` |`2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2` |

[Endpoint aliases](results/v120-v121-endpoint-aliases-v1.json) and the
[V120 selection receipt](results/current-model-v120-selection-v1.json) preserve
the original checkpoint and prior selector evidence. New experimental data do
not silently change an existing run's parent, schedule or input snapshots.

## Quality and remaining work

The current [training pipeline](training-pipeline.md) uses native 256/B16,
geometry before final area reduction and zero optical PSF augmentation.
The newest prepared dataset has 90,773 photos/37 reviewed regions. The
[latest source inspection](v125-v131-source-review-5600-9800.md) withholds one
grainy coastal source and adds mixed leaf detail while preserving all 36 prior
region objects. V134/V135 retain their 33-region bank; active and queued
comparisons keep declared cohorts. A
[full source-schedule audit](training-source-schedule-coverage.md) distinguishes
corpus size from the identities actually selected in 20k planned updates.
The optional [photographic epoch order](photographic-epoch-order.md) achieves
full source visitation on the prepared set at that budget; trained quality
under this new ordering remains unmeasured.

| Quality question | Current evidence and action |
| --- | --- |
| Persistent detail bias | [V12420k native check](v124-final20000-native.md) gives ordinary+.0095dB/faint−.0856dB versus V120; faint spatial MSE is only0.39% higher after late recovery from14k. Real mesh remains weak. [V1256k](v125-progress6000-quality.md) is still1.009dB below V120 on faint contexts. Limited and unequal-budget supports; original matched full endpoint/bias review remains pending |
| Spatial RAW detail | [V131/V132](raw-spatial-training.md) tests a22,664-parameter branch on90781/29. [V131 control at1k](v131-progress1000-quality.md) gives ordinary+.0016dB, deepest shadows−.0237–.0342dB and faint ADC−.2734dB versus V120, with mixed local detail and no clear mesh recovery. V131 stopped at step14,549; V132 production/full endpoints remain unmeasured |
| Global RAW repetition | [Completed V1361k](v136-global-attention-quality.md) adds18,272 parameters for two-pass global attention. Against matched V129: ordinary+.0003dB, shadows+.0007–.0026dB, faint ADC+.0131dB; local gains/errors are mixed and real mesh remains weak. Full native comparison and independent audits published |
| Conditioning global matching | [Completed V1371k](v137-global-conditioned-quality.md) gives faint ADC+.0334dB over V136, tiny ordinary/shadow regressions and weak real mesh. A [trained-memory ablation](global-memory-contribution.md) finds only0.83–1.39% feature-offset change on six contexts despite varied attention; it does not measure final RGB influence |
| Adapting only the global branch | [Completed V1381k](v138-quality.md) freezes all 91 parent model/EMA tensors and trains 18 branch tensors at LR1e−3. Faint ADC +.00406 dB and noisy-flat spatial RMS −.15% versus V120; no clear new mesh recovery. All 150 inputs/audits/native views complete |
| Removing the global branch's local bypass | [V139](raw-global-memory-only.md) retains15 memory-path tensors with the V120 parent frozen. CPU/CUDA16+2 checks pass; original1k remains unstarted after the original dependency failure. V138 recovery does not launch it; quality remains unmeasured |
| Separate gradient-error smoothing | [V141](v141-gradient-epsilon-pilot.md) changes only gradient epsilon3e−4→3e−5: faint ADC+.01528dB versus V129, mixed local detail and no new mesh recovery; noisy-flat coarse error near V129 and5.75% above V120. Default remains inherited pixel epsilon |
| Crossed-line and empty training targets | [Completed V142](v142-crossed-line-pilot.md): faint ADC+.05212dB and noisy-flat spatial RMS−4.55% over V129, with selected weak grass/wood gains. Coarse noisy error stays5.08% above V120; ADC-only DC bias worsens. Useful further-training data, no new mesh recovery |
| Comparing neighboring gradients before memory | [V140](raw-patch-memory.md) adds2,048 zero-initialized descriptor parameters. Standalone1k/102-input native/faint/GFX and48-flat reviews complete: ordinary+.00003dB/faint−.00015dB over V120, no clear mesh recovery, near-parent flat/sky variation |
| Photographic variety at fixed budget | [V133](reviewed-quota-training.md) lowers V131's reviewed quota from50% to5% with the same parent/data/20k horizon. CPU/CUDA16+2 checks pass; original production/review dependency queues exited; trained quality remains unmeasured |
| Cleaned corpus and source visitation | [V134/V135](photo-epoch-training.md) compares replacement/epoch ordering on identical90,778/33 data. All four CPU/CUDA16+2 checks pass; original20k production/full-review dependency queues exited; trained quality remains unmeasured |
| RAW frequency features | [Completed V122/V12320k trial](v122-v123-quality.md): joint-arm photo gain+.05493 dB over adapter-only, with lower unseen-camera mean, ADC maximum4190.02 DN16 and little weak natural-detail or real-mesh recovery |
| Larger Fourier window and more mesh exposure | [V146 at 500 updates](v146-coherent-frequency.md): frozen V143 parent, native256 Fourier support and 1,246 present/1,183 empty training meshes. Raw/EMA response+.62%/+.44%, but mesh/photo errors rise and native detail remains missing. [Matched inference-window transfer](v146-window-transfer.md) to native512 support also gives no useful gain, with 72 actual512 flats and 32 native figures. No replacement for V143/detail |
| Direct late RAW innovation | [Completed V1471k](late-spectral-detail.md): mesh response−8%, noisy-flat error+.24–.34%, no clear new real mesh or organic detail. Strong-edge whole-scene RMS improves .31–.42% while quiet patches worsen. All 64 native figures/audits complete. Removing local support exposes a worse frequency proposal; the component remains for research |
| Bounded complex CFA mixing after parent | [Completed matched V1481k](phase-matrix-detail.md): scalar control exactly reproduces V147; matrix response falls8–9% against V143, with higher photo-band and native512 flat errors. Small strong-edge/full256-flat gains coexist with worse quiet patches and missing native green-mesh/feather detail. All four endpoints,58 figures and audits complete; research component, no improved model recommendation |
| Spectral capacity and local flat safety | [Target-informed diagnostic](spectral-capacity-oracle.md): bounded per-bin matrices can express much stronger detail with GT, but full support can invent a quiet-region lattice beside stripes. Oracle outputs are unavailable at inference; they relax shared-network coupling. Compare actual blank/DC/spatial error alongside correction energy, which can also represent beneficial denoising |
| Known CFA phase and green coherence | [Completed matched V1491k](coherent-phase-estimator.md): alignment modestly improves the native control, but both new arms retain6–7% less mesh response than V143, with no useful new cab-mesh/photo texture. Strong-edge whole RMS gains .45–.74% coexist with worse quiet regions and native512 noisy flats. Tiny dark-photo/native256-flat gains do not restore weak bands. All6 endpoints/66 native figures/audits complete; research components remain available, with no inference integration |
| Training-loss noise scale | [Completed V150](objective-floor-training.md) tests the [diagnosed ADC pressure](spectral-loss-allocation.md): 16 DN reduces ADC clipping35→4, noisy512 flat RMS .045–.047% versus V143 and ADC photo RMS about3.06% on two held-out sources. Mesh response still falls4.3–4.5%; no useful new real wires/noisy organic texture, with quiet/coarse-slope regressions. All4 endpoints/822 cases/72 actual native views/audits complete; native control's trace/weights/Adam/all1596 retained predictions are exact. Use16 DN for the next noisy-head training comparison while retaining2 DN's stronger ADC band/coarse-flat results. No inference integration |
| ADC isolation and noisy peak emphasis | [Completed matched V151](noisy-objective-training.md): noisy-only raises mesh response 3.76–7.22% over V143 and lowers native512 noisy-flat RMS .10–.16%. Absolute response is only 2.28–2.36% of exact GT; quiet errors still rise and real wires/natural texture stay missing. Most ADC photo gains are lost. Peak8 nearly closes support, without useful noisy recovery. All six endpoints/822 cases/84 native views/audits complete; all 1,644 control predictions reproduce V150 exactly. Use noisy-only/16 DN/no peak bonus as the next noisy-head training control; retain V150's ADC strengths. No inference integration |
| Relative phase between RAW and residual | [Completed V152](relative-phase-estimator.md): cross-spectrum inputs raise mesh response 1.27–1.41% over V151 noisy-only and modestly lower noisy-flat error. Response remains 2.31–2.39% of GT; quiet RMS worsens .334–.834% over V143 and natural-band response falls further. No convincing new real wires/organic texture. All four endpoints / 822 cases / 72 native views/audits complete; all 1,644 control arrays reproduce V151 exactly. Keep the new input feature for estimator/support prototypes and V151 as the quieter control; V150 retains stronger ADC photo results. No inference integration |
| Fixed proposal/support diagnosis | [Completed V152 crossover](support-crossover.md): most added quiet MSE follows the relative proposal under fixed original maps. Full support raises response to2.56–2.60% of GT, with worse actual blank/quiet errors and no new convincing real crossings. All six compositions/822 cases/84 native views, independent metric/reconstruction/risk audits and1,644 exact original replays complete. Crosses are two-head diagnostics, not new checkpoints. Test delivered-output spectral supervision next; general inference choices remain V120 and explicit V143 periodic detail |
| Loss or shadow reweighting | [V117/V118](v117-v118-quality.md), [V126/V127](reviewed-shadow-pilot-quality.md) and [V128](v128-feature-pilot-quality.md) find no useful broad weak-detail gain from their tested band, shadow or DINO feature additions. These terms stay off by default |
| More reviewed sources / training precision | [V129](reviewed-detail-training-pilot.md) and [V130](training-precision-pilot.md) show small mixed1k changes without clear noisy/GFX recovery. FP32 improves selected [faint-ADC bands](faint-adc-precision.md), with global PSNR−.01720 dB and subtle native changes |

The [main DSCF3879/3880 gallery](gfx-qualitative.md) includes foliage, fence,
building and sky. The additional [DSCF3842/DSCF3835 fine green mesh](gfx-green-mesh.md)
remains an adverse case under both fixed profiles. ISO100/AHD and camera JPEG
references differ in aperture, exposure time and moving subjects; they are
qualitative references, not exact GT. Both pairs and siblings remain held out.
The [Q2/Sony/GFX50R comparisons](cross-camera-qualitative.md) likewise retain
soft dark rocks/window edges and small differences among recent versions.

The [11-capture binned-reference comparison](native-camera-development.md#v120v121-extension)
finds much finer texture than RawNIND and V120's+3.69903 dB high-noise camera-RGB
gain under added noise. Residual source noise and that limited development
support do not establish broad real high-ISO superiority: stronger released
RawNIND still wins four of nine measured camera scene means. State-of-the-art
quality remains unproven. [Requirements and remaining evidence](requirements.md).

Complete101.996MP FP32 outputs and 16-bit exports are verified. Ordered Tiny/Small
inference/blending observations are 116.57/101.66s; differing warmup/workspace
states prevent a speed ranking. The 100MP/10s target remains open. Hot-pixel
repair and [linear DNG/JPEG export](dng-export.md) are merged; repair was off in
these comparisons. Quality precedes speed optimization.

[PSNR history](performance-history.md) contains56 completed primary endpoints.
Earlier implementation decisions and the exact previous version of this page
are preserved in the [local-time diary](../diary/2026-10-27-08-52-27-source-schedule-coverage.md).
Original study reports, checkpoints and machine receipts remain intact.
