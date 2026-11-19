# Close the scene-context review and compare redraw losses

Recorded: 2026-11-19T12:26:46-08:00 (America/Los_Angeles).


The 64-photo matched 50k monitor closed all 256 cases. On independent
ISO6400 draws, Local 50k reduced fine-increment error by 0.917 DN16
and fine-flat RMS by 0.419 DN16 versus Corpus 100k. Fine response
fell 0.763 points. On the faintest third, Spatial 50k gained 0.378
points when its distant context matched instead of being swapped.
Against Local 50k in that stratum it had slightly lower measured
response and 0.087 DN16 higher fine-flat RMS. Native exact views
were inspected and bound to the final matched checkpoint.
[Controlled review](../docs/scene-50000-controlled.md).

I isolated the band-limited difference between aligned and perturbed
spatial outputs and added it to the local arm. The original local
flat budget selects zero. A relaxed half-strength fit adds 0.013
natural response points on separate sources and loses 0.131 points of
weak-wire response. The sky stays smooth in the main GFX crop and
the finest cab crossings remain incomplete. Both standing
families and both cab profiles were inspected.
[Aligned-context transfer](../docs/aligned-context-delta.md) ·
[Main GFX reviews](../docs/gfx-qualitative.md) ·
[Fine cab reviews](../docs/gfx-green-mesh.md).

Both two-redraw continuations completed 512 updates and 3,072
native observations per arm. Interleaved training took 579.49 s.
Averaging the signed increment before the loss gave 3.07 and 3.31
more natural and wire response points relative to the same loss
applied per draw. Exact missing-direction error rose 0.357 DN16
inside gaps. On the 16-source independent redraw test, the mean
arm lowered the error shared by draws by 568.6 DN16² and added
1,001.7 DN16² of draw-sensitive variance. Individual-frame
fine-increment RMS rose 2.02 DN16. The native review included
both protected captures and the 16-bit exact anchors.
[Mean and individual redraw losses](../docs/local-redraw-average.md) ·
[Training audit](../docs/results/local-redraw-average-v1/training.json).

The new fixed camera panels are complete. The mean arm loses
0.03235 dB known and 0.04143 dB unseen CFA PSNR against the
individual-loss control. Both results are in the source-bound
history registry. The fixed 427-photo evaluation remains in
progress for these checkpoints and for the previous scene and
single-pair continuations.
[Redraw camera panels](../docs/local-redraw-average.md#fixed-camera-panels) ·
[PSNR history](../docs/performance-history.md).
