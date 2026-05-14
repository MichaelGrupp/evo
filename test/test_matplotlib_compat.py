from pathlib import Path

import pytest


def test_use_matplotlib_mplot3d_prefers_active_matplotlib() -> None:
    import matplotlib as mpl

    from evo.tools.matplotlib_compat import use_matplotlib_mplot3d

    use_matplotlib_mplot3d(mpl)

    toolkit_root = Path(mpl.__file__).resolve().parent.parent / "mpl_toolkits"
    if not (toolkit_root / "mplot3d").is_dir():
        pytest.skip("active Matplotlib installation has no bundled mplot3d")

    import mpl_toolkits.mplot3d as mplot3d

    assert Path(mplot3d.__file__).resolve().is_relative_to(toolkit_root)
