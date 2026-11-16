"""Compatibility import; implementation lives in demosaic.experiments.data.shared_edge."""

import sys

from demosaic.experiments.data import shared_edge as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
