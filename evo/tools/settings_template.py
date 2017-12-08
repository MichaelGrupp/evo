"""
default package settings definition
author: Michael Grupp

This file is part of evo (github.com/MichaelGrupp/evo).

evo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

evo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with evo.  If not, see <http://www.gnu.org/licenses/>.
"""

import imp  # TODO deprecated in Python 3


pyqt4_installed = False
try:
    imp.find_module("PyQt4")
    pyqt4_installed = True
except ImportError:
    pass


# default settings with documentation
DEFAULT_SETTINGS_DICT_DOC = {
    "plot_xyz_realistic": ( 
        True,
        "equal axes ratio in 'xyz' plot mode for realistic trajectory plots"
    ),
    "plot_backend": (
        "Qt4Agg" if pyqt4_installed else "TkAgg",
        "matplotlib backend - TkAgg (default) or Qt4Agg (if PyQt is installed)"
    ),
    "plot_hideref": (
        False,
        "hide the reference trajectory in trajectory plots"
    ),
    "plot_linewidth": (
        1.5,
        "line width value supported by matplotlib"
    ),
    "plot_usetex": (
        False,
        "use LaTeX renderer for plots",
    ),
    "plot_fontfamily": (
        "sans-serif",
        "font family string supported by matplotlib"
    ),
    "plot_fontsize": (
        12,
        "font size value supported by matplotlib"
    ),
    "plot_split": (
        False,
        "show / save each figure separately"
    ),
    "plot_figsize": (
        [6, 6],
        "the default size of one (sub)plot figure (width, height)"
    ),
    "plot_info_text": (
        False,
        "allow text boxes with additional infos below the plots"
    ),
    "plot_trajectory_cmap": (
        "jet",
        "matplotlib color map used for mapping values on a trajectory",
    ),
    "plot_multi_cmap": (
        "none",
        "color map for coloring plots from multiple data sources"
        + "\n'none' will use default color cycle"
    ),
    "plot_invert_xaxis": (
        False,
        "invert the x-axes of plots"
    ),
    "plot_invert_yaxis": (
        False,
        "invert the y-axes of plots"
    ),
    "plot_seaborn_style": (
        "darkgrid",
        "defines plot background/grid: whitegrid, darkgrid, white or dark"
    ),
    "plot_export_format": (
        "pdf",
        "file format supported by matplotlib for exporting plots"
    ),
    "table_export_format": (
        "csv",
        "format for exporting tables (csv, excel, latex)",
    ),
    "table_export_transpose": (
        True,
        "transpose tables for export"
    ),
    "save_traj_in_zip": (
        False,
        "backup trajectories in result zip files (increases size)"
    ),
    "logging_format": (
        "%(message)s",
        "format string for the logging module (console only)"
    ),
    "logfile_enabled": (
        False,
        "whether to write a logfile to the home folder"
    )
}

# without documentation
DEFAULT_SETTINGS_DICT = {k : v[0] for k, v in DEFAULT_SETTINGS_DICT_DOC.items()}