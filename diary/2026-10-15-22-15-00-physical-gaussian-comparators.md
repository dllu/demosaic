# Physical Gaussian-prior comparators

Previous goal turn was progress: scale-aware control review completed and a
frozen Gaussian prior produced a strong exact-flat result. Full quality/speed
objective remained unmet. No previous processes were live at turn start.

Implemented centered generalized Anscombe stabilization with float64 physical
math, a numerical expectation inverse and smooth matched high-count asymptotic
tail. Initial quadrature and tail bias were identified with independent dense
integration, then corrected using root-substituted Legendre quadrature and a
continuous tail. Algebraic and published closed-form inverses remain diagnostics.
All214 tests pass in16.47s, Ruff passes. Coverage includes inversion bias/precision,
all CFA layouts, CPU/CUDA, constant/ADC identity, projection geometry and external
source/weight integrity. No numerical-image editing/generative tools used.

Added verified, frozen external Gaussian adapters to paired/synthetic/GFX
reporting. Explicit input-only/nominal shot/read, no target gains or per-image
fitting. Original files untouched; GFX scene/siblings excluded from training.
Verified all four full GFX TIFFs as8746x11662x3 uint16, 16-bit sample tags, sRGB
ICC profiles and thousands of sampled codes. Gray baseline restoration148.05s,
V16 31.35s in the same shared-machine run; not idle timing. Quality/speed open.

Complete gray method known/unseen primary53.28781/52.08223 versus V16
53.27466/53.07857, RawNIND54.06860/53.56220. Gray rendered RGB PSNR is
38.34481/35.28710, SSIM .905832/.855573: substantial general-camera deficit. GFX crop inspection
shows clearer fence/foliage than V16 but remaining colored specks/checkerboard.
No promotion. Complete synthetic64-photo screen also behind V16.

Prepared RGB weights with strict load and external MIT notices. Initial joint
four-step HQS-style pilot uses strengths8/4/2/1, weight.23, first2named scenes
perpanel only. It removes colored specks but softens texture. On first2 unseen
scenes, auxiliary PSNR/SSIM38.24181/.923314 versus RawNIND38.20981/.922831,
but measured PSNR52.15833 versus53.04158. Not comparable to full-panel means.

Input-only scalar/channel/mean gain diagnostic on one predetermined M100 crop
failed to close measured PSNR gap, so no gain calibration was added. A second
fixed pilot tests8 strengths4→.5 and weight.05 for greater fidelity. Live sessions
28400 (paired first2) and40847 (GFX), logs `.cache/eval-gat-joint-first2-v2.log`
and `.cache/gfx-gat-joint-v2.log`. Their authoritative status must be checked;
do not restart on observation timeout. Initial4step, gray/full and prior jobs
all exited successfully. Source/manifests/weights archived per output.

Method/cmds: `docs/stabilized-gaussian-review.md`. Reproducible final quantitative
and crop receipts still being assembled for gray and pilot comparisons. No claim
of a promoted photographic model, state of the art or achieved speed objective.
