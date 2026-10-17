"""Inspect signed RawForge JDD exports and make an explicit CPU device-only port."""

import argparse
import ast
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import sha

from demosaic.safety import writable_path

ASSETS = {
    "JDD256": (
        "DemoRestormerDiT_to_demo_cont.pt",
        "e3ab1b52c14e10d77fbe41c4b3530de69d533be335c2f390c26f2de1650393fc",
    ),
    "JDD": (
        "DemoRestormerDiT_to_demo_cont_cont_768_RawNIND.pt",
        "77b9e403b4feb4579cf1eb677c7d8098cf2725dd6e433414ea8fc333e426d7dc",
    ),
}


def read(path):
    return json.loads(Path(path).read_text())


def devices(model):
    for name, module in model.named_modules():
        for method in module._c._method_names():
            graph = module._c._get_method(method).graph
            for node in graph.findAllNodes("prim::Constant", True):
                value = node.output().toIValue()
                if isinstance(value, torch.device):
                    yield name, method, graph, node, str(value)


def fixture():
    pattern = np.array([[0, 1], [1, 2]])
    colors = np.tile(pattern, (32, 40))
    rgb = np.array([0.2, 0.4, 0.1], dtype=np.float32)
    mask = colors[None] == np.arange(3)[:, None, None]
    sparse = mask * rgb[:, None, None]
    # Preserve the publisher's actual F16 input quantization, then use F32
    # arithmetic on CPU. This is distinct from its CUDA FP16 autocast backend.
    return torch.from_numpy(np.concatenate([sparse, mask], axis=0)[None].astype(np.float16)).float()


@torch.inference_mode()
def main(root, output):
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    output = writable_path(output)
    if output.exists():
        raise ValueError("CPU inspection exists; choose a new output")
    source = root / "source"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    assert commit == "79f17700c29765b28a4cf5bd1b6d90bc7e3eb7f2"
    registry_path = source / "RawForge/application/MODEL_REGISTRY.py"
    registry = ast.literal_eval(ast.parse(registry_path.read_text()).body[0].value)
    handler = source / "RawForge/application/ModelHandlerTorch.py"
    key = next(
        ast.literal_eval(n.value)
        for n in ast.parse(handler.read_text()).body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "key_string" for t in n.targets)
    )
    public = root / "publisher-model-signing-public.pem"
    assert public.read_text() == key
    release = read(root / "JDD-release.json")
    assets = {a["name"]: a for a in release["assets"]}
    inspected = []
    output.mkdir(parents=True, exist_ok=False)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    for name, (filename, digest) in ASSETS.items():
        path = root / "weights" / filename
        assert sha(path) == digest and assets[filename]["digest"] == "sha256:" + digest
        signature = path.with_suffix(".pt.sig")
        assert sha(signature) == assets[signature.name]["digest"].split(":", 1)[1]
        verification = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                str(public),
                "-signature",
                str(signature),
                "-sigopt",
                "rsa_padding_mode:pss",
                "-sigopt",
                "rsa_pss_saltlen:auto",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert verification.stdout.strip() == "Verified OK"
        model = torch.jit.load(str(path), map_location="cpu").eval()
        assert len(list(model.parameters())) == 163
        assert sum(v.numel() for v in model.parameters()) == 11319924
        state = {k: v.clone() for k, v in model.state_dict().items()}
        assert all(torch.isfinite(v).all() for v in state.values())
        assert all(v.dtype == torch.float32 for v in state.values())
        expected_cpu_failure = None
        try:
            model(fixture().half())
        except RuntimeError as error:
            expected_cpu_failure = str(error)
        assert (
            expected_cpu_failure
            and "half" in expected_cpu_failure.lower()
            and "float" in expected_cpu_failure.lower()
        )
        assert not torch.cuda.is_initialized()
        # Reload before touching any graph: a failed first call can populate
        # executor caches, so rewrite before executing the port at all.
        del model
        model = torch.jit.load(str(path), map_location="cpu").eval()
        changes = []
        for module_name, method, graph, node, device in list(devices(model)):
            assert (
                device == "cuda:0"
                and module_name == "middle_blks.0.rope_gen"
                and method == "forward"
            )
            before = str(graph)
            node.s_("value", "cpu")
            after = str(graph)
            assert after == before.replace("cuda:0", "cpu")
            changes.append(
                {
                    "module": module_name,
                    "method": method,
                    "from": device,
                    "to": "cpu",
                    "one_shared_Device_constant_only": True,
                }
            )
        assert len(changes) == 1 and all(device == "cpu" for *_, device in devices(model))
        port = output / (name + "-CPU-device-only.pt")
        torch.jit.save(model, str(port))
        del model
        ported = torch.jit.load(str(port), map_location="cpu").eval()
        assert state.keys() == ported.state_dict().keys()
        assert all(torch.equal(v, ported.state_dict()[k]) for k, v in state.items())
        x = fixture()
        y = ported(x)
        assert y.shape == (1, 3, 64, 80) and y.dtype == torch.float32 and torch.isfinite(y).all()
        repeated = ported(x)
        delta = float((y - repeated).abs().max())
        assert delta < 1e-6
        np.save(output / (name + "-fixture-input-f32.npy"), x.numpy(), allow_pickle=False)
        np.save(output / (name + "-fixture-output-f32.npy"), y.numpy(), allow_pickle=False)
        inspected.append(
            {
                "name": name,
                "original": str(path),
                "original_sha256": digest,
                "publisher_RSA_PSS_SHA256_signature_verified": True,
                "registry": registry[name],
                "parameters": 11319924,
                "parameter_tensors": 163,
                "all_state_tensors_exact": len(state),
                "all_state_tensors_finite_F32": True,
                "CPU_port": str(port),
                "CPU_port_sha256": sha(port),
                "device_graph_changes": changes,
                "all_tensor_values_and_shapes_exact_after_save_reload": True,
                "original_backend_F16_CPU_failure": expected_cpu_failure,
                "ported_F32_fixture_output_shape": list(y.shape),
                "ported_F32_fixture_output_minmax": [float(y.min()), float(y.max())],
                "repeat_max_abs_difference": delta,
            }
        )
        print(
            json.dumps({"model": name, "state_tensors": len(state), "CPU_fixture_finite": True}),
            flush=True,
        )
        del ported, state
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-signed-RAWForge-JDD-export-inspection-and-explicit-CPU-port",
        "source": str(source),
        "source_commit": commit,
        "code_license": "MIT, retained in downloaded source",
        "release": str(root / "JDD-release.json"),
        "release_sha256": sha(root / "JDD-release.json"),
        "source_files": {
            str(p): sha(p)
            for p in [
                registry_path,
                handler,
                source / "LICENSE",
                source / "RawForge/application/TorchBackend.py",
                source / "RawForge/application/helpers/get_image.py",
                source / "RawForge/main.py",
            ]
        },
        "models": inspected,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Publisher signatures and GitHub asset digests verified before load. Original TorchScript has a hardcoded CUDA device in positional coordinates and F32 parameters; its CPU backend passes F16 input and fails. Explicit CPU adaptation uses F16-rounded input expanded to F32 and rewrites one shared Device constant, without changing any weights or other graph text. Genuine original-CUDA versus CPU-port prediction parity remains untested until the owned GPU workflows finish. No trained quality or speed claim; release notes do not separately identify a weight license or exact training membership, so weights remain an optional local research comparison, not bundled into the project.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.root, a.output)
