"""Verify saved diagnostic replay and relevance to actual frozen training code."""

import argparse
import ast
import os
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save


def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def same(first, second):
    return ast.dump(first, include_attributes=False) == ast.dump(second, include_attributes=False)


def main(first_root, root, training_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    first_receipt, receipt = (read(p / "receipt.json") for p in [first_root, root])
    archive_path = root / "source-archive.json"
    archive = read(archive_path)
    for item in [
        archive["first_driver"],
        archive["final_driver"],
        archive["equivalent_frozen_model_package"],
        *archive["equivalent_frozen_physics_sources"],
    ]:
        assert ref(item["path"]) == item
    assert archive["first_driver"]["sha256"] == first_receipt["driver"]["sha256"]
    assert archive["final_driver"]["sha256"] == receipt["driver"]["sha256"]
    assert {
        Path(i["path"]).name: i["sha256"] for i in archive["equivalent_frozen_physics_sources"]
    } == {Path(i["path"]).name: i["sha256"] for i in receipt["sources"]}
    assert (
        receipt["status"]
        == first_receipt["status"]
        == ("completed-CPU-stabilized-noise-proxy-moment-and-covariance-diagnostic")
    )
    for value in [first_receipt, receipt]:
        assert value["all_moment_and_covariance_checks_passed"]
        assert value["moment_cases"] == 24 and value["CUDA_initialized"] is False
        for field in ["moment_rows", "covariance_arrays", "plot", "plot_PDF"]:
            assert ref(value[field]["path"]) == value[field]
    assert first_receipt["moment_rows"]["sha256"] == receipt["moment_rows"]["sha256"]
    with (
        np.load(first_receipt["covariance_arrays"]["path"], allow_pickle=False) as first,
        np.load(receipt["covariance_arrays"]["path"], allow_pickle=False) as second,
    ):
        assert first.files == second.files and len(first.files) == 12
        for key in first.files:
            assert first[key].shape == second[key].shape and first[key].dtype == second[key].dtype
            assert first[key].tobytes(order="C") == second[key].tobytes(order="C")
    assert first_receipt["unit_Gaussian_CFA_covariance"] == receipt["unit_Gaussian_CFA_covariance"]
    assert (
        first_receipt["protocol_level_flat_unclipped_checks"]
        == receipt["protocol_level_flat_unclipped_checks"]
    )
    training = read(training_path)
    old = Path(training["work"]) / "src/demosaic"
    current = Path("src/demosaic").resolve()
    for item in receipt["sources"]:
        assert ref(item["path"]) == item
    trees = [ast.parse((p / "vst.py").read_text()) for p in [old, current]]
    for name in ["expectation_grid", "expectation_table"]:
        assert same(*(function(t, name) for t in trees))
    classes = [
        next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == "GeneralizedAnscombe")
        for t in trees
    ]
    for name in ["__init__", "forward"]:
        assert same(*(function(t, name) for t in classes))
    assert ref(old / "cfa.py")["sha256"] == ref(current / "cfa.py")["sha256"]
    prefixes = []
    for directory in [old, current]:
        f = function(
            ast.parse((directory / "pretrained_rgb.py").read_text()), "physical_rgb_features"
        )
        block = next(n for n in f.body if isinstance(n, ast.With))
        nodes = []
        for node in block.body:
            nodes.append(node)
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "camera" for t in node.targets
            ):
                break
        assert isinstance(nodes[-1], ast.Assign)
        assert any(isinstance(t, ast.Name) and t.id == "camera" for t in nodes[-1].targets)
        prefixes.append(ast.Module(body=nodes, type_ignores=[]))
    assert same(*prefixes)
    result = {
        "status": "verified-numerical-replay-and-active-archived-noise-source-compatibility",
        "driver": ref(__file__),
        "first_run": ref(first_root / "receipt.json"),
        "final_plot_run": ref(root / "receipt.json"),
        "training_plan": ref(training_path),
        "executed_source_archive": ref(archive_path),
        "all24_moment_rows_and_all12_covariance_arrays_bytes_exact": True,
        "GAT_constructor_forward_and_expectation_AST_exact_actual_training_source": True,
        "CFA_module_bytes_exact_actual_training_source": True,
        "physical_feature_noise_span_normalization_prefix_AST_exact_actual_training_source": True,
        "actual_archived_sources": [
            ref(old / n) for n in ["vst.py", "cfa.py", "pretrained_rgb.py"]
        ],
        "scope": "CPU static source and saved-array replay only. V2 changes plot axes/legend only. No model/data/default/training/GPU change or causal quality claim.",
    }
    save(output, result)
    print({"audit": ref(output)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ["first-root", "root", "training-plan", "output"]:
        parser.add_argument("--" + argument, type=Path, required=True)
    args = parser.parse_args()
    main(
        args.first_root.resolve(),
        args.root.resolve(),
        args.training_plan.resolve(),
        args.output.resolve(),
    )
