# Packed learned-operator counts on CPU

Previous goal turn: progress through complete V72 known/unseen camera CPU
statistics and native review. This turn revalidates the live DINO/review owners
and checks a possible avoidable-work hypothesis without changing active code.

Camera metadata is constant over each input, occupying24/32 local-stem and
96/128 quarter-stem channels. Count actual completed V72no-DINO2k and
V70DINO40k graphs on fixed native256/B1 and native512/B4 inputs, CPUFP32,
2threads/nice10/CUDA hidden. Hooks observe actual Conv/Linear/LayerNorm calls;
hooked/unhooked RGB is bitwise equal and model/RNG unchanged in all four cases.
No training, input correction, new images or production feature is introduced.

Native256/B1 learned MACs:14,401,142,784 noDINO /20,630,126,592 DINO.
Native512/B4:230,418,284,544 /330,082,025,472. Constant metadata stem MACs
are7,247,757,312 at512/B4:3.145478%/2.195744% of the counted totals. Both
stems together are9,663,676,416 MACs. Independently derive the core count from
widths/areas/block counts/kernel sizes: all four core totals match exactly.
Core execution has270 Conv2d and104 LayerNorm calls. DINO adds its actual
context calls. No GPU time, traffic/peak-memory, quality or modified-operator
numerical guarantee follows from these nominal counts. Physical/elementwise
operators are excluded; output tensor bytes are not unique allocation traffic.

No metadata folding is adopted on this evidence. Actual trained GPU profiling
after the serial quality review is the next useful speed attribution step.
The current matched training/evaluation source and configs stay frozen.
Public record: `docs/packed-isotropic-operator-counts.md` and
`docs/results/packed-isotropic-operator-census-CPU-v1.json`.
Actual four-case result/source archive:
`/mnt/external/demosaic/benchmarks/packed-isotropic-operator-census-CPU-v1/`.
Ruff passes; real instrumented/uninstrumented forwards and independent core
formula checks pass. No mirror/toy tests or extra GPU work.

DINO remained live at1725optimizer/27,600examples in the latest inspection;
controller2339549, child2404322/1792295586.28, review2362748/1792295060.93.
Protected-final remains closed. SOTA, decisive real-photo superiority and
100MP/10s remain unproven/unmet; the broad goal stays active.
