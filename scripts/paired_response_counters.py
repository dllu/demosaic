"""Compatibility import; implementation lives in demosaic.experiments.data.counters."""

import sys

from demosaic.experiments.data import counters as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
