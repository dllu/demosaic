# Fit and review bounded gains on verified Bayer carriers

Recorded: 2026-11-20T01:34:46-08:00 (America/Los_Angeles).


Fit two 409-parameter gain heads while freezing Local 50k and
the admitted Bayer waveform basis. Both used 192 distinct
training photos across two noise profiles and three blur doses,
with 192 optimizer updates per head. The two CPU fits took
1.85 s after capturing and reducing the common training data.
The archive preserves raw and EMA checkpoints and the exact
photo/observation bindings.

On 32 separate photos with two noise draws, the broad-head
EMA gains 2.787 weak-response points at nominal strength
versus the fixed combined check. Its continuing-strand RMS
falls 6.798 DN16 at nominal strength and rises 6.252 DN16 at
similar weak response. The center-statistics arm gives almost
the same held-out wire scores. The nominal gains reach the
cap in 87.1% of accepted intact-wire directions in the broad
arm. Full-cap delivery explains most of the learned benefit,
with more false weak projection.

Viewed both exact triplets and both complete standing GFX
families. The stronger learned gain adds contrast and
regularity, especially on the right. The fine crossings stay
incomplete. On the natural aligned replay, no donor pair is
nominated in any of the 32 photos. The mismatched exterior
increases rare false updates. The fixed general panels do not
cover the new crop component.

[Training and review](../docs/local-bayer-gain.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Fine mesh map](../docs/gfx-green-mesh.md) ·
[Fixed-panel coverage](../docs/performance-history.md).
