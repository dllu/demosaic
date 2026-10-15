# Native-target body-adaptation comparison

V20/V21's first1000-step fine-only comparison has no convincing gain. To test
whether the restoration body needs to adapt to the new camera-linear targets,
V22/V23 repeat the same seed44 schedules, architecture, initialization and
hyperparameters with restoration and fine correction trainable. DINO remains
frozen. This completes the body/fine-only by native/existing-data comparison
at the first1000-step review, while tracing sampled observations for all arms.

Both configs retain the planned5000-step LR schedule but stop at1000 for
review. Neither changes the current inference model. Protected final and GFX
qualitative scenes remain excluded. Source/lockfile/data snapshots are retained
by the trainer. The quality and speed goals remain open.
