# Review the mixed-optics 128-update checkpoint

Recorded: 2026-11-20T00:09:39-08:00 (America/Los_Angeles).

The 128-update mixed EMA gains 0.247 sharp-normalized weak-response
points over the 128-update sharp regional EMA at σ 0.85. Continuing
wire RMS falls 0.199 DN16 and false weak projection rises 0.031 DN16.
Flat RMS changes 0.006 DN16, with the paired interval spanning zero.
The mixed EMA still recovers 0.586 points less than the Local 50k
starting EMA on the same inputs. The gain over the regional EMA is
larger on sharp inputs. Both viewed native crops retain incomplete
faint crossings.

Replayed the clean targets from all 256 blurred wire training groups.
Median weak contrast retention is 99.33% at σ 0.40 and 96.65% at
σ 0.65. The shortest-period quarter at σ 0.65 retains 88.48%, and
21 of all 256 blurred wires sit in the optical test's period range.
Exact flat cores and eroded true-gap targets match their controls.

The 1,024-update run and the queued reviews continue. The 24
confirmation sources remain reserved for the endpoint. A separate
response-matched diagnostic now ships with the endpoint review.

[Development review and native crops](../docs/local-optical-mixture-128.md) ·
[Paired scores and training target audit](../docs/results/local-optical-mixture-v1/development-0128.json).
