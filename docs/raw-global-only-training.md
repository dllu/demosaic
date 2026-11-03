# Training only the global RAW branch

**V138's original 1,000-step production and 150-input quality review are complete.**
The [completed report](v138-quality.md) finds tiny faint/flat gains against V120,
with no clear new mesh recovery. The completed
genuine CPU/CUDA 16+2 checks are adopted without replay. An explicit recovery
follows the terminal failure of its unrelated V125 admission dependency;
the training recipe, frozen source, parent and schedule remain unchanged.
All primary/faint/GFX/JPEG/flat audits and 46 native-board views are complete.
V120 Small remains the general recommendation.

[Recipe](../configs/quality-v120-raw-global-only-pilot-v138.yaml) ·
[Runner](../scripts/train_global_only_pilot.py) ·
[Training-scope implementation](../src/demosaic/raw_global_training.py) ·
[Tests](../tests/test_raw_global_training_scope.py) ·
[Check and queue evidence](results/raw-global-only-pilot-setup-v1.json).

The [completed V137 review](v137-global-conditioned-quality.md) shows stronger
global matching adaptation without clear new fine-mesh recovery. Its new branch
used the same LR1e−5 as the already trained restoration network. V138 tests a
combined intervention: freeze the parent and train the same normalized branch
at LR1e−3. This comparison cannot isolate the effect of learning rate from the
effect of freezing the parent.

Only 18 tensors/18,272 parameters train. All 91 V120 restoration tensors stay
exact in both model and EMA; the frozen official DINOv3 Small encoder also stays
unchanged. Bias-free differences make this branch return exactly zero for
per-phase spatial constants after adaptation. Freezing the parent therefore
preserves its response for that input class. This does not establish color
accuracy on arbitrary images or a photographic detail gain.

The separate [V139 memory-only prototype](raw-global-memory-only.md) removes the
direct local residual/MLP shortcut. It passes genuine CPU/CUDA16+2 checks with
15 branch tensors and the same91 frozen parent tensors. Its future operator
comparison uses V138's LR, scope, data and seed. Its original1k training and
matched native-quality review remain unstarted after the earlier dependency
queue exited. V138's explicit recovery does not launch V139. Completed checks,
saved predictions and the original architecture/source/budgets remain preserved.

## Training and compatibility

Set `raw_global_only: true` alongside `model.raw_global_features: true`.
Missing scope defaults to the existing joint training. The scope must be a
boolean and cannot combine with another head-only mode. Resume rejects a
changed scope before constructing a model; attention-mode guards remain in
force. EMA updates only trainable branch tensors, leaving frozen parameters
and buffers exact. V138's operator has109 model/EMA tensors and18 Adam states;
the memory-only variant has106/15.

V138 starts freshly from V120's 20k Small EMA, SHA256
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
It keeps V137's seed70, 90,782 photos/27 reviewed regions, 50% reviewed quota,
native256/B16/BF16, single noise view, zero optical blur, paired32/native128,
losses, 100-step warmup and original 1,000-step horizon. Every clean/noisy batch
must match saved V137 before candidate inference; initial executed outputs must
also match. The newest90,774/36 bank stays separate, and V134/V135 retain their
original 33-region cohort.

The learning-rate schedule reaches LR1e−3 after warmup. The short checks end
at update18, during warmup; they do not establish stability at peak learning
rate or convergence. Finite gradients/state and the original resource guards
remain required throughout production. Gradient metadata covers updates1–16
and every25 thereafter, 56 planned observations rather than all steps.

## Completed implementation checks

The focused suites pass 65 tests, including actual adapted flat-field output
equality for all four CFAs in CPU FP32 and BF16. Genuine CPU128/B1/FP32 and
CUDA256/B16/BF16 each complete 16 updates plus a real two-update resume.
Twelve changed-scope/operator resumes reject before construction. All18 branch
tensors receive finite nonzero gradients over each check; all 91 common model
and EMA tensors remain exactly equal to V120. Peak allocated CUDA memory is
8,198,603,264 bytes.

Independent saved-artifact verification executes no neural modules, noise,
RAW decoding or optimizer work. It checks 263,530,104 finite model/EMA/Adam
values across the four retained16/18 states, 263,237,680 exact common-state
values, 162,944,388 prepared values against V137, and 4,259,840 exact initial
RGB/auxiliary output values. All 65 existing modules outside `train.py` retain
their bytes; erasing the explicit new scope additions restores the previous
joint-training AST. The only new model-source module handles training scope.

The first test run had one incorrect fixture assumption: a model without DINO
was assigned the production model's parameter count. The corrected test checks
actual parameter identities; the original failure log is preserved.

## Completed quality review

The primary review uses exactly 102 new root/DINO calls: 64 shadow, 16 ordinary,
16 faint-ADC, four main-GFX512 and two extra-mesh768 inputs. All 408 saved
V120/V129/V136/V137 predictions are reused. It verifies the actual completed
1k endpoint, exact67-module trained source, frozen parent, 18 finite Adam states
and all1,000 batch matches before inference.

Actual outputs are 480 metric rows, 120 summaries and 64 native PNGs,
including noisy/restored/exact synthetic-GT triplets. An independent audit
checks every cell, 24,576,000 RGB channels. A prospectively frozen CPU-only
supplement adds original-source faint-detail strata, mean/spatial error
decomposition and four shared40× native displays: 300 strata,
160 decompositions and2,150,400 exact PNG channels. Enhanced displays are never
used for scoring. All 46 comparison/faint/JPEG/flat boards were viewed in 12
unresized sheets; the separately audited triplets repeat the comparison pixels.

The recovery also completes 48 retained analytic flats, without new noise or
old-control inference, for 150 endpoint root/DINO calls in total. It preserves
the primary/faint protocol and adds independent flat/sky reductions and both
camera-JPEG comparisons. All checks and actual native viewing are complete.

Both main DSCF3879/3880 and corrected extra DSCF3842/DSCF3835 scenes remain in
the review, including foliage and both fine green mesh regions/profiles.
ISO100/AHD and camera JPEG references differ in aperture, exposure time and
moving subjects; they are qualitative references, not exact GT. Both pairs,
JPEGs and siblings stay outside training; cached originals remain read-only.

CPU admission is40GiB, CUDA/production52GiB, allocator cap16GiB and runtime
floor32GB. Limits are30minutes per check and8hours for production. The original
V125 admission dependency ended in failure before V138 production started.
November 3 recovery verifies both original owners dead, adopts successful checks
and runs the original production worker/config once. It preserves the 16GiB
allocator cap, 52GiB admission, 32GB runtime floor and disk reserves. No automatic
retries, schedule resets, old control forwards or new20k run are part of this
pilot. Preparation stopped once for a missing analysis helper before any
review launch; missing helpers were then copied from the frozen V137 review.
A CPU report watcher also raced the first status write. Its failed owner,
source and receipt remain preserved; an explicit replacement finishes the same
zero-neural analysis budget with the original absolute deadline.

The engineering checks establish executable training. The completed review
measures small quality gains and the remaining detail failures; full427/camera/
color/frame performance, broad RawNIND superiority and speed remain unproven.

## Actual memory contribution

The [completed V137 branch diagnostic](global-memory-contribution.md) finds that
removing its trained memory write changes only0.83–1.39% of the added feature
offset RMS on six retained training contexts. That does not quantify final RGB
impact, but distinguishes varied attention from its actual feature contribution.

A separate original CPU companion was prepared to run after this V138 pilot's
primary/faint reviews and owner exits. It would reuse the verified endpoint and
the same six target-free branch inputs/probes, with12 new branch forwards/
backwards and24 attention softmaxes; all V137 controls are reused. It adds no
full-model/DINO calls, noise, RAW decoding or training in its declared budget.
CPU admission is40GiB,
runtime floor32GiB and the original faint-review absolute deadline remains fixed.
Its original dependency protocol remains preserved. The explicit recovery has
completed training and primary/faint/JPEG/flat review. Image quality is measured
in the completed report; the larger-update memory contribution remains unmeasured.
