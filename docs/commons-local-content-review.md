# Original-source content spot check

All three deterministic contact sheets,48 original sources from the completed
1,188-image local batch, have been actually viewed. The sample includes brick,
stone and half-timbered buildings; steel stairs/bridges; foliage, flowers and
grass; lakes/rivers, snow and flat/cloudy skies; cars and a station building;
birds, a fox and an underwater fish; people/portrait scenes; and interior vaults,
wall art and ornament. No obvious corrupt or implausibly colored render appeared
in this finite sample.
[Per-source observations, source identities and sheet hashes](results/commons-local-content-spot-check-v1.json).

Selection uses the first48 fixed source hashes under
`sha256("commons-local-content-v1:" + source_sha1)`, independent of preparation
order or appearance. Every selected original matches its recorded byte count and
Commons SHA1 before and after preview decoding. The previews respect ICC color
profiles and EXIF orientation and use resized sRGB thumbnails with unchanged
exposure. The originals remain unchanged. Full source/author/license/credit
metadata and original Unicode titles accompany every sheet entry.

The complete batch has275 distinct author-field values and13 accepted license
strings. These count metadata values, not independent photographers or scenes.
Visible variety in this sample establishes neither source-family disjointness
nor improved training quality. This review covers original-source thumbnails;
prepared-cache color/quality review, complete integrity, duplicate/protected-scene
screening and a separately frozen data recipe remain required before admission.
The running V82/V83 data and README images remain fixed.

Local source sheets and observations:
`.cache/benchmarks/commons-local-content-20261019-v1/` contains `inspect.py`,
`contact-0.png` through `contact-2.png`, the attribution-bearing render receipt,
and `manual-review.json` with an observation for every actually viewed source.
Some caption glyphs are unavailable in the preview font; original titles and
image pixels are preserved. This is content evidence, without a model inference,
native sharpness/noise assessment or performance comparison.
