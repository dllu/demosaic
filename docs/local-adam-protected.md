# Protecting flat and gap accuracy during a weak-detail AdamW update

The [regional training gradient audit](local-regional-wire-gradient-audit.md)
found that weak-detail supervision often opposed exact-flat and
absent-direction losses through shared weights. This follow-up
measures one finite update with the saved optimizer moments. The
fused-optimizer and projection checks are complete. The full collection
of 32 matched source pairs is running.
[Qualification and verified prefix](results/local-adam-protected-v1/launch.json) ·
[Frozen procedure and first eight pairs](results/local-adam-protected-v1/launch-evidence.tar.xz).

## Update comparison

Each replay starts from the raw regional 1,024-update checkpoint and
its AdamW state in
`bc633b61e30ac5bc708b7249c7885ca0c45591a2155882ba51ead94c97a6f445`.
The learning rate is the saved 7.5e−7. Training-side derivatives use
BF16 neural forwards and FP32 losses. The finite output comparison
uses IEEE FP32. All arms are evaluated before restoring the same raw
checkpoint for the next source.
[Parent checkpoint and native review](local-regional-wire-1024.md).

The shared step uses the original reconstruction, paired-band,
repeat, weak-absence and continuing-strand terms. The full step
adds the regional weak-response term. Both use the same saved
moments and clipping rule. Their parameter difference is the part
of the fused AdamW update attributable to weak-response supervision
for that step.

The protected variant projects that difference onto the set of
directions that have a nonpositive first-order change in the
update photo's exact-flat, weak-absence and strong-gap errors.
It makes the smallest Euclidean correction under those constraints.
The norm-matched control scales the original difference to approximately
the same realized size. Every variant preserves the shared step.
The evaluation measures both the rounded weight changes and the
finite loss on each photo.

There are 64 distinct approved source photos outside the earlier
continuation schedules and frozen comparison panels. Within each
pair, the update and separate evaluation photos share the nominal
noise regime, Bayer layout, coupling law and strong-continuation
status. Their backgrounds, wire geometry and sensor draws differ.
Neither protected GFX capture family enters the probe. The separate
photos measure transfer from a single update. They are held out of
the per-step gradients and projection.

## Verified implementation

The active-set calculation agrees with an independent constrained
solve on 240 problems, including repeated and opposed constraints.
In the first source pair, both shared and full functional replays
exactly reproduce PyTorch fused AdamW's 89 updated parameter
tensors, both moment tensors per parameter and optimizer clocks.
The first eight source pairs have finite post-update outputs.
Their largest norm mismatch is recorded relative to the full
increment in the receipt.

The prefix exhibits both directions of change on separate photos.
Compared with the norm-matched control, the protected step reduces
flat error on five of the first eight separate photos, increases it
on two and ties on one. The final analysis will use the complete
32-pair set across both noise regimes and gap types.
