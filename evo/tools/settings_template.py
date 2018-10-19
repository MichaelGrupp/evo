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

import pkgutil


def get_default_plot_backend():
    backends = {"PyQt5": "Qt5Agg", "PyQt4": "Qt4Agg"}
    for pkg in backends:
        if pkgutil.find_loader(pkg) is not None:
            return backends[pkg]
    return "TkAgg"


# default settings with documentation
# yapf: disable
DEFAULT_SETTINGS_DICT_DOC = {
    "plot_xyz_realistic": (
        True,
        "Equal axes ratio in 'xyz' plot mode for realistic trajectory plots."
    ),
    "plot_backend": (
        get_default_plot_backend(),
        "matplotlib backend - default: 'Qt{4, 5}Agg' (if PyQt is installed) or 'TkAgg'."
    ),
    "plot_hideref": (
        False,
        "Hide the reference trajectory in trajectory plots."
    ),
    "plot_linewidth": (
        1.5,
        "Line width value supported by matplotlib."
    ),
    "plot_usetex": (
        False,
        "Use the LaTeX renderer configured in plot_texsystem for plots.",
    ),
    "plot_texsystem": (
        "pdflatex",
        "'xelatex', 'lualatex' or 'pdflatex', see: https://matplotlib.org/users/pgf.html",
    ),
    "plot_fontfamily": (
        "sans-serif",
        "Font family string supported by matplotlib."
    ),
    "plot_fontscale": (
        1.0,
        "Font scale value, see: https://seaborn.pydata.org/generated/seaborn.set.html"
    ),
    "plot_split": (
        False,
        "Show / save each figure separately instead of a collection."
    ),
    "plot_figsize": (
        [6, 6],
        "The default size of one (sub)plot figure (width, height)."
    ),
    "plot_trajectory_cmap": (
        "jet",
        "matplotlib color map used for mapping values on a trajectory.",
    ),
    "plot_multi_cmap": (
        "none",
        "Color map for coloring plots from multiple data sources.\n"
        + "'none' will use the default color palette, see plot_seaborn_palette."
    ),
    "plot_invert_xaxis": (
        False,
        "Invert the x-axis of plots."
    ),
    "plot_invert_yaxis": (
        False,
        "Invert the y-axis of plots."
    ),
    "plot_seaborn_style": (
        "darkgrid",
        "Defines the plot background/grid.\n"
        + "Options: 'whitegrid', 'darkgrid', 'white' or 'dark'."
    ),
    "plot_seaborn_palette": (
        "deep6",
        "Default color palette of seaborn. Can also be a list of colors.\n"
        + "See: https://seaborn.pydata.org/generated/seaborn.color_palette.html"
    ),
    "plot_export_format": (
        "pdf",
        "File format supported by matplotlib for exporting plots."
    ),
    "table_export_format": (
        "csv",
        "Format for exporting tables, e.g. 'csv', 'excel', 'latex', 'json'...",
    ),
    "table_export_data": (
        "stats",
        "Which data to export: 'info', 'stats' or 'error_array'.",
    ),
    "table_export_transpose": (
        True,
        "Transpose tables for export."
    ),
    "save_traj_in_zip": (
        False,
        "Store backup trajectories in result zip files (increases size)."
    ),
    "logging_format": (
        "%(message)s",
        "Format string for the logging module (console only)."
    ),
    "logfile_enabled": (
        False,
        "Whether to write a logfile to the home folder."
    )
}
# yapf: enable

# without documentation
DEFAULT_SETTINGS_DICT = {k: v[0] for k, v in DEFAULT_SETTINGS_DICT_DOC.items()}
