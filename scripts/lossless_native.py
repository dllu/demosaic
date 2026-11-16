"""Compatibility import; implementation lives in demosaic.experiments.evaluation.native."""

import sys

from demosaic.experiments.evaluation import native as _implementation

# Alias the module so legacy monkeypatching and private imports retain their semantics.
sys.modules[__name__] = _implementation
