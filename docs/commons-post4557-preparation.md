# Preparing the newly downloaded Commons originals

A separate CPU job is preparing **4,337 new originals at both 4× and 8×**.
They come from the completed 4,557-file archive download and have not entered
training. Existing V86/V87 source membership, validation/test sets and the
standing GFX exclusions remain fixed. This is data preparation, without a
trained quality or scene-diversity claim.
[Actual launch and source bindings](results/commons-post4557-preparation-launch-v1.json).

Selection compares source SHA1 identities against the complete prior reviewed
8× corpus and all 1,188 earlier arrivals. It applies the existing free-license
whitelist, minimum 2,048px per side and maximum 120MP. The 220 omissions are
115 license labels outside that whitelist and 105 geometry failures. They stay
in the read-only archive. Selection uses no model output or image-content score.
Full source attribution is pinned in the original download snapshot.

The estimated two-scale payload is **27.524 GiB**, reusing the existing originals
directly rather than duplicating 29.470 GiB of source bytes. One CPU worker runs
at nice10 with single-threaded numerical libraries and hidden CUDA. Launch
requires room for the entire cache estimate plus4GiB margin above a **560GiB
external reserve** and **48GiB available RAM for60s**. Per-source memory/disk
guards stop this job before further decoding. A separate21600s timeout bounds
its own process group. Failure preserves partial output and does not restart or
change the trainer.

The worker verifies every selected live-index immutable metadata field, original
size and publisher SHA1, using a short read-only SQLite transaction. Existing
ICC/EXIF-aware linear-light ingestion writes atomic uint16 HWC arrays in a new
SSD root. Both scales retain deterministic source hash splits. Full cache bytes,
headers, attribution and prepared/error coverage are checked, followed by the
existing complete rounded4×→area2 versus direct8× one-code bound. The unchanged
protected-source screen uses42 cached references plus standing capture-name /
camera-date-family checks, without reading source HDDs or scoring model quality.

Screen-clear train hashes become `quarantine`; new validation/test hashes become
`reserved`. Protected flags stay withheld. Independent duplicate/content/known
series review and a coupled4×/8× admission freeze remain required. Finite
fingerprints do not prove scene independence. No partial output is a new corpus.

Ten focused tests pass, covering known/duplicate identities, unsupported licenses,
geometry, unfinished or corrupt downloads, changed attribution and resource
guards. The [actual two-source fixture](results/commons-post4557-CPU-check2-v1.json)
also verifies all original bytes/credits, all four arrays, both cache scales,
complete area checks and protected screening. Both resulting train hashes stay
quarantined. Every one of the full producer's50 frozen source files matches
that executed fixture; its45 package modules match the actual context trainer.
The production plan binds50 inputs. These are engineering checks, not evidence
that all4,337 sources are yet prepared or safe for training.

Operational root:
`/mnt/external/demosaic/commons-post4557-preparation-20261019-v1/`.
Its `status.json` records the exact owner, plan and current stage. The dated
launch observed PID257168/creation1792448532.19; check PID and creation time
together before acting. New arrays and receipts live under `work/outputs/`.
The archive/index and all original photos remain read-only.

## Preliminary title and source-family review

The [metadata-only screen and actual source-pair review](results/commons-post4557-title-review-v1.json)
cover all4,337 arrivals before the complete cache/protected/duplicate results.
There are3,905 train-bucket queries and432 newly reserved hashes. Anchors include
all9,660 prior validation/test/reserved titles and all432 new reserved titles.
The unchanged.55 title threshold flags1,102 queries;8 more have no feature
neighbor. The other2,795 have no title flag and still require all remaining
review. No new source is admitted.

Eight focused tests pass. The reusable matcher reproduces all10,735 historical
feature sets and all1,075 earlier threshold decisions, with maximum3.34e-16
top-score difference. Sorted `math.fsum` accumulation makes the new calculation
deterministic. Independent source/label coverage checks and dense FP64 dot/norm
replays verify all19,448 saved neighbors, with maximum4.45e-16 difference.
This checks saved-neighbor arithmetic rather than exhaustively recomputing
every absent pair; title similarity does not establish scene identity.

Two fixed sheets containing36 source pairs were actually viewed:24 high-ranking
matches to the prior corpus and12 to newly reserved arrivals. They show shared
buildings/sites, a coastal statue and a tractor capture sequence, including
different framing/details that a near-identical-pixel test can miss. Broad
locality/topic matches also occur: different Seattle scenes, masked-person
photos and different parade years. Those preliminary flags remain withheld;
the sample is not a complete content review and reused anchors are not
independent observations. The resized identity thumbnails are not native model
performance crops. Every original source/credit remains unchanged.

IDF depends on the candidate population. Final title decisions must be recomputed
after complete caches and protected/pixel-duplicate screening establish the
actual candidate set. These preliminary counts are not the eventual corpus size.

## Queued pixel-duplicate audit

The [duplicate queue](results/commons-post4557-duplicate-queue-v1.json) waits for
the exact preparer's successful exit and complete area/protected receipts.
It then runs the existing dHash≤8/correlation≥.99 operator against all95,634
prior8× rows, using a private clone of the completed fingerprint cache. It
preserves every prior source/split, reserves new holdout hashes and withholds
new groups linked to existing sources. Source/index/cache inputs remain
read-only; no active model recipe changes.

A genuine two-new/two-prior-source fixture completed this queue and audit.
All48 production source copies match the fixture. A separate intentional startup
stop confirms that the disposable controller cleans up its own child while the
actual trainer stays live. The added disk guard and SIGTERM cleanup affect
orchestration; the fingerprint operator is unchanged. The audit retains48GiB
available RAM and548GiB external reserves, a30s stable launch gate and a3600s
active bound. Failed predecessors or guards prevent continuation, without an
automatic retry or admission. Its root is
`/mnt/external/demosaic/commons-post4557-duplicate-audit-20261019-v1/`.

## Complete heldout content bank and queued source inspection

The [content-bank and source-review receipts](results/commons-post4557-content-review-setup-v1.json)
add a DINO screen for aliases and different views that titles and pixel
fingerprints can miss. This is source-overlap inspection, without restoration
predictions or protected-final model scoring. Its anchor population contains
all9,660 prior Commons validation/test/reserved images,150 cached native-camera
inspection renders and45 cached protected references. The Commons assignments
remain2,303 validation,2,255 test and5,102 reserved. All originals remain
read-only and source HDDs are never opened.

The bank uses the existing official frozen DINOv3 ConvNeXt-Tiny revision and
preprocessing: exact direct8× uint16 linear-sRGB cache, central largest square,
linear area192, sRGB transfer, ImageNet normalization and normalized pooler
vector. CPU/F32/B8/two-thread execution replays both historical first batches
bitwise. It reuses726 pixel/recipe-matched vectors and computes9,129 missing
ones. Model config/weight bytes and executed source are bound explicitly;
the encoder and Torch RNG remain unchanged. Every selected cache hash/header
is checked during execution. Independent review checks all9,855 anchor records,
all726 reused vectors, all vector norms and all22 fixture rows/vectors against
the full job. This is not a second independent encoding of every fresh source.

Twenty-two focused tests pass, including cache/recipe incompatibility, complete
heldout coverage, cosine normalization, ties at the top-three boundary and
train-versus-reserved query separation. A genuine22-anchor/two-query CPU fixture
also runs the complete retrieval and exports its source sheets. Independent
dense FP64 dot/norm calculations reproduce all ten available neighbors and
their ranks within1.39e-16. Both original historical batches and the first fresh
batch repeat exactly. The two source thumbnails and seven query-pair cells were
actually viewed. The fixture has a deliberately tiny bank and provides no
corpus-safety result.

The production query queue waits for the exact new-cache producer's successful
exit, complete two-scale coverage and zero-error area/cache receipts. It encodes
all4,337 new direct8× caches, then retrieves exhaustive FP64 top-three neighbors
for each of3,905 train-bucket queries in four pools: prior Commons heldout,
newly reserved432 hashes, native150 and protected45. Planned output is46,860
neighbor records. A fixed review selection takes24 rank-one matches per pool
and24 additional prior-heldout matches from queries with no preliminary title
flag. Repeated pairs keep their selection reason. There is no automatic
similarity cutoff, exclusion release or admission. Full actual viewing and
source-family decisions remain separate work.

A second small queue can render all4,337 source thumbnails as soon as the
complete4× manifest, error file and summary have finalized, while8× preparation
continues. It requires exact selected-source/attribution coverage, no preparation
errors and every cache hash/header. The44 planned sheets fit full cached images
inside136×96 using independent linear-light RGB BOX-area resizing followed by
sRGB, without exposure adjustment. These resized source-review thumbnails are
not native100% model-performance crops. Three genuine two-source invocations
export the identical PNG. Rendering alone does not review or approve sources.

Both jobs hide CUDA, run at nice10 and retain48GiB available RAM and548GiB
external disk. The query job has a30s stable launch gate, one-hour resource
wait and one-hour active bound; its producer wait is bounded at seven hours.
The thumbnail producer wait is bounded at four hours and rendering at one hour.
Failures preserve output without retrying or changing another job. The initial
bank fixture's missing default HF-cache failure and an unused idle thumbnail
waiter retired for a readiness fix are preserved in the receipt. The corrected
fixture binds the explicit project SSD model cache; production sources match
the executed successful fixtures.

Operational roots:

- `/mnt/external/demosaic/commons-post4557-content-bank-20261019-v1/`
- `/mnt/external/demosaic/commons-post4557-content-retrieval-20261019-v1/`
- `/mnt/external/demosaic/commons-post4557-contact-queue-20261019-v2/`

These are inspection artifacts and queued work. Complete new caches, actual
content/source-family review and a deliberate coupled4×/8× admission freeze
are still required. Existing V86/V87 data and the representative README crops
stay fixed.
