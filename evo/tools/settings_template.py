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
    "global_logfile_enabled": (
        False,
        ("Whether to write a global logfile to the home folder.\n"
         "Run 'evo pkg --logfile' to see the logfile location.")
    ),
    "console_logging_format": (
        "%(message)s",
        "Format string for the logging module (affects only console output)."
    ),
    "euler_angle_sequence": (
        "sxyz",
        ("Only used in evo_traj's RPY plot: Euler rotation axis sequence.\n"
         "E.g. 'sxyz' or 'ryxy', where s=static or r=rotating frame.\n"
         "See evo/core/transformations.py for more information.")
    ),
    "plot_axis_marker_scale": (
        0.,
        "Scaling parameter of pose coordinate frame markers. 0 will draw nothing."
    ),
    "plot_backend": (
        get_default_plot_backend(),
        "matplotlib backend - default: 'Qt{4, 5}Agg' (if PyQt is installed) or 'TkAgg'."
    ),
    "plot_statistics": (
        ["rmse", "median", "mean", "std", "min", "max"],
        ("Statistics that are included in plots of evo_{ape, rpe, res}.\n"
         "Can also be set to 'none'.")
    ),
    "plot_export_format": (
        "pdf",
        "File format supported by matplotlib for exporting plots."
    ),
    "plot_figsize": (
        [6, 6],
        "The default size of one (sub)plot figure (width, height)."
    ),
    "plot_fontfamily": (
        "sans-serif",
        "Font family string supported by matplotlib."
    ),
    "plot_fontscale": (
        1.0,
        "Font scale value, see: https://seaborn.pydata.org/generated/seaborn.set.html"
    ),
    "plot_invert_xaxis": (
        False,
        "Invert the x-axis of plots."
    ),
    "plot_invert_yaxis": (
        False,
        "Invert the y-axis of plots."
    ),
    "plot_linewidth": (
        1.5,
        "Line width value supported by matplotlib."
    ),
    "plot_multi_cmap": (
        "none",
        "Color map for coloring plots from multiple data sources.\n"
        + "'none' will use the default color palette, see plot_seaborn_palette."
    ),
    "plot_reference_alpha": (
        0.5,
        "Alpha value of the reference trajectories in plots."
    ),
    "plot_reference_color": (
        "black",
        "Color of the reference trajectories in plots."
    ),
    "plot_reference_linestyle": (
        "--",
        "matplotlib linestyle of reference trajectories in plots."
    ),
    "plot_seaborn_palette": (
        "deep6",
        "Default color cycle, taken from a palette of the seaborn package.\n"
        "Can also be a list of colors.\n"
        "See: https://seaborn.pydata.org/generated/seaborn.color_palette.html"
    ),
    "plot_seaborn_style": (
        "darkgrid",
        "Defines the plot background/grid.\n"
        + "Options: 'whitegrid', 'darkgrid', 'white' or 'dark'."
    ),
    "plot_split": (
        False,
        "Show / save each figure separately instead of a collection."
    ),
    "plot_texsystem": (
        "pdflatex",
        "'xelatex', 'lualatex' or 'pdflatex', see: https://matplotlib.org/users/pgf.html",
    ),
    "plot_trajectory_alpha": (
        0.75,
        "Alpha value of non-reference trajectories in plots.",
    ),
    "plot_trajectory_cmap": (
        "jet",
        "matplotlib color map used for mapping values on a trajectory.",
    ),
    "plot_trajectory_linestyle": (
        "-",
        "matplotlib linestyle of non-reference trajectories in plots.",
    ),
    "plot_usetex": (
        False,
        "Use the LaTeX renderer configured in plot_texsystem for plots.",
    ),
    "plot_xyz_realistic": (
        True,
        "Equal axes ratio in 'xyz' plot mode for realistic trajectory plots."
    ),
    "ros_map_unknown_cell_value": (
        205,
        "uint8 value that represents unknown cells in a ROS map image.\n"
        "Used to remove unknown cell pixels when a ROS map is added to a plot."
        "map_saver uses 205, other tools might not.\n"
        "(for example, Cartographer uses 128 for images of probability grids)"
    ),
    "save_traj_in_zip": (
        False,
        "Store backup trajectories in result zip files (increases size)."
    ),
    "table_export_data": (
        "stats",
        "Which data to export: 'info', 'stats' or 'error_array'.",
    ),
    "table_export_format": (
        "csv",
        "Format for exporting tables, e.g. 'csv', 'excel', 'latex', 'json'...",
    ),
    "table_export_transpose": (
        True,
        "Transpose tables for export."
    ),
}
# yapf: enable

# without documentation
DEFAULT_SETTINGS_DICT = {k: v[0] for k, v in DEFAULT_SETTINGS_DICT_DOC.items()}
