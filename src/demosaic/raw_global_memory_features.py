"""A global RAW branch whose returned feature travels through memory attention."""

from .raw_global_conditioned_features import normalized_cross_attention
from .raw_global_features import RawGlobalFeatures


class MemoryOnlyRawGlobalFeatures(RawGlobalFeatures):
    """Remove the direct local content/MLP shortcut from the normalized mixer.

    Keep the same deterministic initialization for all fifteen shared tensors.
    The zero final projection preserves the parent at initialization, and
    bias-free value paths preserve per-phase constants after learning. This
    forces the branch offset through both attention operations; it does not
    establish that matching or restored image quality will improve.
    """

    def __init__(self):
        super().__init__()
        del self.up, self.down, self.ff_gain

    def mix(self, content, condition):
        normalized, _ = self.normalize(content, self.content_gain)
        keys = self.to_keys(normalized) + self.condition(condition)
        queries = self.read_query(self.latents).expand(content.shape[0], -1, -1)
        image_scale = (content.square().mean((1, 2), keepdim=True) + 1e-4).sqrt()
        memory = self.read_out(
            normalized_cross_attention(queries, keys, self.to_values(content / image_scale))
        )
        normalized_memory, _ = self.normalize(memory, self.memory_gain)
        query = self.write_query(normalized) + self.condition(condition)
        context = self.write_out(
            normalized_cross_attention(
                query, self.write_key(normalized_memory), self.write_value(memory)
            )
        )
        return context * image_scale
