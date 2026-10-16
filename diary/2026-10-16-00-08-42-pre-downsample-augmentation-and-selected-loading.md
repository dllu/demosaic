# Address sampling order, batch size and discarded data work

The user requested augmentation before final binning, a measured batch sweep,
and an audit for discarded Commons batches. Confirmed the old trainer consumed
one Commons batch every optimizer step before substituting paired/native data.
Now domain-specific global-index samplers and lazy loaders fetch only selected
batches, stopping prefetch at the requested endpoint. Seed45 first1k selects
514 Commons,230paired,256native:2056 instead of4000 consumed Commons examples
at batch4. Reproduced all41 original V30 logged observation/target hashes exactly
with the new loading route. Existing mixed restart tests retain exact model/EMA.

Added optional augmentation_downsample2: originalICC to linear4x uint16 cache,
exactD4 and combined crop scaling/projective interpolation at2x output resolution,
PSFs in final-pixel units, then final2x2 average. No geometry interpolation after
that reduction. Procedural examples also use the higher intermediate resolution.
Validation keeps the old8x manifest via a separately hashed/snapshotted option;
resume rejects changes. Native-RAW synthetic still uses its existing8x path;
a separate4x native cache/loader extension remains to implement.

Added frozen-selection rebinning without source/split mutation, and corrected
SQLite ingestion to honour committed WAL rows instead of unsafe immutable reads
while downloads run. Materialized metadata releases the read snapshot before
long decoding. Prepared/checked256 actual4x sources, all splits preserved;
four direct4then2 comparisons differ from8x caches by at most oneuint16 code.
A controlled projective cosine test reduced MSE .00493965 to.00047290 against
a denser reference. This is a sampling test, not trained quality evidence.

Full suite248passed20.53s; Ruff passed. First run247passed/1failed because a
new test altered the validation JSONL by adding a blank line (invalid input),
so it failed parsing before the expected hash guard. Changed the fixture to
valid trailing whitespace; the guard and full suite pass. No runtime workaround.

Started a real mixed-training throughput sweep: batches4/8/16/32/64, two repeats,
15warmup excluded/45measured, fresh model/optimizer processes from identical V30
initialization. Includes actual data/GAT/DINO/backward/Adam/EMA. It uses the old
8x path so only batch changes; new4x path throughput and convergence are separate.
Do not choose a batch or scale LR before the completed measurements. Queue:
after the live sweep, CUDA4x-batch smoke, full102MP V28-5k/V29/V30/RawNIND with
allRGB16files reverified, then full frozen-selection4x preparation. Only owned
jobs are managed; unrelatedGPU process is untouched. Commons download continues.

V30 first1k terminalreview improves real primary54.25796/53.75824 and screen
photo34.81952/.957844 over V29. Real rendered deficits/highlight error remain;
not SOTA. Published native exactGT triplets and correctly labeled GFX foliage/
fence in docs/anchored-stabilized-rgb-v30-review.md and numerical receipt; README
uses current experimental GFX examples. Full427/protected-final/noDINO trial,
quality target and10s/100MP remain open. Goal stays active.
