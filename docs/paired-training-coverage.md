# Paired training coverage and the next edge-context test (V201)

The complete saved schedule already contains noisy flats and contrast-reduced
photos. The useful gap is more specific: **all 139 noisy mixed edge/quiet
batches have zero coupled pairs**. Existing paired domains supervise detail
against simpler absent/constant backgrounds. A next test should preserve the
same strong edge/background in both members and add only faint mesh to one.
Then the pair difference targets the weak increment while full-image and quiet
losses still constrain the common scene. This is a training-data hypothesis,
not a demonstrated image-quality gain.

This CPU metadata audit checks all **1,000 saved rows** against the completed
V200 training trace: **900 updates, 100 ADC skips and 3,600 noisy images**.
It reads no image arrays, original photos, noise samples or models and imports
no Torch. [Exact source-bound audit](results/v201-training-distribution-audit-v1.json).
The [V200 actual comparison](scale-supported-cfa-wave-comparison.md) supplies
the current image-quality evidence: small quiet/flat gains near V198, slightly
lower response, persistent fringes/ripples and incomplete fine cab crossings.

## Actual schedule coverage

| Domain | All batches | Noisy updates | ADC skips | Noisy images | Coupled pairs on noisy inputs | Domain weight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| flat | 153 | 141 | 12 | 564 | 0 | 1 |
| mesh | 341 | 307 | 34 | 1228 | 614 | 4 |
| mixed | 156 | 139 | 17 | 556 | 0 | 1 |
| photo | 243 | 214 | 29 | 856 | 428 | 1 |
| weak | 107 | 99 | 8 | 396 | 198 | 4 |

Each noisy batch contains four images. Domain weights describe the scalar loss
schedule; weighted update counts do not measure gradient size, Adam effects or
causal influence on quality.

The 428 photographic present/background pairs include
**215 full-contrast** and **213 reduced-contrast** recipes.
Reduced contrast spans **0.005031607–0.199394193**. The
paired photographic counterfactual is the augmented patch's constant channel
means; it removes the broad scene as well as fine detail. Merely adding the
first reduced-contrast augmentation would repeat an existing strategy.

All **556 noisy mixed-scene images** have nominal background level
parameters **0.002011904–0.049955419**, and bar half-width
parameters **2.026787395–19.955666203 pixels**. These
metadata parameters precede geometry/camera transport. Stripe/side intensity,
color transport and geometry also affect realized gradients; the level range
is **not a bound on image brightness or edge contrast**. Full-contrast photos
already supply edges, so this audit does not establish that strong edges are
absent from training overall.

## Prospective data change

Build generic training-only edge/background scenes with broad variation in
level, color, orientation, width and subpixel position. Form paired clean
targets with the **same broad scene**, placing a faint/dark crossed-wire
increment in one member. Retain cases where wires approach an edge as well as
quiet regions away from it. Shared camera/CFA and the existing coupled physical
sensor noise keep the weak difference meaningful. Include no-increment and
standalone-flat controls, rather than assuming support features reject them.

This changes which scene content the pair loss must explain. A broad common
edge cancels from the target increment; recovering only that edge cannot stand
in for recovering weak mesh. Existing full-image, gradient, anchor/regret,
common-pair and flat-spatial terms continue to constrain the common scene.
Actual benefit, loss balance and any response loss remain empirical questions.

Keep both protected GFX families, JPEGs and siblings excluded from training.
Do not use their pixels or references to construct these targets. A trained
trial must retain the complete matched present/absent/quiet/fresh-flat/photo
suite, raw and EMA endpoints, both real scenes/ROIs/noise profiles, native
noisy/restored/GT triplets and the existing building/flat counterexamples.
No new neural source, training, quality result or calibrated-confidence claim
is supplied by this coverage audit.
