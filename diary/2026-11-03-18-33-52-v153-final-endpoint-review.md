# V153 final endpoint review and recovery

Recorded: 2026-11-03T18:33:52-08:00 (America/Los_Angeles).

Completed review: 2026-11-03T18:49:26-08:00 (America/Los_Angeles).

This goal turn progressed from the original live V153 worker at step370 through
all1,000 updates, six endpoint collections, independent state/metric audits and
actual viewing of84 native figures. No training was restarted. The requested
fine dark-detail and clean-sky outcome remains unproven: new real cab crossings
and noisy organic texture are still missing. The broad goal stays active.

[Completed V153 comparison](../docs/delivered-spectral-objective.md) keeps all
33,713 parameters /13 tensors and86 neural source files identical across three
fresh heads. Only spectral supervision changes: pre-support CFA coefficients,
delivered mosaic error, or all-RGB error packed into12 spatial phases. The same
4,000 old observations/parents, noisy-only routing,16 DN floor, .25 coefficient,
geometry, initialization, schedule and clipping apply. RGB repeats RAW scales as
training proxies, not calibrated RGB covariance. Targets stay training/scoring/
display-only, never forward inputs.

Delivered loss raises mesh response6.04–7.97% over matched V152-relative control,
11.43–17.40% over V143, but reaches only2.45–2.59% of exact constructed GT.
Whole mesh RMS improves .411–.508% over V143. Actual present-mesh blank RMS
rises .014–.114% above V143 and all four delivered endpoints regress versus
matched controls. Native2302 remains nearly flat;2309 still lacks crossings.
The standing real sky/building stay close, foliage remains painterly, coarse
fence survives, and fine cab wires remain incomplete under both windows/priors.
ISO100/AHD/JPEG references remain qualitative, not exact GT, and unscored.

Noisy native512 flat RMS improves .096–.181% over V143, less than pre-control;
broad colored mottle remains. Quiet errors are mostly worse than control. RGB
EMA ISO6400 quiet RMS3.917796 slightly improves control3.920584, but remains
.486% above V143; ISO12800 worsens. All natural-photo groups lose band response
versus matched controls; exact feather/moth/grass/bark/bird texture stays soft.
ADC photo full RMS becomes .067–.129% worse than V143, losing the control's
.302–.324% gain. V150's roughly3.06% ADC restoration remains useful. Mosaic
slope block32 error improves .093–.192% below V143, replacing control's .719–.933%
regression, with slightly worse DC. All48 constant ADC cases retain parents
under all6 endpoints,288 exact arrays (checked by final publication verifier).

The proposal grows while support closes: mesh mean support is .326/.310 for
mosaic raw/EMA and .323/.303 for RGB, versus .479/.464 control. Coefficient RMS
roughly doubles. Present/absent support means remain nearly equal; larger
response is not evidence of spatial selectivity or calibrated confidence.
Retain delivered supervision as a stronger response prototype, with quieter
V151/V152 controls and V150 ADC strengths compared directly. General inference
choices stay V120 and explicit V143 periodic detail. The old V147 intervention
or study promotion gates do not erase these newer narrow gains or their costs.

All three heads finish882 supervised /118 zero-ADC-gradient batches, with all
1,000 AdamW/EMA clocks. No clipping occurs. The 27 focused objective/operator
tests and genuine8+2 CUDA checks remain passed. Final audit proves39 finite
Adam states and exact pre-control trace, raw/EMA weights and complete Adam state.
All1,644 control output arrays reproduce V152 relative phase exactly. Quality
collection performs4,932 actual head forwards with unchanged weights and RNG.
Peak allocated CUDA is4.15 GiB training /1.44 GiB review. Independent metrics
pass6,330 rows,54,246 scalar checks and656 Decimal reductions, maximum4.55e-13;
42 real rows remain unscored. PNG/display checks cover42,470,400 RGB channels.
All84 primary figures were actually viewed at original detail in21 unscaled
sheets, including36 repeated-cell triplets. Every crop cell remains160×160
native pixels with identical ROI/transforms and recorded conditioning/hashes.

The initial postprocessor finished the state audit but its reviewer failed at
an obsolete literal12-tensor assertion copied from the older native head. I
missed that assertion during adaptation. The V153 recipe and independent audit
correctly have13 tensors per head. The traceback occurs before review claim,
CUDA setup or any neural forward; there were no endpoint arrays to replace.
Ten exact failure-source/log/receipt copies are preserved. Revision2 validates
all actual final model/EMA/Adam counts and strict CPU loading before claim,
then performs the first endpoint collection. V1 files are never overwritten;
v2 has separate source/plan/log/status. The old controller overwrote its transient
failed-reviewer owner field, so that child's exact PID/create-time cannot be
recovered after exit. Its nonzero return/traceback proves completion, without
inventing a PID receipt. All12 retained owners are independently terminal.
The corrected controller retains failed-child metadata for future failures.

[Final evidence](../docs/results/v153-delivered-objective-final-v1.json) preserves
26 byte-exact final receipts plus10 preclaim artifacts, all84 PNGs and the
unchanged13 preparation receipts. Preparation's18 source texts and86 neural
hashes stay byte-exact; original bytes for two now-corrected mutable source paths
are preserved in the failure copies. The historical261-row active snapshot and
checkpoint250 audit stay unchanged. Total tracked head work is56 compatibility
+30 discarded smoke +3,000 production +4,932 quality =8,018 calls, excluding unit
tests. Failed preclaim and CPU strict-load validation add zero head forwards.
There are no new parent/DINO/noise calls, original lookups, RAW decodes or dataz
access. Personal media stays read-only; protected captures/JPEGs/siblings and
validation sources remain outside training. Resource reserves were respected.

README now shows two native V153 mosaic-raw mesh triplets, with actual blank/
quiet costs stated beside response gain. Detailed report, research/model and
experiment indices are current. Every improved endpoint has two fixed native
mesh triplets in the report. Next test a smooth robust delivered-RGB spectral
penalty to increase relative pressure on weak errors, preserving exact-flat
penalties and both real scenes. Keep MSE as matched control, verify finite zero
and complex/output gradients, and do not treat more correction or support as
quality by itself. This next hypothesis is not implemented or trained yet.
