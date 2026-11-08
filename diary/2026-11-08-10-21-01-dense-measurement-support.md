# Dense measurement support diagnostic

Recorded: 2026-11-08T10:21:01-08:00 (America/Los_Angeles).

The previous goal turn made concrete progress: V191 completed full training, independent audits and all native views, but regressed on detail. Its architecture changed measurement taper, local frequency grid, coefficient units and synthesis together. V192 isolates linear measurement support and carrier mismatch before choosing another model.

The deterministic test crosses 48 fixed tones (12 base65-grid centers × four prescribed offsets), unit-amplitude cosine/sine quadratures, uniform/graded independent variance, interior/corner positions, three measurements and exact/nearest carrier modes: 1,152 cases. Rectangular65 uses available global256-grid frequencies only as a resolution comparator, not V187's actual sparse selector. No real image, GFX reference, learned checkpoint, sensor-noise draw or neural forward is used. These are analytical one-phase measurements, not joint-CFA RGB recovery or statistical replications.

With exact frequency, Hann65 retains 43.1–45.2% of rectangular65 SNR power, and Hann129 retains 170.7–172.8%. With nearest available carriers, ranges are 23.0–47.6% and 112.4–175.9%. Uniform interior means are .3606 / 1.4634; corner means are .4076 / 1.6129. All 48 fixed cases per condition place Hann129 above the rectangular comparator and Hann65 below; this is not photographic confidence or a learned quality result. For an unfitted interior coherent average, effective sample counts are 4,225 / 1,820.44 / 7,281.78 for rect65 / Hann65 / Hann129. Symmetric interior windows cancel the deliberately linear variance gradient in the relevant sums, so overlapping curves do not establish robustness to general heteroscedastic camera noise.

Fifteen CPU contracts and the independent QR audit pass all 1,152 cases, 12,672 response/variance coordinates, 768 ratios and sixteen Decimal means. The standalone PNG/SVG/PDF 2×2 CDF was actually viewed, with all 768 plotted points checked against audited values. Sources, cases and owners are frozen/bound. All successful scientific work completed once, and all 103 neural source hashes remain unchanged.

This supports a larger coherent-window trial while leaving actual texture, nonlinear mixing, false quiet structure, compute cost and native real-fence quality unresolved. Larger support may spread edge structure farther into quiet regions. V187 stays preferred and V120 Small remains the general recommendation until a trained variant passes full native review. No dataz/original/reference access or external output allocation occurs; the new analytical outputs are local with a 40 GiB floor. The overall quality goal remains open.

[Full calculation](../docs/dense-measurement-support.md) · [Evidence](../docs/results/v192-dense-support-v1.json) · [Publication verification](../docs/results/v192-dense-support-publication-verification-v1.json).
