"""Mixed-domain optimizer batches with unchanged per-source supervision."""

from collections import defaultdict

import torch

from .losses import DEFAULT_RECONSTRUCTION_EPSILON, reconstruction_loss
from .paired_training import paired_reconstruction_loss
from .precision import amp_context, ieee_fp32


def batch_layout(config):
    groups = config.get("optimizer_batch_groups", 1)
    forward = config.get("optimizer_forward_groups", 1)
    if any(type(value) is not int or value < 1 for value in (groups, forward)):
        raise ValueError("Optimizer batch/forward groups must be positive integers")
    if groups % forward:
        raise ValueError("Optimizer forward groups must divide optimizer batch groups")
    if groups > 1 and (
        config.get("model", {}).get("restoration_backbone") != "packed-isotropic"
        or not config.get("data_seed_per_step", False)
    ):
        raise ValueError("Grouped batches require packed-isotropic and per-data-step RNG")
    return groups, forward


def optimizer_batches(selected, groups):
    """Collect complete consecutive source batches, including across resumes."""
    pending, previous = [], None
    for item in selected:
        data_step = item[0]
        if previous is not None and data_step != previous + 1:
            raise ValueError("Source data steps must be consecutive")
        if not pending and (data_step - 1) % groups:
            raise ValueError("Source data must start at an optimizer batch boundary")
        previous = data_step
        pending.append(item)
        if len(pending) == groups:
            yield data_step // groups, pending
            pending = []
    if pending:
        raise ValueError("Incomplete optimizer batch")


def backward_groups(model, selected, prepare, config, *, fingerprint=None):
    """Accumulate equal group losses and clip once; caller steps the optimizer.

    `prepare` receives original data step/domain/source values. Forward chunks
    join equally sized groups without combining their targets or loss masks.
    Loss terms are weighted contributions averaged over *all* original groups.
    """
    groups, forward = batch_layout(config)
    if len(selected) != groups or groups < 2:
        raise ValueError("Expected a complete grouped optimizer batch")
    if model.config.restoration_backbone != "packed-isotropic":
        raise ValueError("Grouped forwards require packed-isotropic")
    if any(domain not in ("commons", "native", "paired") for _, domain, _ in selected):
        raise ValueError("Unknown training domain")
    losses, terms, observations = [], defaultdict(list), []
    size = None
    for start in range(0, groups, forward):
        selection = selected[start : start + forward]
        batches = [prepare(*item) for item in selection]
        size = len(batches[0]["packed"]) if size is None else size
        if any(len(batch["packed"]) != size for batch in batches):
            raise ValueError("Source groups must have equal example counts")
        for (data_step, domain, _), batch in zip(selection, batches, strict=True):
            observation = {"data_step": data_step, "domain": domain, "examples": size}
            if fingerprint is not None:
                observation["batch_sha256"] = fingerprint(batch)
            observations.append(observation)
        keys = ["packed", "variance", "colors", "wb", "matrix"]
        inputs = [torch.cat([batch[key] for batch in batches]) for key in keys]
        model.set_noise(
            torch.cat([batch["shot"] for batch in batches]),
            torch.cat([batch["read"] for batch in batches]),
        )
        device = inputs[0].device
        precision = config.get("precision", "bfloat16")
        with amp_context(
            device, config.get("amp", True) or precision == "float32", dtype=precision
        ):
            prediction, auxiliary = model(*inputs, auxiliary=True)
            chunk_losses = []
            for index, ((_, domain, _), batch) in enumerate(zip(selection, batches, strict=True)):
                region = slice(index * size, (index + 1) * size)
                multiscale = config.get("multiscale_sensor_weight", 0.0)
                if domain == "paired":
                    value, parts = paired_reconstruction_loss(
                        prediction[region],
                        batch,
                        auxiliary[region],
                        multiscale_sensor_weight=multiscale,
                        objective=config.get("reconstruction_objective", "charbonnier-v1"),
                    )
                else:
                    value, parts = reconstruction_loss(
                        prediction[region],
                        batch,
                        auxiliary[region],
                        physical_fp32=True,
                        normalized_sensor_weight=config.get("normalized_sensor_weight", 0.0),
                        multiscale_sensor_weight=multiscale,
                        objective=config.get("reconstruction_objective", "charbonnier-v1"),
                        camera_supervision=config.get("camera_supervision", "reference-white-v1"),
                        reference_interval_weight=config.get("reference_interval_weight", 0.0),
                        reconstruction_charbonnier_epsilon=config.get(
                            "reconstruction_charbonnier_epsilon", DEFAULT_RECONSTRUCTION_EPSILON
                        ),
                    )
                if not torch.isfinite(value):
                    raise RuntimeError("Nonfinite group loss; last checkpoint retained")
                chunk_losses.append(value)
                losses.append(value.detach())
                for name, term in parts.items():
                    terms[name].append(term.detach())
            weighted = torch.stack(chunk_losses).sum() / groups
        with ieee_fp32():
            weighted.backward()
        del prediction, auxiliary, chunk_losses, weighted, batches, inputs, value, parts
    with ieee_fp32():
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
    return (
        torch.stack(losses).mean(),
        {name: torch.stack(values).sum() / groups for name, values in terms.items()},
        norm,
        observations,
    )
