# Fix the observed profiling hash failure and recover timing work

The first final10000 CUDA profiler failed before warmup/timing on a
channels-last1×1 weight: contiguous singleton dimensions retain last stride21,
which dtype byte reinterpretation rejects. This is observational hashing, not
model instability. Its downstream batch/compiled owners correctly refused work;
neither started training/compilation. Preserved all failed v1 files and owners.

Hash exact logical values through an explicitly copied canonical vector, keeping
original dtype/shape headers. Eleven targeted tests pass, including BF16/scalar/
noncontiguous buffers/negative zero. Real CPU preflight keeps prior model/DINO
hash245113... and reference file948530... exactly. An independent actual-model
NCHW/channels-last check reproduces14 old failures while the fixed hash agrees.
No numerical model/source/data/precision change or quality rerun is required.

Launched separate bounded v2 profiler and serial discarded RAW batch sweep after
checking actual failed owners exited and all old/new guards. Profiler completed
with genuine CUDA and exact outputs/state/RNG. Fixed GFX B4/native512 unhooked
median366.464ms; inclusive trunk180.088/RAWhead138.932/DINOcontext30.048ms, nested
coefficients30.831/backbone23.001ms. Trace reader independently maps all1209
device activities; trunk181.055ms summed activity includes92.617ms add/ReLU/copy.
Trace instrumentation and inclusive events have distinct scopes. No new100MP
speed claim; final quality review independently records52.704s.

Actual profile meets the predeclared compilation triage. A separate v2 follower
waits for actual batch-owner completion before bounded compilation. Existing
compiled CPU fixture/runner is unchanged; hash compatibility is separately
verified. Batch4/8/16/32/48/64×two remain the declared sweep; partial cases do not
select a production batch or change LR. Status/owner/source hashes and actual
result are in docs/results/raw-kernel-inference-profile-recovery-v2.json.
