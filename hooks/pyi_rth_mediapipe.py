"""Stub matplotlib so MediaPipe solutions import without pyplot (not used by FKYC)."""
from __future__ import annotations

import sys
from types import ModuleType


def _noop(*_args, **_kwargs):
    return None


if "matplotlib.pyplot" not in sys.modules:
    mpl = sys.modules.get("matplotlib") or ModuleType("matplotlib")
    pyplot = ModuleType("matplotlib.pyplot")
    pyplot.figure = _noop
    pyplot.show = _noop
    pyplot.plot = _noop
    pyplot.subplots = lambda *_a, **_k: (None, None)
    mpl.pyplot = pyplot
    sys.modules["matplotlib"] = mpl
    sys.modules["matplotlib.pyplot"] = pyplot
