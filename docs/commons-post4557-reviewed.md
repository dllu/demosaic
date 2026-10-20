# Reviewed Commons extension: 88,508 future training sources

The new two-scale corpus adds **2,751 training images** to the previously
reviewed 85,757, giving **88,508**. Validation remains 2,303 and test remains
2,255, with their original records preserved. This is a separate future corpus;
the V86/V87 model comparison keeps its frozen data. A trained quality or
scene-diversity benefit has not been measured.

[Complete freeze, source review and independent evidence](results/commons-post4557-reviewed-v1.json).
[Preparation and original-byte checks](results/commons-post4557-preparation-complete-v1.json).
[Actual new-source loader check](results/commons-post4557-loader-smoke-v1.json).

All 4,337 selected originals finished both 4× and 8× preparation. A separate
read-only audit verifies their 29.470 GiB of original bytes against publisher
SHA1s, all immutable live-index/source attribution fields, and all 8,674 cache
hashes/headers. Every cache is uint16 linear-sRGB. An independent integer
ties-to-even implementation checks all 2,953,488,120 cross-scale RGB codes:
4×→area2 differs from direct 8× by at most one code. Its exact rounding statements
also match all 262,141 possible four-uint16 sums. The auditor refuses an actual
unfinished producer before opening partial caches.

The protected-source screen withholds 58 sources: 53 train-bucket images and
five holdout-bucket images. The remaining 4,279 pass the unchanged pixel-duplicate
operator against all 95,634 prior rows. It adds no new duplicate exclusion.
One existing exact-cache link connects an old train row to its already excluded
alias; the previous exclusion and all other old records remain unchanged.

Final title retrieval recomputes the actual 3,852 candidate training queries
against all 9,660 prior heldout/reserved titles and all 432 new holdout hashes,
including the five protected flags. It withholds 1,089 title risks and eight
uninformative titles. All 3,852 labels agree with their preliminary labels;
no preliminary flag becomes eligible through the population change alone.

The completed DINOv3 query encodes all 4,337 direct-8× caches and retrieves
46,860 top-three records for 3,905 raw train-bucket queries across four pools.
The official frozen ConvNeXt-Tiny state and Torch RNG remain unchanged; the
first batch repeats bit for bit. Independent scalar dot/norm calculations
reproduce every saved cosine within 5.56e-16. Separate exhaustive rank replay
passes all 174 selected/prefix query-pool groups, and all 240 contact panels
rebuild exactly from their bound sources. This is not a second neural encoding
or an independent rank replay of every query.

All 44 complete source sheets and all ten neighbor sheets were actually viewed:
4,337 source thumbnails and 120 selected pairs. Thirteen pairs show conservative
scene/series risks; 107 show different scenes or ordinary subject similarity.
These are resized identity views, without restoration predictions or quality
scores. Different shell species, camera models, butterflies and unrelated
portrait projects are not automatically aliases.

Nine larger full-source views clarify the Strullendorf railway corridor and
Seville bullring families. Four additional `no-title-flag` sources stay withheld:
two railway images and two bullring/event/site images. The named station and
construction siblings already carrying title flags stay withheld too. Other
unrelated photographs from the same towns are not grouped by locality alone.
The ten previously reviewed prefix groups have no matches in these arrivals.

| Disposition among 4,337 arrivals | Sources |
| --- | ---: |
| Protected-source flags, outside the candidate | 58 |
| Final title risk/uninformative | 1,097 |
| Additional manually reviewed scene/site risks | 4 |
| New reserved sources | 427 |
| New eligible training sources | 2,751 |

The coupled freezer freshly checks all 5,502 newly eligible 4×/8× array hashes
and headers. Independent final review verifies identical training membership
and source fields across scales, every prior literal JSONL byte, all new
reserved/excluded decisions and the four additional withholds. All 58 protected
flags remain outside the additions. It also rechecks the current context trial's
269 frozen files and 758 inputs. Originals, prior caches and active model recipes
remain unchanged.

Three fixed newly eligible sources—first, middle and last—also pass the actual
CPU clean-image loader at patch256 with `augmentation_downsample: 2`. They execute
the existing geometry/PSF/final-area2 path, return finite contiguous FP32 RGB and
repeat exactly, preserving source bytes and Torch RNG. This check has no neural
forward or optimizer update, and does not qualify every source for a larger
320px recipe.

Frozen files are under
`/mnt/external/demosaic/commons-post4557-reviewed-20261020-v1/`:

- `manifest4.jsonl`: 88,508 train / 2,303 val / 2,255 test;
  SHA256 `18a21d02ea9256495aea1c7279404ca75a6baf77cb64c3fdc9bad4ed141d38e7`.
- `manifest8.jsonl`: the same active memberships plus 5,529 reserved and
  1,318 excluded; SHA256
  `fef9df8c528e0d979231b665f9aa153c48d509f71c327be4c93328c9568743b9`.

The 4× training manifest supports augmentation before the final 2× reduction.
Keep the existing validation manifest and all comparison inputs fixed in a
separate fresh training trial. Finite embeddings, fingerprints, metadata rules
and thumbnail views do not prove complete scene independence. This freeze does
not change the working model or its representative README performance crops.
