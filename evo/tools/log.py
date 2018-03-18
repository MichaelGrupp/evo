import logging
import os
import sys

import colorama
from colorama import Fore

from evo.tools.settings import SETTINGS, DEFAULT_LOGFILE_PATH


CONSOLE_ERROR_FMT = "{}[%(levelname)s]{} %(msg)s".format(Fore.LIGHTRED_EX, Fore.RESET)
CONSOLE_WARN_FMT = "{}[%(levelname)s]{} %(msg)s".format(Fore.LIGHTYELLOW_EX, Fore.RESET)
DEFAULT_LONG_FMT = "[%(levelname)s][%(asctime)s][%(module)s.%(funcName)s():%(lineno)s]\n%(message)s"


class ConsoleFormatter(logging.Formatter):
    def __init__(self, fmt="%(msg)s"):
        logging.Formatter.__init__(self, fmt)
        colorama.init()
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
        result = logging.Formatter.format(self, record)
        return result


# configures the package's root logger (see __init__.py)
def configure_logging(verbose=False, silent=False, debug=False,
                      console_fmt=None, file_fmt=DEFAULT_LONG_FMT, file_path=None):

    logger = logging.getLogger("evo")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if len(logger.handlers) > 0:
        logger.removeHandler(logger.handlers[0])

    if not SETTINGS.logfile_enabled:
        logfile = os.devnull
    elif file_path is None:
        logfile = DEFAULT_LOGFILE_PATH
    else:
        logfile = file_path

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
        console_fmt = SETTINGS.logging_format

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
                user=gp.getuser() + "@" + pf.node()))
