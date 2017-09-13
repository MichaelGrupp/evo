"""
default settings and a static container which loads and holds the settings from settings.json
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

import os
import sys
import json
import logging
import imp  # TODO deprecated in Python 3

import colorama
from colorama import Fore

class SettingsException(Exception):
    pass


pyqt4_installed = False
try:
    imp.find_module("PyQt4")
    pyqt4_installed = True
except ImportError:
    pass
    

DEFAULT_SETTINGS_DICT = {
    "plot_xyz_realistic": True,
    "plot_backend": "Qt4Agg" if pyqt4_installed else "TkAgg",
    "plot_hideref": False,
    "plot_linewidth": 1.5,
    "plot_usetex": False,
    "plot_fontfamily": "sans-serif",
    "plot_fontsize": 12,
    "plot_split": False,
    "plot_figsize": [8, 8],
    "plot_info_text": False,
    "plot_trajectory_cmap": "cool",
    "plot_multi_cmap": "none",
    "plot_invert_xaxis": False,
    "plot_invert_yaxis": False,
    "plot_seaborn_style": "darkgrid",
    "plot_export_format": "pdf",
    "table_export_format": "csv",
    "table_export_transpose": True,
    "save_traj_in_zip": False,
    "logging_format": "%(message)s",
    "logfile_enabled": False
}

DEFAULT_SETTINGS_HELP = '''
plot_backend
    matplotlib backend - tabs are supported with TkAgg and Qt4Agg
plot_hideref
    hide reference trajectory in trajectory plots of metrics
plot_linewidth
    matplotlib supported line width value
plot_usetex
    use LaTeX renderer for plots
plot_fontfamily
    matplotlib supported font family string
plot_fontsize
    matplotlib supported font size integer
plot_split
    show / save each figure separately
    default: window with tabs from TkAgg backend
plot_figsize
    the default size of one (sub)plot figure (width, height)
plot_xyz_realistic
    equal axes aspect ratio for more realistic trajectory plots in xyz plot mode
plot_info_text
    allow text boxes with additional infos below the plots
plot_seaborn_style
    whitegrid, darkgrid, white, dark
plot_trajectory_cmap
    matplotlib color map for mapping values on a trajectory
plot_multi_cmap matplotlib
    color map for coloring plots from multiple data sources
    "none" will use default color cycle
plot_export_format
    matplotlib supported file format for exporting plots
table_export_format
    format for exporting tables (csv, excel, latex)
table_export_transpose
    transpose tables for export
save_traj_in_zip
    backup trajectories in result zip files (increases size)
logging_format
    format string for the logging module (console only)
logfile_enabled
    whether to write .evo.log logfile to home folder
'''


class SettingsContainer(dict):
    def __init__(self, settings_path, data=None):
        super(SettingsContainer, self).__init__()
        try:
            if not data:
                with open(settings_path) as settings_file:
                    data = json.load(settings_file)
            for k, v in data.items():
                setattr(self, k, v)
        except Exception as e:
            logging.error(str(e))
            raise SettingsException("fatal: failed to load package settings file " + settings_path)

    def __getattr__(self, attr):
        # allow dot access
        return self[attr]

    def __setattr__(self, attr, value):
        # allow dot access
        self[attr] = value


PACKAGE_BASE_PATH = os.path.abspath(__file__ + "/../../")
PACKAGE_VERSION = open(os.path.join(PACKAGE_BASE_PATH, "version")).read()

DEFAULT_PATH = os.path.join(PACKAGE_BASE_PATH, "settings.json")
DEFAULT_LOGFILE_PATH = os.path.join(os.path.expanduser('~'), ".evo.log")
if not os.path.exists(DEFAULT_PATH):
    logging.error(Fore.LIGHTRED_EX + "fatal: failed to load package settings file " + DEFAULT_PATH + Fore.RESET)
    logging.warning(Fore.LIGHTYELLOW_EX + "trying to generate new settings.json" + Fore.RESET)
    with open(DEFAULT_PATH, 'w') as cfg_file:
        cfg_file.write(json.dumps(DEFAULT_SETTINGS_DICT, indent=4, sort_keys=True))
SETTINGS = SettingsContainer(DEFAULT_PATH)


class DefaultConsoleFormatter(logging.Formatter):
    def __init__(self, fmt="%(msg)s"):
        logging.Formatter.__init__(self, fmt)
        colorama.init()
        self.error_fmt  = Fore.LIGHTRED_EX + "[%(levelname)s]" + Fore.RESET + "\n%(msg)s"
        self.warning_fmt  = Fore.LIGHTYELLOW_EX + "[%(levelname)s]" + Fore.RESET + "\n%(msg)s"
        self.info_fmt = fmt
        self.debug_fmt  = fmt

    def format(self, record):
        if record.levelno == logging.ERROR:
            self._fmt = self.error_fmt
        elif record.levelno == logging.WARNING:
            self._fmt = self.warning_fmt
        elif record.levelno == logging.INFO:
            self._fmt = self.info_fmt
        elif record.levelno == logging.DEBUG:
            self._fmt = self.debug_fmt
        result = logging.Formatter.format(self, record)
        return result


def configure_logging(verbose=False, silent=False, debug=False, 
                      fmt=None, dbg_fmt=None, file_path=None, mark_entry=True):
    if fmt is None:
        fmt = SETTINGS.logging_format
    if dbg_fmt is None:
        dbg_fmt = "[%(levelname)s][%(asctime)s][%(module)s.%(funcName)s():%(lineno)s]\n%(message)s"
    # if enabled, always log in debug mode to logfile
    if not SETTINGS.logfile_enabled:
        logfile = os.devnull
    elif file_path is None:
        logfile = DEFAULT_LOGFILE_PATH
    else:
        logfile = file_path
    logging.basicConfig(level=logging.DEBUG, format=dbg_fmt, filename=logfile, filemode='a')
    version = open(os.path.join(PACKAGE_BASE_PATH, "version")).read().rstrip()
    if mark_entry:
        logging.debug("#"*80 + "\nlog entry - evo " + version + "\n" + "#"*80)
    # console output based on user's choice
    if debug or verbose and not silent:
        console_level = logging.DEBUG
    elif not silent:
        console_level = logging.INFO
    else: 
        console_level = logging.WARNING
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_formatter = logging.Formatter(dbg_fmt) if debug else DefaultConsoleFormatter()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    # add console_handler to default root logger
    logging.getLogger('').addHandler(console_handler)
    # and a global console logger that can be retreived by its name
    console_logger = logging.getLogger("console")
    console_logger.addHandler(console_handler)
    console_logger.setLevel(console_level)
    if debug:
        import getpass as gp
        import platform as pf
        logging.debug("system info:"
                      "\nPython %s\n%s\n%s\n"
                      % (pf.python_version(), pf.platform(), gp.getuser() + "@" + pf.node()))
