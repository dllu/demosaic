"""Fetch pinned NLFeMF comparison weights and compile its inference sampler.

Use with the optional ``nonlocal`` extra. Downloads and compiler caches remain
inside the project or /mnt/external. Existing verified bytes are adopted.
"""

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import tarfile
import typing
import urllib.request

REPO = Path(__file__).resolve().parents[1]
RELEASE = "https://github.com/MIA-UIB/nonlocal-matchfilter/releases/download/v1.0.0/"
WEIGHTS_HASH = "b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2"
ARCHIVE_HASH = "afdd8279771b93ba409fbddc0aaae1e555b8607d3d06dd316b7628a92aaeaa9e"
DEFORM_COMMIT = "ba6c21d34effcb3c3903237704ab58388b86d006"
DEFORM_BLOBS = {
    "LICENSE": "d5c351c4a18ab2e4662ee85ebb0b55b92a07002e",
    "deform_neighbourhood_sampling/csrc/cpu/deform_nbrhd_kernel.cpp": "45f6be195bb0bef518e31fc6d7389ac633277246",
    "deform_neighbourhood_sampling/csrc/cuda/deform_nbrhd_kernel.cu": "7cfbea6ca72c357ed7e5532683542f05dbee0d14",
    "deform_neighbourhood_sampling/csrc/deform_nbrhd.cpp": "8c83e054af3eac836cc56bc5d7bf5c8c4ec75ecb",
    "deform_neighbourhood_sampling/csrc/deform_nbrhd.h": "3c7984bb316f2e4ea1500c6d24a92ecd583888f6",
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reference(path):
    return {"path": str(Path(path).absolute()), "sha256": digest(path)}


def download(url, path, expected=None):
    path = Path(path)
    if not path.exists():
        partial = path.with_suffix(path.suffix + ".part")
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("xb") as output:
            while block := response.read(4 * 1024 * 1024):
                output.write(block)
        partial.rename(path)
    if expected is not None and digest(path) != expected:
        raise ValueError(f"Downloaded bytes differ: {path}")
    return reference(path)


def extract_weights(source, target):
    """Restricted tensor load; inert objects stand in for unused config metadata."""
    import torch

    if digest(source) != WEIGHTS_HASH:
        raise ValueError("Checkpoint differs from the published release digest")
    names = ["omegaconf.nodes.AnyNode", "omegaconf.base.ContainerMetadata",
             "omegaconf.listconfig.ListConfig", "omegaconf.base.Metadata"]
    globals_expected = set(names + ["builtins.dict", "builtins.list", "builtins.int",
                                   "collections.defaultdict", "typing.Any"])
    if set(torch.serialization.get_unsafe_globals_in_checkpoint(source)) != globals_expected:
        raise ValueError("Unexpected checkpoint metadata globals")
    inert = [(type(name.rsplit(".", 1)[1], (), {}), name) for name in names]
    with torch.serialization.safe_globals(inert + [dict, list, int, collections.defaultdict, typing.Any]):
        checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    state = {key.removeprefix("model."): value for key, value in checkpoint["state_dict"].items()
             if key.startswith("model.")}
    if len(state) != 141 or sum(value.numel() for value in state.values()) != 15_282_866:
        raise ValueError("Unexpected released network shape")
    if not all(isinstance(value, torch.Tensor) and torch.isfinite(value).all() for value in state.values()):
        raise ValueError("Invalid weight tensors")
    if target.exists():
        adopted = torch.load(target, map_location="cpu", weights_only=True)
        assert adopted["source_sha256"] == WEIGHTS_HASH and adopted["state_dict"].keys() == state.keys()
        assert all(torch.equal(value, adopted["state_dict"][key]) for key, value in state.items())
    else:
        with target.open("xb") as stream:
            torch.save({"state_dict": state, "source_sha256": WEIGHTS_HASH}, stream)
    return reference(target)


def fetch(root, weights, build=True):
    import torch

    root, weights = root.resolve(), weights.resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert weights.is_relative_to(Path("/mnt/external/demosaic")) or weights.is_relative_to(REPO)
    upstream = root / "upstream"
    upstream.mkdir(parents=True, exist_ok=True)
    weights.mkdir(parents=True, exist_ok=True)
    archive = upstream / "nonlocal_matchfilter-1.0.0.tar.gz"
    source_record = download(RELEASE + archive.name, archive, ARCHIVE_HASH)
    source = upstream / "source"
    if not source.exists():
        source.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter="data")
    checkpoint = weights / "rawnoise_25_15_9nbr.ckpt"
    weight_record = download(RELEASE + checkpoint.name, checkpoint, WEIGHTS_HASH)
    extracted = extract_weights(checkpoint, weights / "rawnoise-25-15-9-tensors-v1.pt")
    deform_archive = upstream / "deform-neighbourhood-v0.1.1.tar.gz"
    deform_record = download("https://codeload.github.com/MIA-UIB/deform-neighbourhood-sampling/tar.gz/" + DEFORM_COMMIT, deform_archive)
    deform_source = upstream / "deform-source"
    if not deform_source.exists():
        deform_source.mkdir()
        with tarfile.open(deform_archive) as stream:
            stream.extractall(deform_source, filter="data")
    tree = next(deform_source.glob("deform-neighbourhood-sampling-*"))
    blobs = {}
    for name, expected in DEFORM_BLOBS.items():
        path = tree / name
        data = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise ValueError(f"Pinned sampler source differs: {name}")
        blobs[name] = dict(reference(path), git_blob=actual)
    library = None
    if build:
        previous = root / "deform-build-v1.json"
        if previous.exists():
            prior = json.loads(previous.read_text())
            assert prior["Torch"] == torch.__version__ and prior["Torch_CUDA"] == torch.version.cuda
            assert reference(prior["library"]["path"]) == prior["library"]
            library = prior["library"]
        else:
            from torch.utils.cpp_extension import load

            directory = root / "compiled-deform-v1"
            directory.mkdir(exist_ok=False)
            os.environ["MAX_JOBS"] = "2"
            os.environ["TORCH_CUDA_ARCH_LIST"] = "12.1"
            csrc = tree / "deform_neighbourhood_sampling/csrc"
            module = load(name="v170_deform", sources=[str(csrc / name) for name in [
                "deform_nbrhd.cpp", "cpu/deform_nbrhd_kernel.cpp", "cuda/deform_nbrhd_kernel.cu"]],
                build_directory=str(directory), with_cuda=True, extra_cflags=["-O2"], extra_cuda_cflags=["-O2"], verbose=True)
            library = reference(module.__file__)
            previous.write_text(json.dumps(dict(Torch=torch.__version__, Torch_CUDA=torch.version.cuda, library=library), indent=2) + "\n")
    receipt = root / "fetch-adoption-v1.json"
    result = dict(status="verified-pinned-release-sources-weights-and-native-library", source_archive=source_record,
                  original_weights=weight_record, tensor_weights=extracted, deform_archive=deform_record,
                  pinned_sampler_blobs=blobs, library=library, new_neural_forwards=0,
                  fetcher=dict(reference(__file__), text=Path(__file__).read_text()))
    if not receipt.exists():
        receipt.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO / ".cache/nonlocal-matchfilter-v1")
    parser.add_argument("--weights", type=Path, default=Path("/mnt/external/demosaic/models/nonlocal-matchfilter-v1"))
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    result = fetch(args.root, args.weights, not args.no_build)
    print("Verified release weights and pinned sources; library:", result["library"])
