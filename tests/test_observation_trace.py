import torch

from demosaic.train import batch_fingerprint


def test_observation_trace_ignores_layout_but_detects_data_metadata_and_type_changes():
    batch = {
        "packed": torch.arange(320).float().reshape(2, 4, 4, 10),
        "wb": torch.ones(2, 3),
        "mask": torch.ones(2, 3, 8, 20, dtype=torch.bool),
    }
    expected = batch_fingerprint(batch)
    altered = {
        "mask": batch["mask"],
        "wb": batch["wb"],
        "packed": batch["packed"].contiguous(memory_format=torch.channels_last),
    }
    assert batch_fingerprint(altered) == expected
    for name in batch:
        changed = {k: v.clone() for k, v in batch.items()}
        if name == "mask":
            changed[name].flatten()[0] = False
        else:
            changed[name].flatten()[0] += 1 / 65536
        assert batch_fingerprint(changed) != expected
    altered["packed"] = batch["packed"].bfloat16()
    assert batch_fingerprint(altered) != expected
