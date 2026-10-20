# Fixed late RGB / shared-trunk detail diagnosis

The [completed V90/V91 review](late-rgb-original4k-review.md) finds a tiny
positive matched photo effect but weak-detail failures and24 ADC draw/layout
losses. Both jointly trained checkpoints also changed their shared trunk.
This diagnosis separates immediate late-head effects from those adapted
trunk differences before choosing another training intervention.

Use genuine immutable V90/global4000, V91/spatial4000 and V63 original20k EMA.
No training, target input to the network, new checkpoint/export, default
change or promotion. A head-bypassed output is the intermediate prediction
of a jointly trained model, not a model trained without that head. Pooling
V91's frozen head is likewise an inference counterfactual, not a retrained
global arm.

One actual trunk/DINO forward supplies each headed model's normalized base,
decoder/physical inputs, frozen DINO fields and actual refined output.
Replay the identical physical inverse; require its complete output to match
the actual forward exactly. Direct head replay must also be exact. Reuse
those inputs for head bypass and pooled V91 prompts, with no extra common
trunk/DINO calls. Pooling an already-global V90 head must be an identity.
Retain the actual inputs for a later precision study without rerunning the
common networks. That possible study is not evidence of a precision bug.

Fixed data are the earlier native256 analytic generator, seed20261016,
WB[2,1,1.5], unchanged matrix, metric/crop ROI[48,48,160,160], four CFAs:

- All12 ADC-only carrier groups: means.01/.18, contrasts.02/.10,
  periods4/8/16. Verify all four old ADC draw labels give identical
  measurements; retain one unique draw/CFA,48 observations.
- Highest-noise carriers(.01,.10,8) and(.18,.02,16), plus a mean.18 flat,
  four original CPU-generated draws per CFA,48 observations. Shot.00256,
  read variance.0000262144. No new draw/condition selection after results.

All96 unique observations enter all six diagnostic methods: V63 full;
V90 full/bypass; V91 full/bypass/pooled. The complete frozen recipe and source
hashes precede execution. Engineering CPU uses only two64×80 subcontexts
per checkpoint and cannot supply quality conclusions. Require genuine CPU
full-output/capture/inverse/head parity, state/parameter/RNG checks and the
focused unit suite before CUDA.

GPU is IEEE FP32/channels-last with16GiB allocator cap. One extra unhooked
baseline per model verifies capture parity:75 common forwards total, rather
than rerunning the shared network for every diagnostic method. Require one
DINO invocation per common forward and none for reused variants. Preserve
all output arrays; selected complete B4 head-input captures retain actual
strides. Both states and all inputs/RNG must remain unchanged.

Only after viewing native comparisons interpret component gains. Fixed four
display cases are the two low-contrast4px ADC means and two noisy carriers,
RGGB/draw0. Dark cases use16× display exposure; bright cases1×. Every method,
noisy and exact analytic GT shares the same exposure/ROI; never resize pixels.
Other groups remain in the full scalar output. No real-photo improvement is
inferred from these artificial known horizontal signals.

Independently fit DC/cos/sin in NumPy FP64. Full V90/V91 metrics must replay
the prior closed analytic rows within1e−6 for dimensionless gain fields and
1e−8 for absolute RGB errors. Preserve all cases, including favorable ones.
Check the RGB and signed-gain identity
`F91−F90 = (B91−B90)+[(F91−B91)−(F90−B90)]` separately from nonlinear error
and RMS summaries. Report parent-relative adapted-base and late effects,
the frozen pooled-head contrast and flat behavior. Do not add RMS components
or use known-carrier GT for a deployable correction.

Wait for the exact prior owners' successful review/probe exits. Require48GiB
available RAM stable60s before CUDA,24GiB active floor, root64GiB/external
500GiB reserves,900s owned-worker bound, no automatic retry. Cache/source
RAFs are not needed and remain untouched. The complete project quality and
100MP/10s goals remain open.
