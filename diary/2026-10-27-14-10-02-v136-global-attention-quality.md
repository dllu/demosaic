# V136 global RAW attention quality

Recorded: 2026-10-27T14:10:02-07:00 (America/Los_Angeles).

V136 completes its full original1,000-update horizon. The new18,272-parameter
global RAW branch is the only recipe difference from saved V129: all1,000 clean
and noisy batch hashes match before candidate forwards. There are1,000 training
and64 validation root/DINO calls,16,000 target contexts and1,000 optimizer
updates, plus the already recorded36 discarded CPU/CUDA check/resume updates.
All109 model/EMA tensors and107 Adam states are finite at1,000; the endpoint
SHA256 is`71e2db399ad951b3f1d7f303e3d2dfc5e8b8e42e5c7bb5096c1aceaa102410c6`.
The [initial pilot entry](2026-10-27-13-30-04-raw-global-attention-pilot.md)
preserves the earlier setup and unmeasured state.

The dependent review completes exactly102 new root/DINO forwards, reusing all
V120/V129 predictions. CUDA peak is9,356,368,384 allocated bytes. No new noise,
RAW decoding, reference inference or review optimizer update occurs. The
independent audit recomputes288 metric rows/72 summaries/4,275 fields and all64
native PNGs,19,660,800 exact RGB channels; maximum PSNR difference is1.43e−14dB.

Against V129, arithmetic mean sRGB PSNR rises+.000292dB ordinary,
+.000697–.002648dB on the four shadow conditions and+.013065dB faint ADC.
This comprises four material contexts/all four CFAs, one observation per CFA,
not a new427-source benchmark. Compared with V120, ordinary/gain1/8 means rise
slightly while both deeper gain1/32 means and faint ADC fall.
Selected ordinary fur/wood gains rise over V129 with higher band errors;
grass loses response while its error falls. These are mixed detail changes.

The retained faint-detail supplement was frozen at training step650, before
the candidate's training endpoint or quality predictions existed. It fixes the
earlier original-source masks, shared40× contrast display and a per-channel
ROI-mean/centered-spatial MSE decomposition. The two new public analysis/audit
scripts use pure NumPy, with independently mirrored FFT, channelwise display
and long-double reductions. Four analytic tests pass. The first test's exact
floating equality saw1.0000000000000002; only its tolerance was corrected,
with the failed log retained. Existing controls then match on120 strata,
64 decompositions/496 scalar fields and2,457,600 exact display channels, without
candidate predictions or any model work.

The final supplement independently checks180 strata,96 decompositions and
1,536,000 exact PNG channels. Against V129, selected faint fur/wood gains rise
with worse relative errors, while grass improves slightly in both. Pooled sRGB
MSE barely changes1.99070374e−7→1.99048824e−7, while centered spatial MSE
increases1.88438478e−7→1.89603011e−7. The pooled ROI-mean error fraction falls
5.341%→4.745%. The per-observation mean PSNR gain therefore does not demonstrate
better spatial detail; no correction is fitted or applied.

Actually viewed all32 primary comparison boards, two exact synthetic-GT
triplets and four enhanced faint boards at native resolution. Larger bark
structure survives but fine hairs/grass/wood remain attenuated; deeper shadows
lose texture and retain color blotches. Main GFX foliage remains painterly,
larger fence/building geometry coherent and sky quiet. The corrected
DSCF3842/DSCF3835 extra mesh remains largely erased nominally; the nearby3879
profile leaves weak irregular diagonal texture without clear new correct
lattice recovery. The left blue point persists. Normal faint8-bit panels look
almost identical; enhanced panels show residual color texture without a broad
recovery. The other primary triplets are audited pixel subsets, not separately
claimed viewed.

Both cached DSCF3835 RAW/JPEG hashes match their configured identities and are
read-only. The main pair remains DSCF3879/3880. Both real ISO100/AHD references
and camera JPEGs differ in aperture/exposure time/moving subjects and are not
exact GT. Both pairs, JPEGs and siblings remain held out; no source-HDD reads
or original-file modifications occur.

The [quality report](../docs/v136-global-attention-quality.md) publishes26 exact
PNG copies,288 score rows,948 band rows,180 faint strata and96 decompositions,
with checkpoint/source/ROI/noise/exposure metadata and source credits. README,
current-model/research/training/index/experiment guides and both GFX galleries
now reflect measured quality. V120 remains the general recommendation on the
measured balance; the tiny gains are still documented directly.

No20k global run is queued. All18 branch tensors have nonzero gradients, but
retained memory-path maxima are tiny: latents1.07e−11/memory gain2.46e−14 versus
output projection1.89e−3. This is an optimization concern, not a causal
ablation or proof that global attention cannot help. All22 original controllers,
including V124/V125, retain their declared sources, budgets and schedules.
The primary history stays56 completed comparable endpoints. Full20k global,
full427/camera/color/frame quality, broad RawNIND superiority, state of the art
and100MP/10s remain unproven.

[Execution/quality receipt](../docs/results/v136-global-attention-quality-v1.json) ·
[Prospective supplement and initial-failure evidence](../docs/results/v136-faint-detail-predeclaration-v1.json) ·
[Final publication verification](../docs/results/v136-global-attention-publication-v2.json).
