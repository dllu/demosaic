# V168 checkpoint recovery after the local disk guard

The original model worker stopped before update916 because internal free space
fell below its56GiB guard. It had completed915 updates per head;its latest
durable full checkpoint was750. The original controller,training failure,queue
failure,journals,checkpoints and sources remain intact.

Recovery loads the actual750 model,EMA,Adam and CPU/CUDA RNG states. All915
original control rows match V167,and the750 control model/EMA/Adam state matches
V167's750 checkpoint.165 overlapping updates751–915 are recomputed;both arms'
complete recorded rows match bit-for-bit. Original915 state was not saved,so
no direct comparison to that unretained state is claimed. The fixed horizon
continues to1000. New checkpoint915 is retained. Resource pressure now causes
a durable checkpoint before waiting,rather than losing in-memory state.

117 of this project's own procedural mesh NPZ fixtures,1.257GiB,were copied to
fast external SSD with their recorded hashes checked before atomic replacement
by links at the original paths. Fixture/receipt bytes remain unchanged. No
original media,RAF,JPEG,training pixels,noise draw,model or loss changes. The
56/116GiB local/external reserves and future review projection remain satisfied.

Actual model accounting adds330 recovery forwards/1320images:5638 head roots /
12688 images,including20 original smoke,2330 physical training/recovery and3288
review forwards. Logical planned trajectories still have2000 unique training
head updates.342 parent/backbone roots each remain separate and unchanged.
There are15 recorded original/recovery scientific owners. One training resource
failure caused two dependent controller failures;one checkpoint recovery follows.
No full-training restart occurs. The parent-policy correction and first read-only
preparation-verifier bookkeeping correction remain separately preserved.

Final gradient maxima cover smoke first10 and recovery751–1000,not global
first1000 maxima. The original and resumed sources assert every gradient finite
on every completed update. All822 quality cases/four raw/EMA endpoints and
72 native figures/24 triplets remain required;restoration quality is pending.
