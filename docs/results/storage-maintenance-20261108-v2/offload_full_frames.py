"""One-time, hash-verified relocation of inactive full-frame render evidence."""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import numpy as np
import tifffile

REPO = Path('/home/dllu/proj/demosaic')
sys.path.insert(0, str(REPO / 'scripts'))
import compact_historical_cache as core

ROOT = Path(__file__).resolve().parent
DEST = Path('/mnt/external/demosaic/cold-full-frame-20261108-v1')
SOURCES = [REPO / '.cache' / name for name in
           ['current-quality-20261023-v1', 'quality-20261102', 'quality-20261103']]


def ref(path):
    return {'path': str(Path(path).absolute()), 'sha256': core.sha(path)}


def reader(path):
    if path.suffix == '.npy':
        a = np.load(path, mmap_mode='r', allow_pickle=False)
    else:
        a = tifffile.memmap(path, mode='r')
    v = a.reshape(-1)
    sample = np.concatenate([v[:16], v[len(v)//2:len(v)//2+16], v[-16:]]).tobytes()
    return {'shape': list(a.shape), 'dtype': a.dtype.str,
            'sample_sha256': hashlib.sha256(sample).hexdigest()}


def plan():
    assert not DEST.exists()
    core.assert_inactive(SOURCES)
    by_inode = {}
    for root in SOURCES:
        for directory, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [n for n in dirs if not Path(directory, n).is_symlink()]
            for name in names:
                path = Path(directory, name)
                s = path.lstat()
                if (path.suffix not in {'.npy', '.tiff'} or not stat.S_ISREG(s.st_mode)
                        or s.st_size < 200 * 2**20 or s.st_mtime > time.time() - 2*86400):
                    continue
                key = s.st_dev, s.st_ino
                by_inode.setdefault(key, {'identity': core.identity(path), 'paths': []})['paths'].append(str(path))
    groups = [g for g in by_inode.values() if len(g['paths']) == g['identity']['nlink']]
    for i, group in enumerate(groups):
        p = Path(group['paths'][0])
        group['sha256'] = core.sha(p)
        group['reader'] = reader(p)
        group['destination'] = str(DEST / p.relative_to(REPO))
        assert core.identity(p) == group['identity']
        if i % 10 == 0:
            print(json.dumps({'hashed_files': i+1, 'total': len(groups)}), flush=True)
    core.save(ROOT / 'offload-plan-v1.json.gz', {
        'status': 'hashed-inactive-full-frame-offload-plan', 'driver': ref(__file__),
        'engine': ref(core.__file__), 'created_local': core.local_now(),
        'roots': list(map(str, SOURCES)), 'destination_root': str(DEST), 'groups': groups,
        'allocated_bytes': sum(g['identity']['blocks']*512 for g in groups),
        'note': 'Preserve every file byte and original path via individual file symlinks. '
                'No directory, source code, receipt, checkpoint, native crop, original photo or protected GFX cache moves. '
                'Path.resolve() now returns the recorded external path; use this relocation map when validating old literal path bindings.'})


def apply():
    plan_path = ROOT / 'offload-plan-v1.json.gz'
    data = core.read(plan_path)
    assert data['driver'] == ref(__file__) and data['engine'] == ref(core.__file__)
    assert not DEST.exists() and not (ROOT / 'offload-claim').exists()
    paths = {p for g in data['groups'] for p in g['paths']}
    core.assert_inactive(SOURCES, paths)
    assert shutil.disk_usage(DEST.parent).free >= data['allocated_bytes'] + 150 * 2**30
    for g in data['groups']:
        for name in g['paths']:
            p = Path(name)
            assert p.resolve() == p and any(p.is_relative_to(r) for r in SOURCES)
            assert core.identity(p) == g['identity']
    (ROOT / 'offload-claim').write_text(str(os.getpid()))
    before = {'local': shutil.disk_usage(REPO).free, 'external': shutil.disk_usage(DEST.parent).free}
    DEST.mkdir()
    with (ROOT / 'offload-applied-v1.jsonl').open('x') as journal:
        for i, g in enumerate(data['groups']):
            source = Path(g['paths'][0])
            assert core.sha(source) == g['sha256']
            destination = Path(g['destination'])
            assert destination.is_relative_to(DEST)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + '.partial')
            shutil.copy2(source, temporary)
            assert core.sha(temporary) == g['sha256']
            # The temporary name has no .npy suffix; use the final suffix for the reader.
            temporary.rename(destination)
            assert reader(destination) == g['reader']
            destination.chmod(g['identity']['mode'] & 0o777 & ~0o222)
            with destination.open('rb') as stream:
                os.fsync(stream.fileno())
            journal.write(json.dumps({'group': i, 'sha256': g['sha256'],
                                      'destination': str(destination), 'paths': g['paths']}) + '\n')
            journal.flush()
            os.fsync(journal.fileno())
            for ordinal, name in enumerate(g['paths']):
                p = Path(name)
                actual = core.identity(p)
                for k, value in g['identity'].items():
                    if k != 'ctime_ns':
                        assert actual[k] == (value - ordinal if k == 'nlink' else value)
                link = p.with_name(p.name + '.offload-link')
                assert not link.exists() and not link.is_symlink()
                link.symlink_to(destination)
                os.replace(link, p)
                assert p.resolve() == destination and reader(p) == g['reader']
            assert core.sha(source) == g['sha256']
            print(json.dumps({'offloaded_groups': i+1, 'total': len(data['groups'])}), flush=True)
    core.save(ROOT / 'offload-result-v1.json', {
        'status': 'verified-inactive-full-frame-offload-completed', 'created_local': core.local_now(),
        'plan': ref(plan_path), 'journal': ref(ROOT / 'offload-applied-v1.jsonl'),
        'groups': len(data['groups']), 'paths_preserved': len(paths),
        'allocated_local_bytes_reclaimed': data['allocated_bytes'],
        'all_destination_hashes_and_original_path_readers_verified': True,
        'free_before': before, 'free_after': {'local': shutil.disk_usage(REPO).free,
                                             'external': shutil.disk_usage(DEST).free}})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['plan', 'apply'])
    args = parser.parse_args()
    globals()[args.action]()
