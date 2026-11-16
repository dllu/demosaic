"""Compatibility import; implementation lives in demosaic.experiments.evaluation.detail."""

import sys

from demosaic.experiments.evaluation import detail as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
