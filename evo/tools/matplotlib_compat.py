# -*- coding: UTF8 -*-
"""
Compatibility helpers for Matplotlib imports.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType


def _module_is_outside(module: ModuleType, root: Path) -> bool:
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return True
    return not Path(module_file).resolve().is_relative_to(root)


def use_matplotlib_mplot3d(mpl: ModuleType | None = None) -> None:
    """
    Prefer the mpl_toolkits.mplot3d copy shipped with active Matplotlib.

    Some distributions install ``mpl_toolkits`` as a regular system package.
    When a newer Matplotlib is installed in user/site packages, Python can pair
    that Matplotlib with the older system ``mplot3d`` module. Keep the system
    toolkit path as a fallback, but put Matplotlib's own toolkit first.
    """
    if mpl is None:
        import matplotlib as mpl

    toolkit_root = Path(mpl.__file__).resolve().parent.parent / "mpl_toolkits"
    if not (toolkit_root / "mplot3d").is_dir():
        return

    for name, module in tuple(sys.modules.items()):
        if name != "mpl_toolkits.mplot3d" and not name.startswith(
            "mpl_toolkits.mplot3d."
        ):
            continue
        if _module_is_outside(module, toolkit_root):
            sys.modules.pop(name, None)

    mpl_toolkits = importlib.import_module("mpl_toolkits")
    search_path = getattr(mpl_toolkits, "__path__", None)
    if search_path is None:
        return

    toolkit_path = str(toolkit_root)
    paths = [toolkit_path] + [
        path for path in list(search_path) if path != toolkit_path
    ]
    if list(search_path) == paths:
        return

    try:
        search_path[:] = paths
    except (AttributeError, TypeError):
        mpl_toolkits.__path__ = paths
    importlib.invalidate_caches()
