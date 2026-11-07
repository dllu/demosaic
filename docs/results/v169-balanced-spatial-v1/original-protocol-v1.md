# V169 fixed spatial balance

V168 improved fine-wire response through finer crossed-carrier training, with
increased quiet and total-flat error. V169 tests a fixed inference change on its
existing raw/EMA weights: remove the broad part of the learned direct RGB
correction while retaining its fine component and the full spectral path.
Quality measurement and native review are in progress; no gain is claimed yet.

The direct RGB correction is replaced with its Gaussian complement, using
sigma8/radius24 **native pixels** and replicated boundaries. Numerical centering
on each channel's first pixel makes constant corrections exactly zero in FP32.
The parent image is not filtered. All 124,909 parameters and 47 persistent state
tensors load unchanged; the kernel is fixed, derived and nonpersistent. The
disabled mode reproduces the original outputs, auxiliaries and gradients.

This can remove useful coarse corrections, preserve pre-existing parent mottle,
or leave false detail at finer scales. It is not a flat detector or a guarantee
of accurate crossings. Spectral-only and direct-RGB-only outputs diagnose the
two branches. These are fixed-weight interventions, not models retrained with
the new path. Frequency/scale selection is a hypothesis from prior evidence;
the reused adaptive cohort does not establish blind generalization.

All 822 V168 cases are fixed, including absent and present mesh, natural faint
and dark photographs, mixed quiet fields, native512 flats and ADC controls.
Both raw/EMA endpoints run once per case: 1,644 neural root forwards. Their
original unbalanced outputs must replay the archived V168 predictions exactly.
No new parent/DINO, source, noise or training calls are required. The two GFX
scenes, both fine-cab noise priors and camera JPEGs stay excluded and use cached
inputs. ISO100/AHD/JPEG references remain qualitative, not exact GT.

All cases receive streamed metrics and prediction fingerprints. The 36 native
cases selected by V168 retain full new predictions and direct corrections;
this is deliberately not a complete new prediction archive. Independent NumPy
separable convolution checks every filtered correction pixel in process.
Original V168 metric scalars and per-case error decompositions are checked.
The fixed 48 boards and 24 triplets retain the same native160 coordinates,
exposure, contrast and conditioning. Crop pixels are never resized.

All 47 relevant CPU checks pass, including 19 new tests for the independent
filter oracle, constant annihilation, fine/coarse carriers, strict embedding,
initialization, RNG and gradients. Six CPU/CUDA filter value/gradient cases and
three FP32 autocast checks pass without a neural forward. Both actual V168
raw/EMA weight files load strictly on CPU. All 90 prior neural files are
unchanged. CUDA is capped at12GiB; minimum RAM/local/external headroom is
32/56/116GiB, with a .5GiB projection margin and .801GiB array projection.
Resource pressure waits before the next forward.

The first preparation stopped at an admission assertion without reporting its
resource values; the failing subcondition cannot be established retrospectively.
Its source is preserved. The second preparation records actual resources, but
its worker stopped at an unavailable SciPy import before a claim, CUDA setup or
any model forward. The current worker uses the independently tested NumPy
convolution and adopts the already completed CUDA filter check byte-exactly.
No scientific forward has been repeated by either correction.

[Current immutable preparation and complete sources](results/v169-spatial-balance-preparation-v2.json)
· [Original preparation](results/v169-spatial-balance-preparation-v1.json).
