# V120 fine mesh review and saved-prediction adoption

Recorded: 2026-10-26T00:53:53-07:00 (America/Los_Angeles).

V120's original20,000-update checkpoint is already complete and independently
verified. Rather than wait for V121's full run before seeing its adverse mesh
behavior, evaluated the two existing fixed mesh profiles now, exactly once
each, with the original quality family's frozen model code. The corrected
reference is DSCF3835 ISO100 f/5.6/2.5s,46s earlier than DSCF3842 ISO6400;
the standing DSCF3879/3880 pair remains unchanged. Both references are
independent real exposures, never exact GT.

Checkpoint SHA256:
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
Used the saved `[600,6260,768,768]` observation and fixed local160px ROIs,
CPU IEEE FP32/B1/contiguous/two threads. The two actual root/encoder call counts
are1/1 per profile. Five V115/V119/RawNIND predictions were reused. No RAW was
decoded, observation regenerated, parameter fitted, optimizer updated or CUDA
initialized by this comparison. Saved FP32 predictions and complete method
receipts remain reusable.

Actually viewed both +2EV all-method boards, the two +4EV native matched
V115/V119/V120 boards and both noisy/V120/independent-reference triplets at
original resolution. **No clear V120 fine-lattice recovery gain appears at
either matched profile.** Nominal conditioning still largely erases the mesh;
the nearby profile reveals more diagonal texture, especially on the right,
but fine lattice remains soft, irregular and incomplete. The left blue point
persists. This supports a documented weakness, not an overall model ranking;
full primary/analytic/main-GFX/complete-frame evaluation remains pending.

Published both current V120 profile boards and two native triplets, plus direct
two-profile parent comparisons in `docs/images/v120-green-mesh-v1/`. Independent
NumPy64 display arithmetic checks2,150,400 native channel values:2,150,390 exact,
ten differing by one DN8 from FP32. Sixteen shared control cells and six triplet
cells are exact; original V120 PNGs are byte-identical copies. No panel pixels
were resized. Updated README, both GFX guides, endpoint/data-trial guides,
experiment index and training pipeline to reflect actual completion and review.

The first preparation source walk encountered old cached preview outputs inside
the idle queue workspace and stopped before any model loading/forward. Preserved
`prepare-v1.py`, its failure receipt and the immutable checkpoint snapshot;
`prepare-v2.py` copies only recorded frozen source entries. No failed inference
or optimizer work was retried and no executed source was edited.

Added completed-endpoint adoption to `scripts/queue_green_mesh_review.py`.
It checks exact input receipt/NPZ conditioning, original20000-update inference
and call accounting, prediction and immutable checkpoint bindings, and agreement
with the later final report checkpoint SHA. Paths may differ while bytes match.
Tests cover missing/duplicate/unknown endpoints, wrong profiles/inputs/steps,
counts and final checkpoint mismatch;34 pass and Ruff passes.

The actual frozen replacement's preflight forbids all neural Module calls and
model loading, reuses saved controls plus V120, and reproduces both +2EV boards,
both +4EV boards and both triplets byte-for-byte. A clearly marked nonexistent
V121 checkpoint placeholder tests scheduling only; it is never loaded or treated
as a completed endpoint. Wrong final V120 SHA is rejected.

After that proof, retired only the exact owned idle mesh controller
4131655/create1792995519.74 with SIGINT. It had no children, completed stages or
new prediction outputs. Preserved its frozen source, old preflight images,
plans, claim, terminal KeyboardInterrupt state and explicit retirement receipt.
Replacement owner59653/create1793001074.1 waits for the same original matched
report, adopts V120's two existing predictions and schedules only V121's two
new mesh forwards. This keeps the whole family at four rather than six calls.
The V122/V123 mesh queue and all training/quality/audit/report jobs are unchanged.

At recording, all11 owned active controllers retain their original identities.
V121 is training; V122 is still intentionally stopped under the live GPU-yield
coordinator and will resume the same worker. The broader quality/speed goals
remain open. No corpus membership, ROI bank or training recipe changed here.
Final publication checks resolve318 local Markdown targets and verify all62
unique artifact bindings in the new public receipt/manifest. Ruff formatting,
lint and `git diff --check` pass; these checks add no neural/RAW/noise work.

[Execution, actual viewing, pixel checks and queue adoption](../docs/results/v120-green-mesh-v1.json) ·
[Current native comparison](../docs/gfx-green-mesh.md#v120-after-correcting-the-paired-data-mix).

