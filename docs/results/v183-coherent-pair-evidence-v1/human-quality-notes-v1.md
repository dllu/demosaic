V183 recovers much of V181's lost weak-detail response while retaining some of
its quiet-field advantage over V180. The added coherent pair-response loss
raises mean mesh response **6.745% raw / 6.953% EMA versus V181**, reaching
**4.42281% / 4.43901% of exact constructed GT amplitude**. Response increases
on 238/256 raw and 237/256 EMA inputs. EMA remains **2.406% below V180**,
while quiet spatial RMS is **0.492% / 0.089% lower** at ISO6400/12800;
28/32 quiet inputs improve spatially against V180. This is a useful intermediate
recipe on the local-evidence architecture. Retain V180 for stronger response,
V181 for quieter spatial output and V172 as the balanced comparison. V120 Small
remains the broad photo/camera recommendation.

The detail gain has a measurable quiet-field cost versus V181. Quiet spatial
RMS rises **0.625% / 0.363% raw and 0.668% / 0.386% EMA** at ISO6400/12800;
all 32 quiet inputs worsen at each endpoint. Quiet total RMS rises
**0.509% / 0.340% raw and 0.538% / 0.357% EMA**, with 31/32 raw and 30/32 EMA
inputs worsening. EMA quiet DC RMS rises 0.147% / 0.194%. Against V180 EMA,
quiet total RMS changes **−0.427% / +0.0087%**; the higher-noise mean remains
mixed even though spatial RMS improves. The new recipe does not dominate
either predecessor, and stronger coherent response does not imply flat safety.

Present-mesh full RMS falls **0.340% raw / 0.352% EMA versus V181**, but
present blank RMS rises 0.0815% / 0.0812%. Blank spatial RMS rises 0.0907% /
0.0979%, worsening 242/256 raw and 241/256 EMA inputs; blank DC RMS falls
0.0464% / 0.1511%. Absent-mesh full RMS rises 0.0389% / 0.0350%, and absent
spatial RMS rises 0.0448% / 0.0483%. Signed absent-template gains remain near
zero, 0.00001412 raw / 0.00001744 EMA. No relative percentage is reported for
that near-zero quantity; it cannot certify absence of false texture.

Standalone512 full-flat RMS rises **0.0211% / 0.0365% raw and 0.0130% /
0.0221% EMA** versus V181. EMA spatial RMS rises 0.0498% / 0.0510%, while
coarse32 RMS changes +0.0019% / −0.0019%. Against V180 EMA, full-flat RMS
still falls 0.0648% / 0.0875%, with 39/48 inputs improving. The broad flat
error is unresolved; the small spatial changes are not removal of broad casts.

Natural photographic fine-band response rises versus V181 on all 128 inputs
at both endpoints. EMA retained faint/dark and organic faint/dark means rise
**0.261%, 0.155%, 0.312% and 0.150%**; raw rises 0.258%, 0.157%, 0.310%
and 0.153%. EMA relative band error changes **−0.0052%, −0.0018%, −0.0091%
and +0.0026%**. Three cohort means improve, while organic-dark error worsens.
These are small response gains, not established broad photographic superiority.

EMA mesh response exceeds V172 by **14.490%**, although only 100/256 inputs
increase and 156 decrease. Against V172, quiet total RMS rises 0.323% / 0.467%
and spatial RMS rises 0.609% / 0.670%. Full-flat RMS changes +0.0214% /
−0.0715%. Against global V178 EMA, mesh response rises 13.138%, but quiet
spatial RMS rises 0.557% / 0.696%. Keep earlier strengths visible: V173's quiet
spatial reduction, V171's standalone flats, V175 raw's modest quiet-total gain,
and V161's stronger learned mesh response at larger quiet costs.

All **60 actual native figures in 15 original-detail sheets** were inspected,
including 12 unresized noisy/restored/exact constructed-GT triplets. Mesh2302
remains almost uniform at normal contrast. Contrast40 reveals somewhat stronger
fine periodic modulation than V181, under broad colored error; a complete
lattice does not emerge. Mesh2309 retains mostly one strong orientation, with
the weaker crossing still missing. Both fine green cab windows remain soft
and incomplete under nominal and profile3879 conditioning. Subtle V181/V183
differences do not clearly recover new crossings beside the independent ISO100
and JPEG references. Main coarse chain-link strands survive. Building edges,
foliage, bird feathers, butterfly wing pattern and bark remain soft.

The main sky looks smooth at ordinary exposure4. Gray/color flats and quiet
regions beside vertical/slanted steps, narrow bars and stripe patches retain
broad green/purple mottle at contrast40. V183 adds slightly more fine structured
variation than V181 in several quiet views; the broad field remains dominant.
At normal contrast the fields look nearly smooth and step/bar/stripe boundaries
survive. ADC bark/fur and all four sloped ADC planes retain the exact frozen
output. These zero-noise identities do not establish noisy-sky safety.

Both protected GFX families remain in the comparison: DSCF3879 ISO6400 /
independent DSCF3880 ISO100 f/5.6 for sky, building, foliage and coarse fence;
DSCF3842 ISO6400 / independent DSCF3835 ISO100 f/5.6 and both camera JPEGs for
the fine cab fence. **ISO100/AHD and JPEG references are qualitative, not exact
GT**: aperture, exposure time, processing and moving subjects differ. No real
reference is scored pixelwise. Captures, JPEGs and siblings remain excluded
from training. Only cached arrays and parent outputs are used; originals and
unavailable `/mnt/dataz` remain untouched.

Mesh triplets retain source cases mesh2302/mesh2309, native ROI
`[176,176,160,160]` in 512px RGGB contexts, exposure8/contrast1, shot .00128
and read variance 6.5536e−6. Quiet triplets retain ROI `[80,176,160,160]`,
exposure8/contrast40 about camera RGB
`[.001500000013,.006000000052,.002666666871]`, with shot/read variance
.00128/6.5536e−6 or .00256/2.62144e−5. Fine cab crops retain context
`[600,6260,768,768]`, ROIs `[206,229,160,160]` / `[426,189,160,160]`, exposure16.
Every method uses identical coordinates and display transforms. Crop pixels
are never resized. Training checkpoint SHA256 is
`4d6d47cc14ef3effb9569d867c5aed59a1e09b315de6bbb82e61281e928b3962`.
Both strict CPU exports bind the checkpoint, raw/EMA state, exact source/class/
config and module hash. The viewer retains all eight earlier V178/V180/V181
checkpoint entries separately beside the two V183 endpoints.

The intended change from V181 is one added training loss: a per-pair bounded
coherent-response residual with a 1-DN16 energy floor, at 0.25 times domain
weight after the unchanged eight-term FP32 total. All 98 neural files, the
clean mask, domains, LR, EMA and sampler stay unchanged. Training adds
900 updates/3,600 noisy images across the same 1,000 cached rows with 100 ADC
skips, from the original V172 raw/Adam/EMA900 state plus a zero local adapter.
Network clocks finish at1,800 and adapter at900. Genuine row8 restoration resumes
at row9 with zero prefix replay. Independent audit verifies all900 nine-term
FP32 totals, masks, full trace and five strict raw/EMA/Adam/frozen/RNG checkpoints.
Peak training CUDA allocation is 6,787,514,368 bytes, about6.32GiB. The two
admission updates are separate probes and never initialize this trial.

The fixed review completes all822 cases at both endpoints:1,644 wrapper/frozen,
1,500 network/projection and7,500 sampler calls,1,644 exact frozen replays and
144 ADC identities. Independent quality audit verifies6,576 input fingerprints,
72 native RGB plus72 residual arrays,53,772,288 addition channels,582 native
metric scalars,278 Decimal means and750 exact input-only raw/EMA evidence pairs.
Geometry/finite-power checks do not independently recompute the spectrum or
calibrate confidence. No new parent/DINO, sensor/source draw or RAW decode runs.

All19 methods/15,618 metric rows, including both V175 endpoints, all four V178
endpoints and both V180/V181 endpoints, remain available. Two same-endpoint
primary loss contrasts plus30 contextual contrasts retain1,218 table cells,
2,591 independent Decimal means and12,870 paired checks. Earlier completed
outputs are reused; this is not bit-exact paired retraining. Sampler atomic
backward remains warn-only nondeterministic. The reused development suite has
no blind or seed-uncertainty estimate. V183 establishes a useful intermediate
recipe; missing real fence crossings and broad colored mottle keep the joint
goal open.
