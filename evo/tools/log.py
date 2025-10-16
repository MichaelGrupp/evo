# -*- coding: UTF8 -*-
"""
utilities for the configuration of the package's loggers
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

import logging
import sys

import colorama
from colorama import Fore

from evo.tools.settings import SETTINGS, GLOBAL_LOGFILE_PATH
from evo.tools._typing import PathStr

colorama.init()

CONSOLE_ERROR_FMT = "{}[%(levelname)s]{} %(message)s".format(
    Fore.LIGHTRED_EX, Fore.RESET
)
CONSOLE_WARN_FMT = "{}[%(levelname)s]{} %(message)s".format(
    Fore.LIGHTYELLOW_EX, Fore.RESET
)
DEFAULT_LONG_FMT = "[%(levelname)s][%(asctime)s][%(module)s.%(funcName)s():%(lineno)s]\n%(message)s"


class ConsoleFormatter(logging.Formatter):
    def __init__(self, fmt="%(msg)s"):
        super(ConsoleFormatter, self).__init__(fmt)
        self.critical_fmt = CONSOLE_ERROR_FMT
        self.error_fmt = CONSOLE_ERROR_FMT
        self.warning_fmt = CONSOLE_WARN_FMT
        self.info_fmt = fmt
        self.debug_fmt = fmt

    def format(self, record):
        if record.levelno == logging.CRITICAL:
            self._fmt = self.error_fmt
        elif record.levelno == logging.ERROR:
            self._fmt = self.error_fmt
        elif record.levelno == logging.WARNING:
            self._fmt = self.warning_fmt
        elif record.levelno == logging.INFO:
            self._fmt = self.info_fmt
        elif record.levelno == logging.DEBUG:
            self._fmt = self.debug_fmt
        self._style._fmt = self._fmt
        result = logging.Formatter.format(self, record)
        return result


# configures the package's root logger (see __init__.py)
def configure_logging(
    verbose: bool = False,
    silent: bool = False,
    debug: bool = False,
    console_fmt: str | None = None,
    file_fmt: str = DEFAULT_LONG_FMT,
    local_logfile: PathStr | None = None,
) -> None:

    logger = logging.getLogger("evo")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])

    logfiles: list[PathStr] = []
    if SETTINGS.global_logfile_enabled:
        logfiles.append(GLOBAL_LOGFILE_PATH)
    if local_logfile is not None:
        logfiles.append(local_logfile)

    for logfile in logfiles:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(file_fmt))
        logger.addHandler(file_handler)

    if debug or verbose:
        console_level = logging.DEBUG
    elif silent:
        console_level = logging.WARNING
    else:
        console_level = logging.INFO

    if debug:
        console_fmt = DEFAULT_LONG_FMT
    elif console_fmt is None:
        console_fmt = SETTINGS.console_logging_format

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ConsoleFormatter(console_fmt))
    logger.addHandler(console_handler)

    # log header for debug mode
    if debug:
        import getpass as gp
        import platform as pf

        logger.debug(
            "System info:\nPython {pyversion}\n{platform}\n{user}\n".format(
                pyversion=pf.python_version(),
                platform=pf.platform(),
                user=gp.getuser() + "@" + pf.node(),
            )
        )
