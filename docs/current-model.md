# Current model choices

**V120 Small remains the general recommendation.** The consolidation changes
software organization and experiment execution; it changes no trained weights
or measured quality ranking. [Architecture and commands](architecture.md).

| Choice | Useful strength | Remaining weakness |
| --- | --- | --- |
| [V120 Small](v120-v121-primary.md) | 37.04008 dB on 427 photos; known/unseen CFA means 54.31272/54.00872 dB; verified 102MP RGB16 exports | Fine foliage, mesh, neon and dark-field mottle |
| [V114 Tiny](v114-v115-quality.md) | Lower tested ADC maximum: 51.73 versus V120's 55.52 DN16 | Different photo/camera tradeoffs |
| [V187 pooled waves](pooled-phase-wave-comparison.md) | Quieter wave option; 5.359% constructed-GT mesh amplitude | Incomplete crossings, false waves and small flat/absent costs |
| [V195 response pressure](directional-response-comparison.md) | 5.575% GT mesh response; stronger than V187 in that comparison | Quiet RMS +0.334–0.376%; fine crossings unresolved |
| [V198 CFA innovation](cfa-innovation-wave-comparison.md) | 11.158% GT mesh amplitude; stronger colored synthetic and real cab modulation | New green/magenta building fringes; quiet RMS +1.151–1.648% versus V195 |
| [V200 cross-scale support](scale-supported-cfa-wave-comparison.md) | Quiet RMS −0.059–0.119% and fresh-flat RMS −0.022–0.030% versus V198 | Mesh response falls to 11.102% GT; building fringes, ripples and incomplete crossings persist |

V198/V200 do not combine strong fine-detail recovery with clean quiet fields.
These are bounded experiment results, not a broad ranking against V120. Mesh
response percentages describe projected amplitude, not overall restoration
accuracy. Real ISO100 captures differ in aperture, exposure and motion and are
qualitative references, not exact GT.

Earlier useful strengths remain available: [V171 standalone flats](learned-matching-residual.md),
[V172 balanced matching](local-noise-matching.md), [V173 quiet fields](weak-gradient-matching.md),
[V181 spatial loss](flat-spatial-evidence-comparison.md), [V183 coherent pairs](coherent-pair-evidence-comparison.md),
[V185 smaller support](spatial-context-wave-comparison.md), and
[the optional supported-amplitude stage](supported-wave-amplitude.md).
Their measured gains and weaknesses remain documented; the historical catalogue
is [preserved in full](history/current-model-through-v200.md).

## Loading and inference

The normal full-frame command remains in the [README](../README.md).
`demosaic-experiment models` lists the explicit preset catalogue.
`demosaic.models.registry.load_model("v120")` verifies the declared checkpoint
identity. V187/V195/V198/V200 use composed component loaders with explicit
historical checkpoint translation. They require supplied base RGB plus physical
RAW inputs; their component exports alone are not full-frame parent models.
[Package interfaces and limits](architecture.md).

## Current research and evidence

The [shared-edge cache](paired-training-coverage.md) is completed and audited:
156 changed rows and 844 exact adoptions. Its [matched trial is training](experiments.md).
No shared-edge model-quality result
has been measured. The new [configured runner](experiments.md) is ready for that
trial, with the same V200 architecture and loss recipe.

The [seven-state native viewer](images/v200-scale-supported-cfa-wave-v1/native-viewer.html)
retains raw/EMA endpoints, both protected GFX scenes, independent ISO100
references, noisy/restored/exact constructed-GT triplets and failure cases.
V200's complete endpoint/audit/native/export evidence remains in its report.
Broad state-of-the-art quality and 100MP within 10 seconds remain goals.
