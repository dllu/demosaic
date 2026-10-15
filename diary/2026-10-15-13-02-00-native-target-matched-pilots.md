# Matched native-target pilots started

Launched V20 native-target and V21 control from the identical frozen V16
step5000 EMA. Both train the 144,072-parameter fine RGB branch only, with seed44,
LR3e-5, BF16 base / FP32 correction and the same 5000-step schedule, stopping at
1000 for review. V20 uses 50% paired /25% native-target synthetic /25% existing
synthetic batches; V21 uses 50% paired /50% existing synthetic. Both isolate data
RNG per global step and log sampled observation/target hashes.

Initial shared hashes match. CUDA floating-point losses differ slightly even
on the first identical batch, consistent with the existing nondeterministic
CUDA execution; bit-identical optimization is not claimed. Evaluation will
freeze checkpoints, use the existing known/unseen development panels, and retain
two native noisy/denoised/reference triplets per candidate. No protected final
test or personal GFX captures enter training.

V19's original controlled continuation has completed step5000 and its paired
evaluation has started. V18 joint tuning is still finishing. No candidate has
been promoted; the full quality and speed goals remain open.
