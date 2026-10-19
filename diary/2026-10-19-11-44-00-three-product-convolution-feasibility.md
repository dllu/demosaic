# Genuine mature-model CPU precision proxy and offline Tensor Core convolution

Previous goal turn was progress: committed/pushed888443a admitted18 reviewed
public RAW sources into isolated future146/168 native manifests, with actual
loader/physics/CPU integration. Revalidated the live exact control/training,
review/closure/reference and archive-download owners at the start of this turn.
Full quality/speed requirements remain unmet/unproven; no completion claim.

Investigated a separate inference-only speed candidate while fixed original20k
V84/V85 training occupies the GPU. Local Torch2.14.1+cu130/Triton3.8.0 and official
Triton/NVIDIA documentation support checking three-product Tensor Core arithmetic.
Downloaded and hashed the pinned8KB compiler pass as reference. A CPU operand
proxy uses RNA TF32 high operands plus truncated residuals, retaining two cross
products and omitting low×low. CPU FP32 reductions differ from GPU MMA; it is
not a bitwise hardware emulator. Subnormal/nonfinite/overflow cases reject.

Both genuine V43/2000 and V63/20000 EMA models process the same two fixed native256
RGGB/ISO12800-prior observations.59 hidden dense convolutions are replaced
temporarily, retaining IEEE projections/physical/native-skip/context/transpose
paths. High-only operand proxies differ by7.02–9.03DN16; three-product proxies
stay below.06250 max/.00762RMS across all786,432 values. Independent full-array
NumPy FP64/math.fsum replay agrees. Repeats and original-after-context outputs
are bitwise exact; all model/DINO states, parameter identities, inputs, source
files and RNG remain unchanged. No GPU initialized or model training occurs.

Standalone channels-last implicit-GEMM Triton convolution supports the two
mature hidden geometries. Five actual CPU-interpreter cases verify indexing,
odd sizes, padding/stride/batches and channel/reduction tails against FP64.
All seven unique B4/native512 hidden shapes compile offline for SM121, with
TF32 MMA/RNA instructions and49,152B declared shared memory. No kernel loaded,
no runtime register query or device execution. The first direct-script import
failed before main; log remains, corrected fresh v2 completes. AOT/interpretation
do not establish real kernel accuracy, speed or memory behavior.

Prepared a frozen GPU check (47files/57inputs), but did not queue or launch it.
Its actual worker refuses the live exact training/review owners before CUDA or
output creation. Future execution requires successful original20k study/full
numerical review/CPU closure/reference boards and exact owner exits. Five
CPU-FP64-known operators precede both mature models on two photos and four GFX
contexts. Full RGB gates stay1DN16 max/.25RMS; failures stop before timing.
Only all6 model cases passing admits resident B4/native512 timing, with16GiB
quota and reversed policy order. No CLI/default/full-frame adoption follows.
20 focused tests pass in5.47s; Ruff passes.

Published two native160 triplets/model for the CPU proxies, with exact saved
GT/source/cache/ROI/checkpoint/noise/display records. Source-cache ROIs replay
and saved targets match; noisy/GT cells remain exact. Viewed the full8-triplet,
24-cell/12-unique-cell board at original resolution. Proxy/original appearance
is unchanged; missing fine canopy cords/folds remain. No quality gain or GPU
parity/timing claim. README keeps V43 and its representative crops.

The active control advanced to7700 at11:42:56UTC, about.894s/update/6.9GB CUDA.
The original matched study and review remain frozen; downloaded arrivals and
future native/Commons extensions stay out of both arms. No source HDD access,
private-photo publication, active-model/default change, automatic retry,
extension or promotion. The goal remains active.
