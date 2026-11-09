# Audit paired training coverage before stronger edge-context data

Recorded: 2026-11-08T18:58:16-08:00 (America/Los_Angeles).

After completing and publishing V200's full quality comparison, inspected the
saved training metadata and completed trace before choosing another data/loss
change. The full audit checks 1,000 row identities, batch bindings, domains and
noise flags. Counts agree: 900 noisy updates, 100 ADC skips, 3,600 images.
It reads metadata/trace JSON only, imports no Torch, draws no source/noise and
reads no training image arrays or protected captures. The executed script was
copied before execution; source/input hashes are bound before the row audit
and match again afterward.

Noisy updates by domain: mesh 307, weak 99, photo 214, flat 141, mixed 139.
There are already 428 photographic present/background pairs: 215 full-contrast
and 213 contrast-reduced. Flat training is also already present. All 139 noisy
mixed edge/quiet batches have zero coupled pairs. This rules out assuming that
flats or contrast reduction have simply been omitted; the paired scene content
is a more specific next variable.

The prospective change is training-only paired scenes sharing a broad strong
edge/background, with a weak mesh increment in only one member. Pair difference
then targets the weak increment while common-scene/pixel/flat constraints remain.
Existing photo counterfactuals replace the broad scene with constant means, so
their target increments also include strong scene content. This rationale does
not prove a causal explanation of current artifacts or a future quality gain.
Nominal mixed levels and widths precede camera/geometry; full-contrast photos
already include edges, so strong-edge absence is not established globally.

[Coverage report and prospective data test](../docs/paired-training-coverage.md) ·
[Source-bound audit](../docs/results/v201-training-distribution-audit-v1.json) ·
[Current V200 quality evidence](../docs/scale-supported-cfa-wave-comparison.md).
