# Pass final-cohort CPU and CUDA checks and start matched V43 training

Recorded: 2026-10-20T21:57:53-07:00 (America/Los_Angeles).

The original queued controller PID2355916/create1792554876.82 stayed live while
headroom recovered from about11 GiB to above48 GiB. It retained the original
60s stable-launch condition, active24 GiB RAM floor, root64/external384 GiB
reserves and no automatic retries. No other workload was changed. Its first
final-cohort CPU worker started after about53 minutes of waiting.

All six actual final-cohort preflights passed: CPU/native32/B1 and
CUDA/native256/B16 for V93, V94 and V95, 24 discarded updates each. This totals
144 genuine training forwards, 144 DINO calls and 144 optimizer updates, with
no validation forwards. Every arm starts at original V43 model hash
`4a45d92210acaeca3d4189c78eb22aa1cbc33f28b971dbeb56d1f6f29d62ed9a`
and DINO hash
`35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898`,
with fresh optimizers. All three data domains occur in each probe.

An independent CPU-only audit reads all six saved checkpoints and complete
metric files, verifies their hashes and exact final cohort/config identities,
checks 71 model/71 EMA finite tensors and69 finite Adam states with counter24
per checkpoint, all24 loss/gradient/input-hash rows, and actual preflight-owner
exits. Frozen source/input guards pass. Auditor CUDA remains uninitialized.
The executed workers additionally assert frozen DINO, configuration, parameter
identities and RNG invariants. Independent audit receipt:
`d06a464c59e0421b39706557ec285ad862cdbe0b59814e950299754550d50dd9`.

| Phase | V93/V94 shared native+paired | Changed Commons | V94/V95 shared paired | Changed treatment |
| --- | ---: | ---: | ---: | ---: |
| CPU |15|5|10|5|
| CUDA |15|9|10|14|

The control comparisons preserve the intended observations while the selected
corpus/augmentation treatments change others. No preflight checkpoint is used
to initialize production or to claim a quality gain.

The same controller has started the real V93 20k stage from the original V43
EMA, rather than continuing its discarded probe. The immutable startup
observation records production through logged step175, with all recorded losses and gradient norms finite,
live controller/worker identities, and about55 GiB available RAM. V94 and V95
will follow serially under the same frozen plan
`2fec2f3e77e15791d1ece4e10e65133a84be234eba0702a4d4dcd643753f7556`.
Startup snapshot receipt:
`18e9b6c3205fb438f3a48a2794785c463e3481aa178219cc8fad7deb78f75783`.

[Published preflight/production-start evidence](../docs/results/v43-quality-final-curated-preflights-v1.json)
and the updated quality/validation/experiment/completion guides distinguish
this actual production start from the earlier immutable queued-launch snapshot.
Final20k EMA remains the primary endpoint, with separate validation best and
4k/8k/12k/16k diagnostics. Independent full evaluation, native noisy/restored/GT
crops and actual real-reference inspection remain pending. V43 remains the
working reference; no completed new quality or speed result is claimed.

