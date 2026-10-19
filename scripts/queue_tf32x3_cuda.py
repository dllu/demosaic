"""Run the frozen precision candidate only after exact quality-work exits.

The waiting controller imports no Torch/Triton/CUDA. The separate worker keeps
its own dependency/accuracy guards. One launch only; no retry or promotion.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': digest}


def alive(owner):
    try:
        process = psutil.Process(owner['pid'])
        return process.create_time() == owner['created'] and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def dependencies_ready(gpu):
    """Detect failed work immediately; require successful exact terminal owners."""
    live = any(alive(owner) for owner in gpu['blocking_owners'])
    for dependency in gpu['completed_dependencies']:
        state = read(dependency['path'])
        if state['controller'] != dependency['controller'] or state['plan'] != dependency['plan']:
            raise ValueError('Dependency owner/plan identity changed')
        if ref(state['plan']['path']) != state['plan']:
            raise ValueError('Dependency plan bytes changed')
        if state['status'].startswith('failed-'):
            raise RuntimeError('Quality dependency failed; no GPU launch or automatic retry')
        if not live and state['status'] != dependency['status']:
            raise RuntimeError('Exited quality owner lacks successful terminal state')
        if not live and state.get('child') and alive(state['child']):
            raise RuntimeError('Dependency child remains live')
    if live:
        return False
    for dependency in gpu.get('required_completed_receipts', []):
        if read(dependency['path'])['status'] != dependency['status']:
            raise RuntimeError('Retained-reference preparation did not complete')
    return True


def guard(plan):
    for item in [plan['controller'], plan['GPU_plan'], *read(plan['GPU_plan']['path'])['inputs']]:
        if ref(item['path']) != item:
            raise ValueError('Frozen precision-candidate input changed: ' + item['path'])


def resource_ready(plan):
    return (
        psutil.virtual_memory().available >= plan['launch_available_gib'] * 2**30
        and shutil.disk_usage(plan['root']).free >= plan['root_reserve_gib'] * 2**30
        and shutil.disk_usage('/mnt/external').free >= plan['external_reserve_gib'] * 2**30
    )


def stop_owned(process, owner):
    """Signal only the exact child started here, then reap it."""
    if alive(owner):
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if alive(owner):
            process.kill()
        process.wait(timeout=10)


def main(plan_path):
    os.nice(10)
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    root = Path(plan['root'])
    if ref(__file__) != plan['controller']:
        raise ValueError('Frozen controller changed')
    guard(plan)
    gpu = read(plan['GPU_plan']['path'])
    if Path(gpu['output']).exists():
        raise ValueError('GPU output already exists; choose a separately reviewed recovery')
    with (root / 'controller.claim').open('x') as stream:
        stream.write(str(os.getpid()))
    status_path = root / 'status.json'
    owner = {'pid': os.getpid(), 'created': psutil.Process().create_time()}
    info = {'controller': owner, 'plan': ref(plan_path), 'GPU_plan': plan['GPU_plan']}

    def record(status, **fields):
        info.update(status=status, updated_unix=time.time(), **fields)
        temporary = status_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + '\n')
        temporary.replace(status_path)

    record('waiting-for-exact-training-review-closure-and-reference-exits-no-Torch-or-CUDA')
    try:
        started = time.monotonic()
        while not dependencies_ready(gpu):
            if time.monotonic() - started > plan['dependency_timeout_seconds']:
                raise TimeoutError('Quality dependency wait expired; no automatic retry')
            time.sleep(plan['poll_seconds'])
        guard(plan)
        record('waiting-for-stable-memory-and-disk-no-Torch-or-CUDA')
        started, stable = time.monotonic(), None
        while True:
            now = time.monotonic()
            if now - started > plan['resource_timeout_seconds']:
                raise TimeoutError('Resource wait expired; no automatic retry')
            if resource_ready(plan):
                stable = now if stable is None else stable
                if now - stable >= plan['stable_seconds']:
                    break
            else:
                stable = None
            time.sleep(plan['poll_seconds'])
        assert dependencies_ready(gpu)
        guard(plan)
        env = dict(os.environ, **plan['worker_env'])
        with (root / 'GPU-worker.log').open('xb') as log:
            process = subprocess.Popen(
                [gpu['python'], '-P', gpu['worker']['path'], plan['GPU_plan']['path']],
                cwd=gpu['work'], env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            child = {'pid': process.pid, 'created': psutil.Process(process.pid).create_time()}
            record('running-frozen-CUDA-array-gates-then-conditional-resident-timing', child=child)
            started = time.monotonic()
            try:
                while process.poll() is None:
                    if time.monotonic() - started > plan['worker_timeout_seconds']:
                        raise TimeoutError('CUDA preflight runtime bound exceeded')
                    if psutil.virtual_memory().available < plan['active_available_gib'] * 2**30:
                        raise MemoryError('Shared available-memory guard reached')
                    if shutil.disk_usage('/mnt/external').free < plan['external_reserve_gib'] * 2**30:
                        raise OSError('External disk reserve reached')
                    time.sleep(2)
            except BaseException:
                stop_owned(process, child)
                raise
            if process.returncode != 0 or alive(child):
                raise RuntimeError('Frozen GPU worker failed; no automatic retry')
        guard(plan)
        terminal = read(Path(gpu['output']) / 'status.json')
        if terminal['owner'] != child:
            raise ValueError('GPU terminal owner differs from exact launched child')
        if terminal['status'] == 'rejected-CUDA-RGB-accuracy-no-timing-or-fullframe':
            record('rejected-CUDA-array-gate-no-timing-or-fullframe-awaiting-native-inspection',
                   GPU_terminal=ref(Path(gpu['output']) / 'status.json'))
            return
        expected = 'completed-isolated-TF32x3-CUDA-array-gates-and-resident-timing-awaiting-native-review'
        if terminal['status'] != expected or ref(terminal['receipt']['path']) != terminal['receipt']:
            raise ValueError('GPU worker has no verified completed receipt')
        result = read(terminal['receipt']['path'])
        if result['plan'] != plan['GPU_plan'] or result['owner'] != child:
            raise ValueError('Completed precision-candidate lineage changed')
        record('completed-CUDA-numerics-and-resident-timing-awaiting-independent-array-and-native-review',
               GPU_receipt=terminal['receipt'])
    except BaseException as error:
        record('failed-precision-candidate-queue-no-automatic-retry', error=repr(error))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    main(parser.parse_args().plan)
