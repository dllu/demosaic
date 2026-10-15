# Native-target body-adaptation comparison

V20/V21's first1000-step fine-only comparison has no convincing gain. To test
whether the restoration body needs to adapt to the new camera-linear targets,
V22/V23 repeat the same seed44 schedules, architecture, initialization and
hyperparameters with restoration and fine correction trainable. DINO remains
frozen. The planned first1000-step reviews will complete the body/fine-only by
native/existing-data comparison, tracing sampled observations for all arms.

Both configs retain the planned5000-step LR schedule but stop at1000 for
review. Neither changes the current inference model. Protected final and GFX
qualitative scenes remain excluded. Source/lockfile/data snapshots are retained
by the trainer. The quality and speed goals remain open.

Both jobs started successfully, with 4,819,236 trainable parameters each and
finite losses through step25. Their first two logged batch hashes (steps1/25)
exactly match the corresponding V20/V21 fine-only arms. Logs are
`.cache/train-dino-native-joint-v22-1k.log` and
`.cache/train-dino-native-joint-control-v23-1k.log`.
