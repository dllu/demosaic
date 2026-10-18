# Inspect 40k camera progress at identical native pixels

Previous goal turn made progress: the real-GFX conditioning study and six native
images were committed/pushed in8654ba5; the completed matched40k training audit
and successful quality-review handoff were published in4bedea5. Current exact
checks confirm review controller1784241 and full427 child2099149/1792285394.04
live, with86,058/111,636 rows at the last check. Compilation/grid controllers
remain waiting. The original CPU diagnostic is live and yielded at116 updates.

Completed a read-only interim analysis of the finished known/unseen camera
panels while full427 continues. Compared each40k model with its own original8k
checkpoint on the same9 measured-reference scenes (four known/five unseen),
eight/ten captures and nine prepared crops per capture. Input/protocol metadata,
all486 classical-control case metric records and all selected noisy/reference
PNG pixels match exactly across endpoints. Checkpoint ancestry matches the
frozen original parents and completed40k boundary.

Independent math.fsum reductions reproduce every per-capture and scene-balanced
summary metric within7.105427357601002e-15. Measured-CFA PSNR point means:

| Model | Known | Unseen |
| --- | ---: | ---: |
| No-DINO8k | 44.1825 | 41.4379 |
| No-DINO40k | 48.2818 | 46.1458 |
| DINO8k | 44.3533 | 41.6402 |
| DINO40k | 48.3667 | 46.0103 |
| Wiener7+Malvar | 50.0717 | 49.5913 |
| V43 | 54.2333 | 53.8061 |
| V63 | 54.2037 | 53.8430 |

Own8k-to40k gains are+4.0992/+4.7079dB without DINO and+4.0134/+4.3701dB
with DINO. The actual longer run therefore does learn; the earlier weak8k
scores and small repeated-training diagnostics do not prove the architecture
cannot learn. Nevertheless both endpoints still trail the simple Wiener
comparator and mature controls. The DINO gap changes sign across panels:
+0.0849dB known,−0.1355dB unseen. This supplies no consistent context benefit,
convergence, complete generalization or quality promotion. Full/statistical
and source-sensitivity results remain pending.

Assembled and viewed every previously selected camera ROI in four1688x192 native
grids:2pilesofplates,7D-1,LucieB_3apples,LucieB_Coulicoco. Columns contain noisy,
both8k/40k arms, V43/V63, both RawNIND adapters and the AHD reference. Every
panel is160x160 with no resampling. Noise clearly decreases at40k, but substantial
grain remains, especially in flat/dark regions. Also viewed two compact512x192
40k noisy/restored/reference triplets. Source/ROI, checkpoint hashes, supplied
shot/read, common exposure1/WB/matrix and per-method receipts accompany them.
Registered low-ISO RAW retains noise/alignment uncertainty; AHD RGB is not exact
GT. Derived images carry RawNIND attribution and CC BY-SA4.0 licensing.

The retained auditor, original input-report refs, source crop receipts and
rendered grids are at
`/mnt/external/demosaic/benchmarks/packed-isotropic-quarter-camera-progress-v1/`.
The public interim report/JSON and six unchanged PNG copies are under docs;
all image hashes and report links verify, as does git diff --check. No model
forward, GPU work, training changes, tests or changes to frozen artifacts are
introduced. The existing full-review queue continues independently.

This advances native inspection and documents partial measured progress without
replacing the required complete review. No promotion, schedule extension or
protected-final scoring; SOTA, decisive real-photo superiority and100MP/10s
remain unmet/unproven.
