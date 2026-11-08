"""Future spatial-trial receipts may use lossless gzip to retain full evidence."""

import gzip
import json
from pathlib import Path

from phase_admission_protocol import owner_live, ref  # noqa: F401


def open_text(path, mode='rt'):
    path = Path(path)
    if path.suffix == '.gz':
        return gzip.open(path, mode, encoding='utf-8', compresslevel=6)
    return path.open(mode.replace('t', ''), encoding='utf-8')


def read(path):
    with open_text(path) as stream:
        return json.load(stream)


def save(path, value):
    with open_text(path, 'xt') as stream:
        json.dump(value, stream, separators=(',', ':'), allow_nan=False)
        stream.write('\n')
