"""Compatibility import; implementation lives in demosaic.experiments.objectives.pair_common."""

import sys

from demosaic.experiments.objectives import pair_common as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
