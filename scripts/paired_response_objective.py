"""Compatibility import; implementation lives in demosaic.experiments.objectives.pair_difference."""

import sys

from demosaic.experiments.objectives import pair_difference as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
