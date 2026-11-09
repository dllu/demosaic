import importlib.util
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import tifffile

spec = importlib.util.spec_from_file_location('offloader', Path(__file__).with_name('offload_full_frames.py'))
offloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offloader)


def setup(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    op = tmp_path / 'operation'
    op.mkdir()
    destination = tmp_path / 'external'
    monkeypatch.setattr(offloader, 'ROOT', op)
    monkeypatch.setattr(offloader, 'DEST', destination)
    monkeypatch.setattr(offloader, 'SOURCES', [source])
    usage = shutil._ntuple_diskusage(700*2**30, 300*2**30, 400*2**30)
    monkeypatch.setattr(offloader.shutil, 'disk_usage', lambda p: usage)
    a = np.arange(192, dtype=np.uint16).reshape(8, 8, 3)
    np.save(source / 'prediction.npy', a)
    os.link(source / 'prediction.npy', source / 'prediction-alias.npy')
    tifffile.imwrite(source / 'render.tiff', a)
    groups = []
    for name, aliases in [('prediction.npy', ['prediction.npy', 'prediction-alias.npy']),
                          ('render.tiff', ['render.tiff'])]:
        p = source / name
        groups.append({'paths': [str(source / n) for n in aliases],
                       'identity': offloader.core.identity(p),
                       'destination': str(destination / name),
                       'sha256': offloader.core.sha(p), 'reader': offloader.reader(p)})
    offloader.core.save(op / 'offload-plan-v1.json.gz', {
        'driver': offloader.ref(offloader.__file__), 'engine': offloader.ref(offloader.core.__file__),
        'groups': groups, 'allocated_bytes': sum(g['identity']['blocks']*512 for g in groups)})
    return source, op, destination, groups


def test_all_aliases_bytes_and_real_image_readers_survive_offload(tmp_path, monkeypatch):
    source, op, destination, groups = setup(tmp_path, monkeypatch)
    offloader.apply()
    assert offloader.core.read(op / 'offload-result-v1.json')['paths_preserved'] == 3
    for group in groups:
        for name in group['paths']:
            p = Path(name)
            assert p.is_symlink() and p.resolve() == Path(group['destination'])
            assert offloader.core.sha(p) == group['sha256']
            assert offloader.reader(p) == group['reader']


def test_copy_failure_preserves_all_originals(tmp_path, monkeypatch):
    source, op, destination, groups = setup(tmp_path, monkeypatch)
    before = {p: offloader.core.identity(p) for p in source.iterdir()}

    def fail(*a, **kw):
        raise OSError('injected copy failure')

    monkeypatch.setattr(offloader.shutil, 'copy2', fail)
    with pytest.raises(OSError, match='injected copy'):
        offloader.apply()
    assert {p: offloader.core.identity(p) for p in source.iterdir()} == before
    assert not (op / 'offload-result-v1.json').exists()


def test_changed_original_is_rejected_before_any_relocation(tmp_path, monkeypatch):
    source, op, destination, groups = setup(tmp_path, monkeypatch)
    (source / 'render.tiff').write_bytes(b'changed after hashing')
    with pytest.raises(AssertionError):
        offloader.apply()
    assert not destination.exists()
    assert not any(p.is_symlink() for p in source.iterdir())
