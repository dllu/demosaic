import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import psutil
import pytest

path = Path(__file__).parents[1] / 'scripts/queue_tf32x3_cuda.py'
spec = importlib.util.spec_from_file_location('tf32x3_queue', path)
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


@pytest.fixture
def dependencies(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, 'alive', lambda owner: owner.get('live', False))
    plan = tmp_path / 'upstream-plan.json'
    plan.write_text('{}\n')
    owner = {'pid': 123, 'created': 456.}
    status = tmp_path / 'status.json'
    state = {'controller': owner, 'plan': queue.ref(plan), 'status': 'running-quality'}
    status.write_text(json.dumps(state))
    gpu = {'blocking_owners': [{'live': True}], 'completed_dependencies': [
        {'path': str(status), 'controller': owner, 'plan': queue.ref(plan), 'status': 'completed-quality'}
    ], 'required_completed_receipts': []}
    return gpu, status, state, plan


def test_live_quality_owner_waits_without_reading_uncreated_reference(dependencies):
    gpu, _, _, _ = dependencies
    gpu['required_completed_receipts'] = [{'path': '/does-not-exist'}]
    assert queue.dependencies_ready(gpu) is False


@pytest.mark.parametrize('change', ['failure', 'owner', 'plan_bytes', 'exited_incomplete', 'live_child'])
def test_failed_changed_or_unfinished_quality_prevents_launch(dependencies, change):
    gpu, path, state, plan = dependencies
    if change == 'failure':
        state['status'] = 'failed-upstream'
    elif change == 'owner':
        state['controller'] = {'pid': 124, 'created': 456.}
    elif change == 'plan_bytes':
        plan.write_text('{"changed":true}\n')
    elif change == 'exited_incomplete':
        gpu['blocking_owners'] = []
    else:
        gpu['blocking_owners'] = []
        state.update(status='completed-quality', child={'live': True})
    path.write_text(json.dumps(state))
    with pytest.raises((RuntimeError, ValueError)):
        queue.dependencies_ready(gpu)


def test_completed_exact_owners_and_reference_receipts_are_required(dependencies, tmp_path):
    gpu, path, state, _ = dependencies
    gpu['blocking_owners'] = []
    state['status'] = 'completed-quality'
    path.write_text(json.dumps(state))
    reference = tmp_path / 'reference.json'
    reference.write_text(json.dumps({'status': 'prepared-refs'}))
    gpu['required_completed_receipts'] = [{'path': str(reference), 'status': 'prepared-refs'}]
    assert queue.dependencies_ready(gpu)
    reference.write_text(json.dumps({'status': 'failed-refs'}))
    with pytest.raises(RuntimeError, match='reference'):
        queue.dependencies_ready(gpu)


def test_actual_own_pid_identity_and_controller_has_no_torch_import():
    owner = {'pid': os.getpid(), 'created': psutil.Process().create_time()}
    assert queue.alive(owner)
    assert not queue.alive({**owner, 'created': owner['created'] - 1})
    # This queue is imported in a process which may already import Torch in
    # other tests; inspect imports of its own source, not global sys.modules.
    import ast
    tree = ast.parse(path.read_text())
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all(not (getattr(node, 'module', '') or '').startswith(('torch', 'triton')) for node in imports)
    assert all(not alias.name.startswith(('torch', 'triton')) for node in imports if isinstance(node, ast.Import) for alias in node.names)
    assert 'torch' not in queue.__dict__ and 'triton' not in queue.__dict__


def test_frozen_controller_or_worker_input_mutations_are_rejected(tmp_path):
    controller, worker, gpu_path = [tmp_path / name for name in ['controller.py', 'worker.py', 'gpu.json']]
    controller.write_text('# controller\n')
    worker.write_text('# worker\n')
    gpu_path.write_text(json.dumps({'inputs': [queue.ref(worker)]}))
    plan = {'controller': queue.ref(controller), 'GPU_plan': queue.ref(gpu_path)}
    queue.guard(plan)
    worker.write_text('# changed worker\n')
    with pytest.raises(ValueError, match='input changed'):
        queue.guard(plan)


def test_only_exact_created_child_is_stopped_and_reaped():
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    owner = {'pid': process.pid, 'created': psutil.Process(process.pid).create_time()}
    try:
        assert queue.alive(owner)
        queue.stop_owned(process, owner)
        assert process.poll() is not None and not queue.alive(owner)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
