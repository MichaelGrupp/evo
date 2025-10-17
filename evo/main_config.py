#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
simple JSON configuration generator script for executables
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
import json
import logging
import os
import sys
import typing

import colorama
from colorama import Style
from pygments import highlight, lexers, formatters

from evo import EvoException
from evo.tools import log, user, settings
from evo.tools._typing import PathStr
from evo.tools.settings_template import DEFAULT_SETTINGS_DICT_DOC
from evo.tools.settings_template import DEFAULT_SETTINGS_DICT

logger = logging.getLogger(__name__)

SEP = "-" * 80


class ConfigError(EvoException):
    pass


def log_info_dict_json(
    data: dict,
    colored: bool = True,
    parameter_subset: typing.Sequence[str] | None = None,
) -> None:
    if parameter_subset:
        data = {
            key: value
            for key, value in data.items()
            if key in parameter_subset
        }
    data_str = json.dumps(data, indent=4, sort_keys=True)
    if colored and os.name != "nt":
        data_str = highlight(
            data_str,
            lexers.JsonLexer(),
            formatters.Terminal256Formatter(
                style=settings.SETTINGS.pygments_style
            ),
        )
    logger.info(data_str)


def show(
    config_path: PathStr,
    colored: bool = True,
    parameter_subset: typing.Sequence[str] | None = None,
) -> None:
    with open(config_path) as config_file:
        log_info_dict_json(json.load(config_file), colored, parameter_subset)


def merge_json_union(
    first_file: PathStr, second_file: PathStr, soft: bool = False
) -> None:
    with open(first_file, "r+") as f_1:
        config_1 = json.loads(f_1.read())
        with open(second_file) as f_2:
            config_2 = json.loads(f_2.read())
            config_1 = settings.merge_dicts(config_1, config_2, soft)
        f_1.truncate(0)
        f_1.seek(0)
        f_1.write(json.dumps(config_1, indent=4, sort_keys=True))


def is_number(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def finalize_values(config: dict, key: str, values: list[str]) -> typing.Any:
    """
    Turns parsed values into final value(s) for the config at the given key,
    e.g. based on the previous type of that parameter or other constraints.
    """
    if len(values) == 0:
        return None
    # Special treatment for plot_seaborn_palette is needed, see #359.
    if key == "plot_seaborn_palette":
        if len(values) > 1:
            return values
        from seaborn.palettes import color_palette

        try:
            color_palette(values[0])
            return values[0]
        except ValueError:
            return values
    if isinstance(config[key], bool):
        value = values[-1]
        if isinstance(value, str) and value.lower() == "false":
            return False
        elif isinstance(value, str) and value.lower() == "true":
            return True
        else:
            return not config[key]
    if not isinstance(config[key], list):
        return values[0]
    if isinstance(values[0], str) and values[0].lower() in ("[]", "none"):
        return []

    return values


def set_config(config_path: PathStr, arg_list: typing.Sequence[str]) -> None:
    with open(config_path) as config_file:
        config = json.load(config_file)
    max_idx = len(arg_list) - 1
    for i, arg in enumerate(arg_list):
        if arg not in config.keys():
            continue
        if i + 1 <= max_idx and arg_list[i + 1] not in config.keys():
            values: list[typing.Any] = []
            for j in range(i + 1, max_idx + 1):
                value = arg_list[j]
                if value in config.keys():
                    break
                if is_number(value):
                    if int(float(value)) - float(value) != 0:
                        values.append(float(value))
                    else:
                        values.append(int(float(value)))
                else:
                    values.append(value)
            config[arg] = finalize_values(config, arg, values)
        else:
            # no argument, toggle if it's a boolean parameter
            config[arg] = (
                not config[arg]
                if isinstance(config[arg], bool)
                else config[arg]
            )
    with open(config_path, "w") as config_file:
        config_file.write(json.dumps(config, indent=4, sort_keys=True))


def generate(arg_list: typing.Sequence[str]) -> dict[str, typing.Any]:
    data: dict[str, typing.Any] = {}
    max_idx = len(arg_list) - 1
    for i, arg in enumerate(arg_list):
        if arg.startswith("-"):
            arg = arg[1:] if not arg.startswith("--") else arg[2:]
            if (
                i + 1 <= max_idx and arg_list[i + 1].startswith("-")
            ) or i + 1 > max_idx:
                data[arg] = True  # just a boolean flag
            else:
                values: list[typing.Any] = []
                for j in range(i + 1, max_idx + 1):
                    value = arg_list[j]
                    if value.startswith("-"):
                        break
                    values.append(float(value) if is_number(value) else value)
                if len(values) == 1:
                    values = values[0]
                data[arg] = values
    return data


SET_HELP = """
set parameters
Unless -c / --config is specified, the package settings will be used.

--EXAMPLE--

If your configuration looks like this (via 'evo_config show'):

    {
        "plot_export_format": "svg"
        "plot_info_text": true,
    }
    
running:
    evo_config set plot_export_format png plot_info_text
will set it to:

    {
        "plot_export_format": "png"
        "plot_info_text": false,
    }
"""

GENERATE_HELP = """
generate configuration files from command-line args

The configuration files are intended to hold command line
parameters used by the respective executables, e.g. 'evo_ape'.

--EXAMPLE--

Running:

    evo_config generate --align --plot --plot_mode xz --verbose

will convert the arguments into the JSON format:

    {
        "align": true,
        "plot": true,
        "plot_mode": "xz",
        "verbose": true
    }

List arguments (--arg 1 2 3) are also supported.
To save the configuration, specify -o / --output.
"""


def main() -> None:
    import argcomplete

    basic_desc = "crappy configuration tool"
    lic = "(c) evo authors"
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument(
        "--no_color", help="don't color output", action="store_true"
    )
    main_parser = argparse.ArgumentParser(
        description="%s %s" % (basic_desc, lic)
    )
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True

    show_parser = sub_parsers.add_parser(
        "show",
        description="show configuration - %s" % lic,
        parents=[shared_parser],
    )
    show_parser.add_argument(
        "-c",
        "--config",
        help="path of the config file to display (default: package settings)",
    )
    show_parser.add_argument(
        "--brief", help="show only the .json data", action="store_true"
    )
    show_parser.add_argument(
        "params",
        choices=list(DEFAULT_SETTINGS_DICT.keys()),
        nargs=argparse.REMAINDER,
        help="parameters to show",
    )

    set_parser = sub_parsers.add_parser(
        "set",
        description=SET_HELP,
        parents=[shared_parser],
        formatter_class=argparse.RawTextHelpFormatter,
    )
    set_parser.add_argument(
        "params",
        choices=list(DEFAULT_SETTINGS_DICT.keys()),
        nargs=argparse.REMAINDER,
        help="parameters to set",
    )
    set_parser.add_argument(
        "-c",
        "--config",
        help="optional config file (default: package settings)",
        default=None,
    )
    set_parser.add_argument(
        "-m",
        "--merge",
        help="other config file to merge in (priority)",
        default=None,
    )
    set_parser.add_argument(
        "--soft", help="do a soft-merge (no overwriting)", action="store_true"
    )

    gen_parser = sub_parsers.add_parser(
        "generate",
        description=GENERATE_HELP,
        parents=[shared_parser],
        formatter_class=argparse.RawTextHelpFormatter,
    )
    gen_parser.add_argument(
        "-o", "--out", help="path for config file to generate"
    )

    reset_parser = sub_parsers.add_parser(
        "reset",
        description="reset package settings - %s" % lic,
        parents=[shared_parser],
    )
    reset_parser.add_argument(
        "-y", help="acknowledge automatically", action="store_true"
    )
    reset_parser.add_argument(
        "params",
        choices=list(DEFAULT_SETTINGS_DICT.keys()),
        nargs=argparse.REMAINDER,
        help="parameters to reset",
    )

    argcomplete.autocomplete(main_parser)
    if len(sys.argv) > 1 and sys.argv[1] == "set":
        args, other_args = main_parser.parse_known_args()
        other_args = [arg for arg in sys.argv[2:]]
    else:
        args, other_args = main_parser.parse_known_args()
    log.configure_logging()
    colorama.init()

    config = settings.DEFAULT_PATH
    if hasattr(args, "config"):
        if args.config:
            config = args.config

    if args.subcommand == "show":
        if not args.brief and not args.config:
            style = Style.BRIGHT if not args.no_color else Style.NORMAL
            doc_str = "\n".join(
                f"{style}{parameter}{Style.RESET_ALL}:\n{value_and_doc[1]}\n"
                for parameter, value_and_doc in sorted(
                    DEFAULT_SETTINGS_DICT_DOC.items()
                )
                if (not args.params or parameter in args.params)
            )
            logger.info(doc_str)
            logger.info("{0}\n{1}\n{0}".format(SEP, config))
        show(config, colored=not args.no_color, parameter_subset=args.params)
        if config == settings.DEFAULT_PATH and not args.brief:
            logger.info(SEP + "\nSee text above for parameter descriptions.")

    elif args.subcommand == "set":
        if not os.access(config, os.W_OK):
            logger.error("No permission to modify %s", config)
            sys.exit(1)
        if other_args or args.merge:
            logger.info("{0}\nOld configuration:\n{0}".format(SEP))
            show(config, colored=not args.no_color)
            try:
                set_config(config, other_args)
            except ConfigError as e:
                logger.error(e)
                sys.exit(1)
            if args.merge:
                merge_json_union(config, args.merge, args.soft)
            logger.info(SEP + "\nNew configuration:\n" + SEP)
            show(config, colored=not args.no_color)
        else:
            logger.error("No configuration parameters given (see --help).")

    elif args.subcommand == "generate":
        if other_args:
            logger.info(
                "{0}\nParsed by argparse:\n{1}\n"
                "{0}\nWARNING:\nMake sure you use the 'long-style' -- options "
                "(e.g. --plot) if possible\nand no combined short '-' flags, "
                "(e.g. -vp)\n{0}".format(SEP, other_args)
            )
            data = generate(other_args)
            log_info_dict_json(data, colored=not args.no_color)
            if args.out and user.check_and_confirm_overwrite(args.out):
                with open(args.out, "w") as out:
                    out.write(json.dumps(data, indent=4, sort_keys=True))
            elif not args.out:
                logger.warning("\n(-o | --out) not specified - saving nothing")
        else:
            logger.error("No command line arguments given (see --help)")

    elif args.subcommand == "reset":
        if not os.access(config, os.W_OK):
            logger.error("No permission to modify %s", config)
            sys.exit(1)
        if args.params:
            settings.reset(settings.DEFAULT_PATH, parameter_subset=args.params)
        elif args.y or user.confirm(
            "Reset all package settings to the default settings? (y/n)"
        ):
            settings.reset()
        else:
            sys.exit()
        logger.info("{0}\nPackage settings after reset:\n{0}".format(SEP))
        show(settings.DEFAULT_PATH, colored=not args.no_color)


if __name__ == "__main__":
    main()
