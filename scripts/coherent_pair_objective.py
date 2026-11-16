"""Compatibility import; implementation lives in demosaic.experiments.objectives.coherent."""

import sys

from demosaic.experiments.objectives import coherent as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
