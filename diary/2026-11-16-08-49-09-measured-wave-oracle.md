# Fixed measured-wave GT oracle reveals response headroom and error tradeoff

Recorded: 2026-11-16T08:49:09-08:00 (America/Los_Angeles).

The last goal turn completed authoritative progress: V13120k control quality and
the matched V1321k review were committed/pushed as326843b5/a7217253. This turn
revalidated V132's exact live worker224010/create1794843486.14 and endpoint
reviewer178183/create1794842394.64 before independent analysis. Training is not
signalled, restarted or relabeled complete.

The coverage/response join had found substantial attenuation even with a nearby
carrier. I tested the additional bank's physical synthesis with its exact
closed choices, retained inputs and saved V200 output. All64 far/400 views
are included:8 source geometries ×4 CFAs ×2 independent repeats ×3 roles.
The actual frozen physical-wave code matches the current tested code. Phase A
loads only packed/variance/colors and the saved anchor, never target arrays or
recipe geometry, then seals all64 CUDA-measured wave banks before GT access.
Exact field hashes match the prior closed diagnostics. No selector or neural
module is constructed/called; runtime monkeypatches forbid module creation/
forward. Peak CUDA375,446,016bytes,27.7455s, Torch RNG unchanged. The original
V132 job remains separate.

Phase B is explicitly a GT oracle: per role/color, fit constant per-carrier
gains against the full native512 camera-RGB target residual. Variants are real
bounded[-1,1], unbounded real and unbounded phase rotation. No scoring crop,
quiet mask, weak template or proximity subset chooses the coefficients. These
global gains are not the actual shared spatial head and do not bound its
capacity. SciPy1.18.1 is added to optional eval dependencies; only SciPy is
installed, with existing package versions retained. NumPy2.5.4. Fit completes
all1,728 solves in56.0248s, fresh NumPy/SciPy process, no Torch imported.

Learned complementary EMA weak response9.43358% → bounded oracle19.38517%;
strong86.88235% →88.25534%. Quiet RMS5.97884→5.95208DN16 and full
20.25961→20.20730DN16, but weak-increment RMS10.50479→10.59565DN16
(+0.86494%), orthogonal error+1.39297%. Weak response improves58/64; strong
response falls20/64 despite its higher mean. Full error improves every view.

Critically, quiet error worsens56/64 and weak-increment error46/64. Six of8
source means have higher quiet error. Median quiet change+0.02311DN16, range
−0.90729..+0.11982; source7 dominates mean quiet reductions. I revised the
chart to display these regression counts explicitly, preserving its first
render/source and all underlying receipts. The final native images are byte-
identical to the first render. Target access and lower aggregate error do not
resolve the detail/false-texture tradeoff.

Removing bounds leaves weak response essentially unchanged; phase-free gains
reach19.81857%, only+0.43340points.14/4,608 bounded scalar gains hit a limit;
real ranks1–8, phase-free2–16. Thus gain limits/phase freedom alone explain
little of this particular global fit's remaining loss, without proving a full
representation bound. The31-view/seven-source extra-bank-within1 subset has
learned6.2647% versus bounded21.4024%, phase-free22.1216%. It differs from
the older combined-bank48-view subset. Original1/3-bin thresholds are retained;
this descriptive grouping happens only after basis closure/fitting.

Seventeen focused tests compare actual FP32/FP64 readout synthesis, native CFA
offsets/conjugate/Nyquist cases, bounded fits against an independent full-design
solver, rank-deficient/zero carriers and phase relaxation. These CPU readout
test forwards are separate from the zero-forward diagnostic. Source identity
and executed/current fit AST agree; optional-eval dependency absence is handled
by skipping these analysis-specific tests in environments without SciPy.

Independent NumPy-only direct-offset synthesis checks all192 saved oracle
arrays/452,984,832RGB channels (max5.5511e−17), all1,728 fit gradients and576
box KKT conditions (max duality gap4.7365e−23 half-MSE). The shared established
metric routine recomputes4,160 fields exactly. The audit does not rerun solvers.
Eight native figures and both first/final charts were actually inspected.
Fixed source0/source1 far/RGGB/repeat0/native160 ROIs use exposure2/contrast1,
same WB/matrix and .00008/2.56e−8 shot/read,16bit/black.03. Two learned
noisy/complementary/exact-GT strips exactly preserve prior reviewed pixels;
oracle strips are separately labeled target-assisted. No resize or method-specific
display change. All views still show incomplete weak structure/crossings.

Published9 final PNGs, full manifests,24 byte-preserving receipt/source archives
and the frozen package/environment snapshot. Both protected GFX families remain
in the unchanged actual-model reports; their independent ISO100/AHD/JPEGs are
not used as oracle GT. V120 remains the recommendation. Next useful work is
input-derived localization/discrimination at matched quiet/increment error,
alongside the ongoing full-model attention training, rather than assuming a
larger scalar gain will recover faithful detail.

Final checks verify all24 archives and eight final native image copies against
their original bytes,382 local Markdown links, Ruff check/format for all four
current Python files and uv lock consistency. Existing locked package versions
are preserved; only optional SciPy is added. Publication-time inspection confirms
the same V132 worker still live at step3,425, with ample memory reserve.

[Report](../docs/measured-wave-oracle.md) ·
[Exact publication](../docs/results/measured-wave-oracle-v1/publication.json).

