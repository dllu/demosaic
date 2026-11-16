"""Compatibility import; implementation lives in demosaic.experiments.objectives.reconstruction."""

import sys

from demosaic.experiments.objectives import reconstruction as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
