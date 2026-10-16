# Queue the current augmentation/data path's batch sweep

The previous goal turn made progress: it launched the guarded V37/V39/V43
step2000 continuation and published the matched fresh DINO recipes with CPU
initializer/output evidence. This turn revalidated live controller PID1038531
and the Commons downloader. V37 has finished; V39 is passing its intermediate
updates with the original resumed optimizer/schedule. Shared logged Commons and
paired observations agree with V37 through the observed prefix.

The original batch4–64 sweep used the8× path. The newer4× geometry/PSF pipeline
and larger native corpus can change preparation costs, so queue the same
two-repeat sweep on the current recipe rather than assume its optimum transfers.
This is throughput evidence only; keep batch16 fixed for quality comparisons.

The live queue PID1048124 waits for the corpus workflow's terminal success and
actual process exit. It then checks available RAM, frozen first1000 V43 checkpoint
SHA and private source bytes before starting the ten fresh benchmark cases.
It verifies complete output, both repeats for every batch and identical source
bundles afterward. It will fail rather than restart a missing/failed prerequisite.
No extra owned GPU work overlaps the active corpus workflow.

[Exact plan and source/initializer hashes](../docs/results/current-pipeline-batch-sweep-queue.json).
Live status:
`/mnt/external/demosaic/benchmarks/current-4x-native128-batch-sweep-v2-workflow.json`.
Output:
`/mnt/external/demosaic/benchmarks/mixed-training-4x-native128-batch-sweep-v2/summary.json`.
The queue driver is archived under the benchmarks directory; its hash is in the
plan. The corpus publication driver is also archived under runs as
`publish_native_corpus_2k.py`, SHA
`ccbfcb4369923c18b8144ec699138b4001f627aa711eafbcc0e5b78daaeb45c3`.

Next: review and publish the corpus second gate with its30 native triplets;
review timing results when complete; then begin the fresh matched DINO trial.
Do not alter the private V43 source while either owned workflow uses it.
