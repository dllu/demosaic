# Check both wires before a Bayer junction correction

Recorded: 2026-11-20T06:53:08-08:00 (America/Los_Angeles).

The [local junction report](../docs/local-junction-support.md) delivers
the measured difference-frequency term where both fundamental wires
have held Bayer evidence. The matched synthetic interaction and
additive roles share photon counts and read jitter. Exact gap masks
separate false delivery from changes to a continuing wire.

On 24 new sources, the locked fit gains 2.768 interaction points and
reduces junction increment RMS 1.121 DN16 versus masked internal phase.
At matched recovery added gap luma falls from 0.248 to 0.136 DN16.
Some additive controls still receive small corrections. Strong-only,
flat-core, edge-only and uniform controls reproduce the prior crop.

The opt-in `weak-junction-phase` fit matches the replay exactly on
336 synthetic and eight standing crops. Both [fine cab reviews](../docs/gfx-green-mesh.md)
show subtle changes mainly on the right, with uneven crossings and
mottle. The [main scene](../docs/gfx-qualitative.md) keeps a smooth sky
and connected coarse fence. Both exact-target triplets and all 12
camera boards were viewed.

The [gap tradeoff plot](../docs/assets/local-junction-support-v1/gap-versus-interaction.png)
covers a frozen crop component. The broad panels in the
[PSNR history](../docs/performance-history.md) fall outside this evaluation.
[Source and receipt bindings](../docs/results/local-junction-support-v1/publication.json).
