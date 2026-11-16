"""Compatibility import; implementation lives in demosaic.experiments.objectives.local_regret."""

import sys

from demosaic.experiments.objectives import local_regret as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
