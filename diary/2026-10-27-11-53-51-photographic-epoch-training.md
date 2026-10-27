# Cleaned-corpus photographic epoch training and review queues

Recorded: 2026-10-27T11:53:51-07:00 (America/Los_Angeles).

Prepared a controlled quality test of the new90778/33 data and optional ordinary
photo epochs. V134 is fresh V120-Small EMA replacement training; V135 changes
only ordinary-photo source ordering. Both seed70/native256/B16/BF16/singleview,
zeroPSF,.05reviewed,paired32/native128,LR1e-5/warm100/cosine20000. The parent is
fixed for this study, while current recommendations can advance on other
measured gains. V134 versus completed original V133 will measure the combined
three-exclusion/four-region change; V135 versus V134 isolates ordering.

All four actual CPU128/B1/FP32 and CUDA256/B16/BF16 checks passed16fresh+2valid
resumed updates inside the original20k horizon. Eight changed order-mode/hash
resume probes reject before construction.72root/encoder/optimizer operations,
612target slots;91model/EMA tensors,89Adam states withstep18. Official DINO
hash unchanged and no backbone gradients. CUDA peaks7041804800bytes. Preserve
allstep16 checkpoints,step18 finals,source snapshots,prepared tensors and logs.
CPU V135 matches13unaffected examples/1851626values; CUDA matches196examples/
112201160values, bothbeforecandidate model calls. Nine native/paired batches
per device are exact. No old model/control inference or training repeated.

Private training root:`.cache/current-quality-20261023-v1/photo-epoch-training-v1/run`.
Plan SHA256:e27a2ce3d339a5482521f58a4b20f53bdd4e6f3731e45f8b9fc90983b996aadb.
Controller2554551/create1793125992.0 is live, allfour checks adopted, production
waiting. It requires original V133 training and its automated endpoint/green-
mesh owner to complete andexit. Two fresh20k production budgets,640validation/
20640encoder calls perarm,progress1000 retained within horizon. CPU40GiB and
CUDA/production52GiB admission;16GiB CUDA cap,32GB runtimefloor,30min/check,
48h/production,8day dependency wait. No automatic retry/reset. The generic
controller adds an optional per-phase headroom mapping; old default behavior
and all existing frozen clones/plans remain unchanged.

Four new full endpoint queues are live: V134-V135-photo-epoch-quality-v1,
V134-V135-photo-epoch-independent-audit-v1,V134-V135-photo-epoch-comparisons-v1,
V134-V135-photo-epoch-green-mesh-v1. Planned9176new endpoint root/encoder calls
include4CPUmesh calls; none executed. Reuse existing V120/V117 numeric controls
and defer original V133 outputs. The V133/V134/V135 matched comparisons require
32px fullframe grids and all130actual tile-input fingerprints. Include complete
photo/camera/texture/color panels,102MPlinear/sRGB16,sixmainGFXROIs,highlights,
material exact syntheticGTtriplets,andboth extra mesh profiles with corrected
DSCF3835reference/JPEGs. Nine saved/deferred mesh predictions reused. No real
ISO100/AHD/JPEG reference called exactGT. The main3879/3880 scene stays held out.

Review setup history remains in
`.cache/current-quality-20261023-v1/V134-V135-full-review-setup-v1/`.
prepare-v1 createdthree queues, then stopped because the prior V133 plan
legitimately holds two completed inference receipts for each same input. No
mesh queue or neural work occurred. The v2 mesh-only continuation reused the
exact original template refs from the retained V133 setup receipt, then stopped
at an API assumption restricting deferred controls toV131. A new optional
explicit deferred-endpoint-arms argument preserves the oldV131 default and
binds this queue toV133. v3 created onlythe mesh queue, adoptingthe three already
live owners. Original scripts/logs,all checks and old jobs remain intact; no
inference,training prefix or observations repeated.

Independent NumPy audit checksall8step16/18model/EMA/Adam states,1052951336finite
values and exactAdam counters. The real18-step endpoints reject before neural
construction. All64quality/training source modules match;five inference helpers
and independent archive metric math remain byte-identical to originalV133
review. Eight additional clean validation reads match786432FP32values against
the frozen reader, with RNGunchanged and CUDAuninitialized. All four new review
owners arelive with empty completed stages/zero quality calls.148focused tests
passed4.25s; Ruff passes. Toy test training is separate from these model checks.

[Current trial documentation](../docs/photo-epoch-training.md) ·
[Actual check/plan/preflight receipt](../docs/results/photo-epoch-training-setup-v1.json).
README,current choices,source guide,pipeline,research and requirements now show
this pending quality test. Current V120 selector, completed PSNR history and all
old receipts remain intact. No production endpoint or quality gain is claimed;
PROMPT's broad quality/RawNIND/speed goals remain active.

Final publication verification passed2070 content bindings,25 frozen plans and
187local links, with22checked controller owners and the exact V124 worker live.
The61other core modules remain byte-identical to the earlier frozen V131 source.
New worker/controller/quality/mesh sources match their actual frozen clones.
`docs/results/photo-epoch-training-publication-v1.json` preserves the source,
owner and unchanged-selector evidence. V124's latest logged step is14050;
V134/V135 remain waiting with allfour checks complete and no production updates.
