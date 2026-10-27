"""RAW global attention with normalized matching and per-image amplitude scales."""

from torch.nn import functional as F

from .raw_global_features import RawGlobalFeatures


def normalized_cross_attention(query, key, value, heads=4):
    """Scaled cosine matching; keep value amplitudes and image batches separate."""
    if query.ndim != 3 or key.ndim != 3 or type(heads) is not int or heads < 1:
        raise ValueError(
            "Normalized attention requires three-dimensional features and positive heads"
        )
    batch, queries, width = query.shape
    tokens = key.shape[1]
    if width % heads or key.shape != value.shape or key.shape[::2] != (batch, width):
        raise ValueError("Normalized attention requires matching per-image key/value channels")
    q = query.reshape(batch, queries, heads, width // heads).transpose(1, 2)
    k = key.reshape(batch, tokens, heads, width // heads).transpose(1, 2)
    v = value.reshape(batch, tokens, heads, width // heads).transpose(1, 2)
    q = F.normalize(q, dim=-1, eps=1e-6)
    k = F.normalize(k, dim=-1, eps=1e-6)
    weights = (q @ k.transpose(-2, -1) * (width // heads) ** 0.5).softmax(-1)
    return (weights @ v).transpose(1, 2).reshape(batch, queries, width)


class ConditionedRawGlobalFeatures(RawGlobalFeatures):
    """Reuse all18 tensors and initial values, changing only global mixing.

    Normalize query/key vectors per attention head. Normalize values by one
    per-image RMS scale before memory aggregation, then restore that scale to
    returned context. This retains an amplitude-bearing value path and an
    exact-zero response for per-phase spatial constants. It does not establish
    trained restoration quality or change a legacy model's operator.
    """

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
        content = content + context * image_scale
        normalized, scale = self.normalize(content, self.ff_gain)
        return content + self.down(F.gelu(self.up(normalized))) * scale
