import importlib.util
from pathlib import Path

import pytest
import review_v146_window_transfer as runner


def test_actual_frozen_runner_executes_with_a_quoted_repository_path(tmp_path):
    destination = tmp_path / "researcher's repository"
    source = runner.relocated_controller_source(Path(runner.__file__).read_text(), destination)
    path = tmp_path / "controller.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("relocated_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.REPO == destination
    assert module.BASE == destination / ".cache/quality-20261103/V146-coherent-frequency-v1"
    assert callable(module.controller)


def test_ambiguous_or_missing_root_assignment_is_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        runner.relocated_controller_source("print('missing root')\n", Path("/example"))
