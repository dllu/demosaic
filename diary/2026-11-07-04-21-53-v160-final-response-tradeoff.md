# V160 paired response: stronger detail and noisy fields

Recorded: 2026-11-07T04:21:53-08:00 (America/Los_Angeles).

V160 completes both fresh 1k heads, all four raw/EMA endpoints and the fixed
822-case review. Pair supervision raises mesh response 81.75% raw / 95.73% EMA
over V143, to 4.00% / 4.31% of exact constructed target amplitude. Against its
matched ordinary heads, the increases are 84.62% / 94.77%. This is a useful
stronger learned-detail starting point than the retained V156–V159 heads.

The cost is explicit: blank RMS +3.25% / +4.69% versus V143, quiet mean
+8.46–11.36%, and native512 full flat RMS +1.48–2.83%. All32 quiet inputs worsen
against matched ordinary at both endpoints;31/32 worsen versus V143. Raw is
worse on47/48 standalone flats, EMA on all48. Coarse means can improve while
spatial/total error and false fine grain get worse.

The ordinary new-data control improves native512 flat full RMS0.42–0.53% versus
V143, with all48 full/coarse inputs improving at both endpoints. Quiet means
instead rise0.76–1.58%;18/32 raw and17/32 EMA inputs regress. Keep its useful
flat-field result beside V158's better quiet accuracy, V159's smaller quiet
cost and V157's stronger coarse gain. Ordinary changes the full data/noise
recipe versus these older studies; only the V160 matched pair-loss contrast
isolates its weight0 versus1.

I actually viewed all18 original-detail sheets covering72 figures/24 triplets,
all four endpoints and five retained comparator columns. Existing partial cab
strands gain slight contrast in places, especially under the nearby profile,
but crossings remain soft and far below independent ISO100 visibility. Broad
mottle persists, amplified flat/quiet crops gain fine colored grain, and natural
microtexture remains weak. Both standing GFX scenes, windows, priors and camera
JPEGs are included. References remain qualitative, not exact GT.

123 CPU checks pass across118 inherited/paired,3 counter and2 batch-isolation
cases. All450 frozen-base parameter-gradient comparisons pass. Genuine8+2
model/EMA/Adam/RNG restoration and first10 complete smoke/train rows match.
Four strict final loads and90 finite Adam states pass. Clipped supervised
batches are119/900 ordinary and142/900 paired; norms describe pressure, not a
separate causal attribution of each quality effect.

Independent scoring checks40,210 scalars and476 Decimal reductions, maximum
difference5.12e-13. Quiet decomposition checks480 scalars/160 per-case energy
identities. The native renderer independently checks50,764,800 RGB channels.
All30 real score rows remain unscored. Both endpoints and every regression
remain visible, including14,336 paired error entries versus retained models.

Actual scientific work:5,364 head calls,1,000 parent and1,000 internal DINO
batch calls. Those evaluate11,424 head images and4,000 parent/DINO images each.
The cache holds4,000 unique step frames from2,618 scene/patch instances;486 photo
pairs visit268 sources. There are234 reduced-contrast and245 reviewed-ROI photo
pairs. All18 held-out source IDs and protected capture/JPEG/sibling families
remain excluded. New review arrays total3,288/8.842GiB externally.

The original source24 counter failure remains preserved. Its procedural draw
was mistaken for sensor Gaussian noise. The explicit continuation adopted all23
completed parent batches and computed977 more; no successful parent forward or
full training run was repeated. The extra source construction remains counted:
4,004 frames and3,312 Poisson/1,928 Gaussian sensor API calls. All15 recorded
successful/failed owners are terminal. Executed cache prose still says990/adopt10;
its actual977/adopt23 fields, adoption manifest and execution ledger correct the
scope without changing frozen bytes.

An auxiliary report builder assumed uniform credit metadata and failed before
writing the document. The nested case was ADC credit metadata; its first failure
note mistakenly named organic metadata. Original source/failure and successful
revision2 are preserved. No scientific stage was repeated.

README now shows two paired-EMA mesh triplets and two quiet-field failure
triplets, with ordinary-flat and previous strengths retained by link. The model,
experiment and research guides describe the stronger response and its costs.
Original captures stay read-only; `/mnt/dataz` is unused. No experiment evidence
was deleted or moved.

[Final report](../docs/paired-response.md) ·
[Immutable final evidence](../docs/results/v160-paired-response-final-v1.json) ·
[Publication verification](../docs/results/v160-paired-response-publication-verification-v1.json).

The fine-detail/clean-field objective remains active. The next direction should
improve discrimination between supported structure and noise while preserving
the demonstrated response, rather than erasing this gain with another hinge
transition sweep. A possible architectural direction is richer context across
frequency bins: the current learned frequency gain sees a local3×3 neighborhood,
whereas reciprocal/harmonic evidence spans distant bins. This is a hypothesis,
not a launched experiment or measured gain.

