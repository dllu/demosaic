# Training repeat stability at fixed correction strength

The [early repeat-training comparison](paired-repeat-stability.md#first-checkpoint-at-300-updates)
reduced independent-draw variance while weakening the correction.
A scaled control reproduced that gain at the same target-aligned
response. This study changes how the repeat term sees delivered
detail, so it can train changes in the correction's shape without
rewarding a uniform reduction in its strength. Ordinary image
and exact-flat losses still act on the actual delivered result.

## Matched training

Three heads use the same paired EMA initialization, frozen
Corpus 100k and two-window Bayer support from the
[original luminance study](paired-luminance-detail.md). The
matched control uses absolute, flat and paired-increment
supervision. The standard repeat head also penalizes
differences between complete physical redraws. The third
head uses the same repeat weight, 0.75, with two directions
removed from the repeat term.

For a source, the predicted present-minus-absent corrections
for both draws are treated as one vector. The two directions
come from the exact clean fine-band increment and the frozen
starting head's delivered correction. Together they define
a projection. The repeat loss uses the teacher's components
along these directions and the student's remaining components.
If the student simply scales the starting correction, the
projected repeat term remains the same. Every other loss uses
the delivered student output. The inference path still
uses one noisy frame and the fixed Bayer support.

Training covers 384 updates and 768 distinct ordinary
photos, with 4,608 observations per head. The photos are
disjoint from both preceding paired-head schedules and the
96-photo evaluation. Two complete redraws per source each
contain a present, absent and exact-flat target. The
schedule uses 48 photos per ISO, Bayer layout and within-pair
coupling cell. Three qualification updates on six separate
photos verified identical initial outputs, a frozen parent
and teacher, finite gradients and the scale-invariance check.
Training is active.
[Bound plan, source schedule and qualification](results/paired-shape-stability-v1/preflight.json) ·
[Frozen source archive](results/paired-shape-stability-v1/preflight-evidence.tar.xz).

## Evaluation

The evaluation reuses the exact 96-photo observations, three
redraws per noise setting and frozen V120 and Corpus 100k
predictions from the original repeat study. It measures
target-aligned fine response, shared and draw-dependent
error, exact-flat texture and ordinary fine error. For
each pair of heads, scalar response matching uses only the
original 64 photos. The additional 32 sources measure
transfer with the scales fixed. The response matching is
a diagnostic. Each head is also measured at its original
correction strength on every source.

Endpoint numerical evaluation and both GFX100S native
reviews are pending.
