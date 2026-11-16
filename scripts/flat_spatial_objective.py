"""Compatibility import; implementation lives in demosaic.experiments.objectives.flat_spatial."""

import sys

from demosaic.experiments.objectives import flat_spatial as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
