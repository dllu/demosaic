# Complete incoming source review and remove atlas reproductions

Recorded: 2026-10-23T13:23:26-07:00 (America/Los_Angeles).

The original CPU V102 screen finished all 2,395 incoming training sources:
4,790 ADC-only/high-noise cases and 2,396 actual neural/DINO forwards. An
independent audit reconstructs source membership, the two cases per source,
loss/PSNR values and every saved top128-loss/top32-proxy list, while checking
frozen inputs and the exited original owner. No scan restart or partial rerun.
[Complete scan and visual-review receipt](../docs/results/incoming-source-loss-complete-v1.json).

All 74 unique final top32-loss/top12-proxy candidates now have actual native
views at their scored coordinates. The final pass adds 27 incoming identities
and revisits four prior sources whose earlier views used a different ROI.
Five actual native1024 views resolve uncertain flower, metal, stone, feather
and apparent stained-glass textures. The natural photographic targets remain
eligible; loss and metadata do not automatically decide quality. Cumulative
targeted native review covers 153 unique arrival identities, alongside all
3,807 full-source thumbnail contexts. This does not claim exhaustive manual
native review of the corpus.

One apparent stained-glass target is an atlas chromolithograph, confirmed by
its native view, local source credit and the primary Commons description.
The credit follow-up actually inspects seven training sources: five printed
atlas reproductions and two real photographed-window controls. Withhold the
five reproductions and retain both controls. Two other atlas sources were
already excluded and one reserved; those memberships stay unchanged. Four
newly withheld atlas images came from the older V102 corpus, with one from the
arrivals. This avoids an artist-name or stained-glass-wide exclusion rule.
[Current illustrated source review and primary attribution](../docs/incoming-commons-quality.md).

Freeze a separate 90,864-source 4×/8× corpus, applying these five decisions on
top of the three earlier photo-quality withholds. Relative to V104, eight
additional training IDs are withheld. Relative to V102, four older sources are
removed and 2,391 new arrivals remain eligible. Validation/test records and
order stay exactly 2,303/2,255; every other manifest row retains its literal
bytes. Originals and cache pixels remain unchanged. Preserve all prior
manifests, source decisions and machine receipts.
[Coupled manifests and literal-row evidence](../docs/results/commons-source-tail-reviewed90864-v1.json).

The unlaunched V107/V108 preparation on 90,869 sources is superseded by
V109 Tiny/V110 Small on 90,864. Both still use the identical V102-derived
Tiny-zero initializer, seed62, fixed20k/B16/native256/BF16, zero optical blur
and the original six byte-identical ROI objects. Only the declared official
encoder identity and run location differ between arms. All 50 numerical Python
modules match V104's frozen implementation. Twelve actual CPU clean-reader
examples repeat exactly, covering six new-source draws and all six ROIs,
with finite contiguous outputs, unchanged Torch RNG and no CUDA.
[Prepared matched recipes, hashes and reader audit](../docs/results/backbone-capacity-training-prepared-v2.json).

The prospective 20k photo schedule has 111,559 examples from 62,367 unique
sources, including 2,707 draws from 1,634 newly eligible sources and 5,657 ROI
examples. These are scheduled counts, not completed training exposure. No
production controller has launched for either capacity preparation. Review
V104 before choosing the next initializer; preserve these prepared snapshots
if a better completed model supersedes their parent.

At this entry, the original V104 trainer is live around step14,550/20,000,
with its exact original plan, 90,872-source inputs and evaluation, full-frame
GFX and material-detail queues unchanged. V102 final20k remains the completed
quality baseline. No new model-quality or capacity gain is established here.
State-of-the-art fine detail and the 100MP/10s goal remain open; quality comes
before speed work.

Separate actual discarded CPU checks subsequently pass eight updates for each
cleaned recipe, at native64/B1/FP32. The workers verify exact initial EMA,
per-arm frozen backbone identities and finite final model/EMA/Adam values.
All eight actual observation fingerprints match across arms: five
Commons/synthetic-domain updates, one native-RAW-synthetic update and two
paired-RAW updates. Production preparations remain unchanged and unlaunched;
CUDA and model-quality checks remain. These private eight-update checkpoints
are implementation fixtures, not model-quality endpoints.
[Actual CPU closure](../docs/results/backbone-cleaned-recipes-CPU-v1.json).

Verification checks 133 distinct referenced files against SHA256 across the
four new public receipts and source-view metadata. Four public source boards/
native images retain their exact inspected PNG bytes, including unchanged
native256/native1024 panels. All local links in the edited documentation and
this diary resolve; whitespace checks pass. Current docs replace the partial
review chronology with completed evidence, while earlier receipts and diary
entries retain their bytes.
