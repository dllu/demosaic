# Preserve numerical output while removing repeated work; extend native4

Previous goal turn made progress: implemented pre-downsample Commons augmentation,
selected-only data loading, full batch sweep and batch16 startup. Revalidated all
owned live processes rather than restarting them. This turn V31 completed2000;
Commons4 preparation and Commons original downloading remain live.

VST profile construction rebuilt the identical2721x321 Poisson probability
matrix and integration nodes for every fresh sample noise profile. Cached one
read-only6.69MiB grid, preserving original arithmetic/reduction order. Compared
132profiles against frozen original source: every expected/mean array is
bitwise identical (0..6e- plus16/1000/1e8). Three64-profile CPU repeats:
5.275->.806ms/profile (6.55x). Four alternating real mixed-training cases atB16
use isolated source snapshots differing only in vst.py, same initializer,
noise/data/optimizer/EMA and active2-worker4x preparation. Original26.18images/s
(range25.98..26.38), cached29.07(range28.78..29.37), +11.05%, same6.94GB CUDA.
Not a6.55x training claim. Receipts docs/results/expectation-grid-performance.json.

Extended the same4x->geometry/PSF at2x->final2x average to native camera-linear
training targets. Metadata/camera units retained; default8x behavior preserved;
wrong bins/sizes and resume recipe changes rejected. Prepared the same53lowISO
captures/31scenes,474370336bytes, with identical raw-sourceIDs and permissions
hash. Source captures/GFX/protected scenes remain read-only/excluded. Real cache
sampling and invariant/mixed resume tests pass. The first receipt writer used a
nonexistent top-level attribution key; corrected it to the existing row credit,
without changing data/runtime. Full validation256passed37.87s; Ruff passed;
rebuilt wheel exact VST/native/trainer code plus four license notices verified.

Added scripts/freeze_rebinned_manifest.py: producer lock must be released and
complete activeIDs/splits must match the audited source exactly. It rejects
partial membership, changed protected splits and overwriting a frozen manifest.
A watcher on owned full-prep parent4123563 will freeze the complete Commons4x
manifest after that producer exits. V34's recipe points to that future immutable
audit, with Commons/nativeaugmentation2 and original8x validation. It is matched
to V32(seed46/B16/LR3e-5/same V30EMA), and has not started. No reduced partial
corpus is substituted for the full selection while waiting.

V31's extra1000B16updates(16000examples) improved synthetic16 photoPSNR/SSIM
34.81952/.957844->35.08524/.958737, but real primary54.25796/53.75824 fell to
54.13644/53.54885. Decline intervals excludezero on these small development
panels. GFX mesh remains irregular/leaves soft; no convincing qualitative lead.
Stop at2000; no promotion or automatic extension. Published exactGT native2
triplets plus accurately labeled real references, complete numerical receipts
and docs/anchored-rgb-b16-v31-review.md. README keeps full-frame V30 examples.
Parent V30 overall real/synthetic metrics reproduce within1e-7 with cached VST.

Queued matched V32/V33 after the controlled performance jobs. Identical V30EMA
initializer, fresh optimizers, seed46/B16/LR3e-5/planned3000 and original8x data;
control25%paired/25%native/50%Commons vs50/25/25. Both stop1000; compare shared
logged-domain hashes, then matched known/unseen/synthetic16/GFX. V32 is training;
V33 follows. Lower LR/data balance are hypotheses, not presumed improvements.
No source edits after the first arm's snapshot; scripts/docs/tests are separate.

Final quality, complete mature-candidate evaluation, protected-final and under10s
full102MP gates remain unmet. Goal stays active. Full4x corpus still prepares;
newly downloaded Commons images still need their own extension/deduplication
review rather than silently entering the frozen trials.
