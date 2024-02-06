# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
separate entry points into pieces to allow common error handling and faster argcomplete
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

import argparse
import logging
import sys
from importlib import import_module

import argcomplete
from evo import EvoException, NullHandler

logger = logging.getLogger(__name__)

KNOWN_EXCEPTIONS = (EvoException, FileNotFoundError)
"""
the actual entry points:
to save time for argcomplete (tab bash completion),
only do required imports in respective module when creating parser
(no expensive global imports)
"""


def handle_entry_point(app_name: str) -> None:
    parser_module = import_module(f"evo.main_{app_name}_parser")
    parser = parser_module.parser()
    argcomplete.autocomplete(parser)
    main_module = import_module(f"evo.main_{app_name}")
    launch(main_module, parser)


def ape() -> None:
    handle_entry_point("ape")


def rpe() -> None:
    handle_entry_point("rpe")


def res() -> None:
    handle_entry_point("res")


def traj() -> None:
    handle_entry_point("traj")


def merge_config(args: argparse.Namespace) -> argparse.Namespace:
    """
    merge .json config file with the command line args (if --config was defined)
    :param args: parsed argparse NameSpace object
    :return: merged argparse NameSpace object
    """
    import json
    if args.config:
        with open(args.config) as config:
            merged_config_dict = vars(args).copy()
            # merge both parameter dicts
            config_dict = json.loads(config.read())
            merged_config_dict.update(config_dict)
            # override args the hacky way
            args = argparse.Namespace(**merged_config_dict)

            # Override global settings for this session
            # if the config file contains matching keys.
            from evo.tools.settings import SETTINGS
            SETTINGS.update_existing_keys(other=config_dict)

    return args


def launch(main_module, parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    if hasattr(args, "config"):
        args = merge_config(args)
    try:
        main_module.run(args)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except KNOWN_EXCEPTIONS as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception:
        base_logger = logging.getLogger("evo")
        if len(base_logger.handlers) == 0 or isinstance(
                base_logger.handlers[0], NullHandler):
            # In case logging couldn't be configured, print & exit directly.
            import traceback
            traceback.print_exc()
            sys.exit(1)
        logger.exception("Unhandled error in " + main_module.__name__)
        print("")
        err_msg = "evo module " + main_module.__name__ + " crashed"
        from evo.tools import settings
        if settings.SETTINGS.global_logfile_enabled:
            err_msg += f" - see {settings.GLOBAL_LOGFILE_PATH}"
        else:
            err_msg += " - no logfile written (disabled)"
        logger.error(err_msg)
        sys.exit(1)
