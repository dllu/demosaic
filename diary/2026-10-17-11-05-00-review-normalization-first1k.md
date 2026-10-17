# First1k normalization review: small means, unresolved quality

Completed the shared-source V63-parent/V68-control/V69-augmentation evaluation:
75,396 primary cases,1,792 analytic cases,4,704 fresh hue predictions, three
full101.995852MP GFX outputs/six RGB16 TIFFs, other cameras and selected CPU
colors. All36 comparisons/nine witnesses,27 source sensitivities, case/group,
state/float/PNG/TIFF and supplementary source audits pass. Independently
reaggregated107,604 metric values/3,843 source means exactly;180 bootstrap fields
max1.39e−17. Protected-final scenes remain unscored.

Actually inspected all81 native originals. The first six-image GFX tool output
was truncated, excluded, and reopened in groups of three before counting.
All26 observation groups have identical noisy/reference pixels and shared
source/ROI/noise/display/WB/matrix metadata. Published all81 byte-identical
PNGs, six exact-photo triplets and GFX foliage/fence in the performance report.
The README keeps the representative V43 images and links this review.

Augmentation−control photo+.006206dB[+.003520,+.009201], procedural+.090593dB.
Photo sensitivity cohorts427/418/416 give+.006206/+.006217/+.006188dB. Hue
bias/RMSE improves16/18 groups, but bright neutral/saturated groups regress;
centered RMS regresses6/18. Both fine-tuned candidates reduce selected bright
carrier response versus the parent; dark carrier stays almost erased. Fabric
cords absent, real GFX detail soft, magenta coarse error remains. Neither model
promoted; V43 working reference. Individual full-frame times36.58/37.06/36.39s
are restoration-only shared-machine observations, not a speed comparison.

Preserved all failures: v1 wrong import before full427; v2 missing inference mode
at the hue library entry (no saved hue arrays); v3 recovery still selected the
v2 plan, rejected missing retained-file field before a stage. Corrected v4
retains completed panels/statistics byteexact and uses fresh hue output. Moved
inference-mode decorator from pure lineage helper to actual library entry;
new direct-entry regression plus existing tests:21 pass, Ruff/format pass.

Public review SHA256:
9d7bae9e61a8f9d32bf241c7645023ac19544e9e965cd06de5f014cfd18dedb0.
Native receipt SHA256:
f1089424b925a13436fea4c7c3181585f9baa391338a9f55a4fd1de62d8606e3.
Completed review owner609803/1792259892.36 exited. Historical first1k training
and current review status are immutable; no original files overwritten.

Explicit quality decision: complete original4k matched horizon from actual1k
model/EMA/Adam/RNG, unchanged data/seed/LR/source/policy, in separate run dirs
preserving first1k logs. No new training budget/corpus. Continuation not yet
launched at this diary capture. Need another full4k quality review. Full PROMPT
SOTA/decisive real-photo quality/100MP10s objectives remain unmet/unproven.
