# Input-adapter gate reviewed; unchanged control replay next

V56 finishes its first 1,000 updates and all evaluation; controller59217 exits.
Candidate SHA c5ef701593bdfe98f9c3e43537fb9d6fea64f6f7b3c982e14bdcd3b5fa649218.
All41 logged input hashes match immutable V54 step1000; final Python/Torch/CUDA
RNG states also match. Learned input weights are finite/nonzero (EMA head norm
.0160603). These facts do not establish identical floating-point optimization.

V56−V54 known primary −.070233 dB [−.113987,−.041735], unseen +.020123
[−.042450,+.075682], natural photo −.125789 [−.179239,−.086208], procedural
−.349372 [−.704129,−.066103]. Photo SSIM declines .00080317; procedural SSIM
increases .00073179. Intervals describe source variation, not training-seed
uncertainty. All86,828 full-suite method cases complete;62,020 classical/RawNIND
and12,404 V54 neural cases replay their original metrics exactly.

Actual analytic GPU evaluation finishes1,344 method cases. At level.18,
contrast.02/high-noise prior, period4/8/16 signed gain changes
.003321/.012818/.354515 → .002225/.016778/.312214. Mixed response without
general improvement. Flat RGB bias/RMSE/band noise falls, but spatial luma RMS
at.18 rises .00052062→.00053928. No blanket noise-gain claim. All448 CPU
Malvar analytic cases replay exactly; V54 neural analytic FP16 is not bit exact
across runs, max RGB-RMSE metric change6.81e-7/carrier gain.0002345, cause
unisolated. Newly recomputed controls are used and strict replay is not claimed.

Visually inspected36 native PNGs: V54/V56/channel-RawNIND on ten standard
subjects, plus six neural analytic examples. Fabric strands remain largely
lost; foliage waxy, building detail soft; V56 does not visibly strengthen fence
wires. RawNIND retains a colored grid. Weak carriers remain attenuated; flat
8-bit previews do not exclude small errors. All46 PNGs verify SHA/geometry/
metadata/shared noisy/reference pixels. Eight full RGB16 files verify SHA,
size/dtype/tags/sampled codes/ICC. GFX control/input-adapter timings33.48/33.73s are
single shared-machine observations, not a speed result. ISO100 remains an
independent optical/time reference, never exact GT.

Decision: stop V56 at this first gate, keep the adapter default-off and V43
step2000 README reference. Preserve complete1000 state on its original4000
schedule. No convergence or universal input-adapter failure follows. Published
docs/dino-input-v56-review.md and full machine receipt, with46 native triplets.
Source remains4bf85a2;483-test CUDA-enabled suite and genuine preflight passed.

Next is V57: exact historical V54 sourceb62c996, same V43 EMA/fresh AdamW/EMA/
seed52/B16/LR/schedule/data/model/noise, changing only run/notes. This checks
procedural repeatability before causal claims about small trial differences;
it is not a new seed or a variance estimate. Actual old source/config/parent
identities are verified. Evaluation-only scripts are separately pinned; all41
logged observations must match and full native/numerical reviews follow.
No duplicate GPU work starts before actual V56 exit and published review.

Actual V57 launch after V56 terminal success/owner exit and report commitfbe5a24:
controller91971 created1792167974.54 in the original b62c996 worktree. First
input hash matches V54 exactly, first loss differs−1.80e-6 (cause unisolated).
The live launch receipt records observed progress and matching logged batches;
full review remains pending. V56 review JSON SHA b6599e7b… is pinned by this
controller and must remain unchanged while it runs. This replay is a new run;
no historical checkpoints or schedules are restarted or overwritten.

Original fresh no-context/S/B3000 snapshots and original10000 schedules remain
intact, with complete optimizer/RNG/source audits. Their continuation driver is
prepared but not launched while this check takes priority. The QI downloader
remains separate; incoming data does not change frozen training membership.
Other users' GPU work remains untouched. Goal remains active: broad SOTA/real
superiority, protected-final assessment and100MP/10s are still unproven.
