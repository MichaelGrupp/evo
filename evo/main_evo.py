#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
main package executable
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

from evo import PACKAGE_BASE_PATH, __version__
from evo.tools import settings

DESC = '''
(c) evo authors - license: run 'evo pkg --license'
More docs are available at: github.com/MichaelGrupp/evo/wiki

Python package for the evaluation of odometry and SLAM

Supported trajectory formats:
* TUM trajectory files
* KITTI pose files
* ROS and ROS2 bagfile with geometry_msgs/PoseStamped,
    geometry_msgs/TransformStamped, geometry_msgs/PoseWithCovarianceStamped,
    nav_msgs/Odometry topics or TF messages
* EuRoC MAV dataset groundtruth files

The following executables are available:

Metrics:
   evo_ape - absolute pose error
   evo_rpe - relative pose error

Tools:
   evo_traj - tool for analyzing, plotting or exporting multiple trajectories
   evo_res - tool for processing multiple result files from the metrics
   evo_ipython - IPython shell with pre-loaded evo modules
   evo_fig - (experimental) tool for re-opening serialized plots
   evo_config - tool for global settings and config file manipulation
'''


def main() -> None:
    import sys
    import argparse
    import argcomplete
    main_parser = argparse.ArgumentParser()
    shared_parser = argparse.ArgumentParser(add_help=False)
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True
    pkg_parser = sub_parsers.add_parser(
        "pkg", description="show infos of the package",
        parents=[shared_parser])
    pkg_parser.add_argument("--info", help="show the package description",
                            action="store_true")
    pkg_parser.add_argument("--version", help="print the package version",
                            action="store_true")
    pkg_parser.add_argument("--pyversion", help="print the Python version",
                            action="store_true")
    pkg_parser.add_argument("--license", help="print the package license",
                            action="store_true")
    pkg_parser.add_argument("--location", help="print the package path",
                            action="store_true")
    pkg_parser.add_argument("--logfile", help="print the logfile path",
                            action="store_true")
    pkg_parser.add_argument("--open_log", help="open the package logfile",
                            action="store_true")
    pkg_parser.add_argument("--clear_log", help="clear package logfile",
                            action="store_true")
    cat_parser = sub_parsers.add_parser(
        "cat_log", description="pipe stdin to global evo logfile"
        " or print logfile to stdout (if no stdin)", parents=[shared_parser])
    cat_parser.add_argument("-l", "--loglevel", help="loglevel of the message",
                            default="info",
                            choices=["error", "warning", "info", "debug"])
    cat_parser.add_argument("-m", "--message",
                            help="explicit message instead of pipe")
    cat_parser.add_argument("-s", "--source",
                            help="source name to use for the log message")
    cat_parser.add_argument("--clear_log", help="clear logfile before exiting",
                            action="store_true")
    argcomplete.autocomplete(main_parser)
    if len(sys.argv[1:]) == 0:
        sys.argv.extend(["pkg", "--info"])  # cheap trick because YOLO
    args = main_parser.parse_args()
    line_end = "\n" if sys.stdout.isatty() else ""

    if args.subcommand == "pkg":
        if not len(sys.argv) > 2:
            pkg_parser.print_help()
            sys.exit(1)
        if args.license:
            print(open(os.path.join(PACKAGE_BASE_PATH, "LICENSE")).read())
        if args.info:
            main_parser.print_usage()
            print(DESC)
        if args.version:
            print(__version__, end=line_end)
        if args.pyversion:
            import platform as pf
            print(pf.python_version(), end=line_end)
        if args.location:
            print(PACKAGE_BASE_PATH, end=line_end)
        if args.logfile or args.open_log:
            print(settings.GLOBAL_LOGFILE_PATH, end=line_end)
            if not os.path.exists(settings.GLOBAL_LOGFILE_PATH):
                print(
                    "no logfile found - run: "
                    "evo_config set global_logfile_enabled", end=line_end)
                sys.exit(1)
            if args.open_log:
                import webbrowser
                webbrowser.open(settings.GLOBAL_LOGFILE_PATH)
        if args.clear_log:
            from evo.tools import user
            if user.confirm("clear logfile? (y/n)"):
                open(settings.GLOBAL_LOGFILE_PATH, mode='w')

    elif args.subcommand == "cat_log":
        if os.name == "nt":
            print("cat_log feature not available on Windows")
            sys.exit(1)
        if not args.message and sys.stdin.isatty():
            if not os.path.exists(settings.GLOBAL_LOGFILE_PATH):
                print(
                    "no logfile found - run: "
                    "evo_config set global_logfile_enabled", end=line_end)
            else:
                print(open(settings.GLOBAL_LOGFILE_PATH).read(), end="")
        elif not settings.SETTINGS.global_logfile_enabled:
            print("logfile disabled", end=line_end)
            sys.exit(1)
        else:
            import logging
            logger = logging.getLogger(__name__)
            from evo.tools import log
            file_fmt = log.DEFAULT_LONG_FMT
            if args.source:
                file_fmt = file_fmt.replace(
                    "%(module)s.%(funcName)s():%(lineno)s", args.source)
            log.configure_logging(silent=True, file_fmt=file_fmt)
            if not args.message:
                msg = sys.stdin.read()
            else:
                msg = args.message
            getattr(logger, args.loglevel)(msg)
        if args.clear_log:
            open(settings.GLOBAL_LOGFILE_PATH, mode='w')


if __name__ == '__main__':
    main()
