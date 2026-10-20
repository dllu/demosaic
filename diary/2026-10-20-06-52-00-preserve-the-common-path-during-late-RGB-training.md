# Preserve the common path during late RGB training

The three requested pipeline changes are already implemented and measured:
4× linear binning followed by geometry/PSF then area2, selected-domain-only
loading, and repeated batch sweeps retaining B16. The complete427-photo matched
geometry comparison gained.50990dB; the current RGB B32 throughput gain was only
1.3% with roughly twice the allocation. These remain separate experiments from
the new training-scope intervention.

The completed component diagnosis is committed/pushed as31a302f. It finds that
the main V90/V91 ADC losses already occur before the late RGB head. This does
not identify the training cause or prove that freezing will help. The next
prospective [V92 protocol](../docs/late-rgb-head-only-v92.md) uses the same global
architecture and original4000 recipe as completed V90, with all91 common
restoration states and frozen DINO held at genuine V63 EMA. Only24 head
parameters train; common EMA states are explicitly left untouched. Clipping
now covers head gradients alone as a consequence of the changed training scope.

The opt-in `late_rgb_only` config is strictly boolean, rejects other head-only
modes and missing heads, retains the head20× LR group, and rejects scope changes
on resume before constructing the new backbone. Legacy modes retain the default
complete-state EMA implementation. The existing `lerp_` already leaves equal
frozen values equal; this is explicit scoped EMA behavior, not a demonstrated
rounding defect in the original implementation. No inference module changes.

All34 expanded late RGB tests pass in92.46s, including both prompt variants,
FP32/BF16 CPU, absent common backward inputs/gradients, all-state preservation,
selective versus legacy EMA and actual four-update interruption/restart. The
separate78-test training/execution/RAW-kernel/component regression passes in15.81s.
Its first collection attempt omitted `scripts` from `PYTHONPATH` and failed
before running tests; that failed JUnit remains preserved. The corrected command
sets `PYTHONPATH=src:scripts`; no test implementation changed in response.

The actual-source frozen CPU plan is
`/mnt/external/demosaic/experiments/late-rgb-head-only-v92-CPU16-v1/plan.json`,
SHA256 `34a330f07f9db158ce25e36b7fd4b3ac294bc3d51d3585cbdb91a2308fcfc923`.
Controller1229976/create1792504173.97 owns only its exact subprocesses. The
uninterrupted16 update stage has completed; first8 and a genuinely new8→16
process follow. These use actual V63/DINO weights and prepared mixed training
sources, retaining the original4000 LR horizon. These discarded updates do not
establish quality or speed. CUDA preflight and the full candidate require
completed, source-matched preceding certificates; no automatic retry, schedule
extension or promotion is allowed.

V90 is a fixed **historical exploratory reference**, chosen before this new
intervention but already observed when choosing V92. It must not be called a
new independent matched two-arm confirmation. Require original logged
observations/LRs/RNG and byte-identical inference sources, all existing quality
and native reviews, standing GFX qualitative crops and the unchanged eligibility
criteria. The README/working V43 stay fixed; SOTA, decisive real-photo superiority
and100MP/10s remain unmet/unproven.

Both genuine CPU and CUDA engineering studies now complete successfully. Each
runs16,8 and a separate-process8→16; full model/EMA/AdamW/best/RNG and all16
observation fingerprints match across restart, and original V90 observations,
LRs and final RNG match. States remain finite115/115/24, head output/prompts
learn, no common gradients are present, and actual DINO remains370a84c2….
CPU certificate SHA33f9d6eafd8a806c4757308dc02f67efd4034ffa026608c62daebb5508722ab5
is published with its plan. CUDA plan SHA
641f4f3f73d8f4acf1d9a7ba2bc7b78f315216ac1418e3bbc66ae5387d811d8c
freezes identical executed sources. An independent CPU-only byte auditor checks
all91 common model/EMA states at all six boundaries plus every final restart
state including signed-zero bits; receipt SHA
6a02d3730f86a709cc5635419ee6cd6dd3e4e44aee1da7442c9a1ccd5774b2a5.
The source audit finds exactly `train.py` different among47 actual model modules
relative to V90; all inference modules remain byte-identical.

Full original4000 V92 is separately frozen, SHA
93da7b7e5b8d0213bcd1580ffe709a53ebb801d8b125f6c9f3c8271cad950b46,
from a fresh V63 initialization. Prelaunch evidence SHA
d46abab92e62c9baa2f1c228490f197a3aa5ac7b941fd82a788b5afa25206de3
binds112 passing tests, both certificates, the independent audit and47 source
comparisons. Detached controller1265645/create1792504985.8 is launched with
the fixed resource limits, stable60s gate and no automatic retry/extension.
No discarded preflight state is reused as a training initialization. Full
training and full quality/native review remain pending. Published proof links
and operational paths are in the
[engineering report](../docs/late-rgb-head-only-engineering.md).

The full worker1265932/create1792505056.08 has actually started after the
headroom gate, with native/paired/Commons observations recorded. At the initial
operational check,62.89GiB RAM and505.64GiB external disk remain available.
No other project's process was changed. The full candidate has not completed
and receives no quality/promotion claim from startup checks.
All16 initial full-run observations now match original V90 source/forward/loss
fingerprints; the immutable startup receipt records both exact live owners and
first-forward parent parity. It explicitly records training/quality incomplete.
