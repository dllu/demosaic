# Distant frequency context: V161

V161 is training a matched architectural comparison from the stronger
[V160 paired-response baseline](paired-response.md). Quality remains pending.
V160 nearly doubled learned mesh response while adding false fine grain in
flat/quiet fields. This trial tests whether distant frequency evidence helps
the learned correction distinguish supported structure from noise.
[Immutable readiness and sources](results/v161-harmonic-context-preparation-v1.json).

The candidate adds one zero-initialized, bias-free projection to the existing
spatial/spectral hybrid: 6,720 parameters, bringing the total to 124,397 across
46 tensors. The control retains 117,677 parameters across 45 tensors. Both use
the same paired-response weight 1, ordinary/local/DC/spectral losses, cached
1,000 B4 observations, initialization of common tensors, LR/AdamW/global clipping
and EMA clocks. The architectural comparison includes more capacity and compute.

The old learned gain sees a local 3×3 frequency neighborhood. The new adapter
also receives 42 observed/innovation/relative-spectrum coordinates from twice
each frequency and all four half-frequency alias branches. Half-bin descriptor
coordinates use periodic linear interpolation, including neighbors across branch
boundaries. This interpolation operates on frequency descriptors; performance
crop pixels remain native. Existing matrix conjugate projection, norm bound,
observed-power factor, band, support and direct RGB path are retained. Targets,
pair labels and independent references never enter inference.

139 CPU checks pass, including 16 new coordinate/adjoint, boundary, nonzero
embedding, per-image independence and gradient checks. CUDA parity passes
28 archived contexts/56 head calls across all CFAs and native 256/384/512/768
contexts. A zero adapter exactly embeds the trained V160 head. Genuine 8+2
model/EMA/Adam/RNG restoration passes, with 91 finite Adam states and exact
V160 control traces. The immutable 40-row live training prefix matches V160.
Smoke peak allocated CUDA is 6.752 GiB under the 12 GiB quota.

Both heads start fresh for 1,000 updates. Final review covers raw and EMA
endpoints on all 822 cached observations: 3,288 actual head calls. The control
must reproduce V160's complete trace/raw/EMA/Adam states and all 1,644 actual
predictions before reusing its storage. All 1,644 new candidate outputs stay
external. No new parent/DINO forwards, source construction or sensor draws occur.

A prospectively fixed 12-case diagnostic evaluates both candidate endpoints
with the learned context active and zeroed: 48 further calls and 24 retained
off arrays. Active outputs must replay the main review exactly. This measures
the trained adapter's output contribution; it does not isolate all effects of
the changed training trajectory or establish improved accuracy.

The native design retains 48 boards and 24 noisy/restored/GT triplets, with
five older comparator columns. Both standing GFX scenes, both cab windows and
priors, sky, building, foliage, coarse fence and camera JPEGs remain included.
DSCF3879/3880 and DSCF3842/3835 references differ in aperture, exposure and moving
subjects; independent ISO100 views remain qualitative references, not exact GT.
All protected captures/JPEGs/siblings stay out of training; originals and
`/mnt/dataz` are unused.

The new study reserves 60/156 GiB local/external plus a 0.5 GiB projected margin.
It preserves all prior receipts and experiment arrays. All 87 prior neural
sources remain unchanged; one new module implements the context adapter.
Fixed training and review total 5,412 scientific head calls, including parity,
discarded smoke and context removal. Trained quality and actual native viewing
are still pending.
