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

from __future__ import print_function

import os
import sys
import json
import argparse
import logging

import colorama
from pygments import highlight, lexers, formatters

from evo.tools import user, settings

SEP = "-" * 80


class ConfigError(Exception):
    pass


def reset_pkg_settings(pkg_config=settings.DEFAULT_PATH):
    with open(pkg_config, 'w') as cfg_file:
        print(pkg_config)
        cfg_file.write(json.dumps(settings.DEFAULT_SETTINGS_DICT, indent=4, sort_keys=True))


def log_info_dict_json(data_str, colored=True):
    data_str = json.dumps(data_str, indent=4, sort_keys=True)
    if colored and os.name != "nt":
        data_str = highlight(data_str, lexers.JsonLexer(), 
                             formatters.Terminal256Formatter(style="monokai"))
    logging.info(data_str)


def show(cfg_path, colored=True):
    with open(cfg_path) as cfg_file:
        log_info_dict_json(json.load(cfg_file), colored)


def merge_json_union(first, second, soft=False):
    with open(first, 'r+') as f_1:
        cfg_1 = json.loads(f_1.read())
        with open(second) as f_2:
            cfg_2 = json.loads(f_2.read())
            cfg_1 = settings.merge_dicts(cfg_1, cfg_2, soft)
        f_1.truncate(0)
        f_1.seek(0)
        f_1.write(json.dumps(cfg_1, indent=4, sort_keys=True))


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def set_cfg(cfg_path, arg_list):
    with open(cfg_path) as cfg_file:
        data = json.load(cfg_file)
    max_idx = len(arg_list) - 1
    for i, arg in enumerate(arg_list):
        if arg in data:
            if i + 1 <= max_idx:
                if arg_list[i+1].lower() == "true":
                    data[arg] = True
                elif arg_list[i+1].lower() == "false":
                    data[arg] = False
                else:
                    values = []
                    for j in range(i + 1, max_idx + 1):
                        value = arg_list[j]
                        if value in data:
                            break
                        if is_number(value):
                            if int(float(value)) - float(value) != 0:
                                values.append(float(value))
                            else:
                                values.append(int(float(value)))
                        else:
                            values.append(value)
                    if len(values) == 1:
                        values = values[0]
                    data[arg] = not data[arg] if isinstance(data[arg], bool) else values
            elif i + 1 > max_idx or arg_list[i+1] in data:
                # toggle boolean parameter
                data[arg] = not data[arg] if isinstance(data[arg], bool) else data[arg]
    with open(cfg_path, 'w') as cfg_file:
        cfg_file.write(json.dumps(data, indent=4, sort_keys=True))


def generate(arg_list):
    data = {}
    max_idx = len(arg_list) - 1
    for i, arg in enumerate(arg_list):
        if arg.startswith("-"):
            arg = arg[1:] if not arg.startswith("--") else arg[2:]
            if (i + 1 <= max_idx and arg_list[i + 1].startswith("-")) or i + 1 > max_idx:
                data[arg] = True  # just a boolean flag
            else:
                values = []
                for j in range(i + 1, max_idx + 1):
                    value = arg_list[j]
                    if value.startswith("-"):
                        break
                    values.append(float(value) if is_number(value) else value)
                if len(values) == 1:
                    values = values[0]
                data[arg] = values
    return data


SET_HELP = '''
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
'''

GENERATE_HELP = '''
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
'''


def main():
    import argcomplete
    basic_desc = "crappy configuration tool"
    lic = "(c) michael.grupp@tum.de"
    shared_parser = argparse.ArgumentParser(add_help=False)
    shared_parser.add_argument("--no_color", help="don't color output", 
                               action="store_false", default=True)
    main_parser = argparse.ArgumentParser(description="%s %s" % (basic_desc, lic))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True

    show_parser = sub_parsers.add_parser("show", description="show configuration - %s" % lic,
                                         parents=[shared_parser])
    show_parser.add_argument("config",
                             help="optional config file to display (default: package settings)",
                             nargs='?')
    show_parser.add_argument("--brief", help="show only the .json data",
                             action="store_true")

    set_parser = sub_parsers.add_parser("set", description=SET_HELP, parents=[shared_parser],
                                        formatter_class=argparse.RawTextHelpFormatter)
    set_parser.add_argument("-c", "--config",
                            help="optional config file (default: package settings)", default=None)
    set_parser.add_argument("-m", "--merge",
                            help="other config file to merge in (priority)", default=None)

    gen_parser = sub_parsers.add_parser("generate", description=GENERATE_HELP,
                                        parents=[shared_parser],
                                        formatter_class=argparse.RawTextHelpFormatter)
    gen_parser.add_argument("-o", "--out", help="path for config file to generate")

    reset_parser = sub_parsers.add_parser("reset", description="reset package settings - %s" % lic,
                                          parents=[shared_parser])

    argcomplete.autocomplete(main_parser)
    args, other_args = main_parser.parse_known_args()
    settings.configure_logging()
    colorama.init()

    config = settings.DEFAULT_PATH
    if hasattr(args, "config"):
        if args.config:
            config = args.config

    if args.subcommand == "show":
        if not args.brief and not args.config:
            logging.info(settings.DEFAULT_SETTINGS_HELP)
            logging.info(SEP + "\n" + config + "\n" + SEP)
        show(config, colored=args.no_color)
        if config == settings.DEFAULT_PATH and not args.brief:
            logging.info(SEP + "\nsee text above for parameter descriptions")

    elif args.subcommand == "set":
        if not os.access(config, os.W_OK):
            logging.info("no permission to modify " + config)
            sys.exit()
        if other_args or args.merge:
            logging.info(SEP + "\nold configuration:\n" + SEP)
            show(config, colored=args.no_color)
            try:
                set_cfg(config, other_args)
            except ConfigError as e:
                logging.error(e)
                sys.exit(1)
            if args.merge:
                merge_json_union(config, args.merge)
            logging.info(SEP + "\nnew configuration:\n" + SEP)
            show(config, colored=args.no_color)
        else:
            logging.info("no configuration parameters given (see --help)")

    elif args.subcommand == "generate":
        if other_args:
            logging.info(SEP + "\nparsed by argparse:\n" + str(other_args))
            logging.info(SEP + "\nWARNING:\n" +
                  "make sure you use the 'long-style' -- options (e.g. --plot) if possible\n" +
                  "and no combined 'short' - flags, (e.g. -avp)\n" + SEP)
            data = generate(other_args)
            log_info_dict_json(data, colored=args.no_color)
            if args.out and user.check_and_confirm_overwrite(args.out):
                with open(args.out, 'w') as out:
                    out.write(json.dumps(data, indent=4, sort_keys=True))
            elif not args.out:
                logging.info(SEP + "\nno output file specified (-o / --out) - doing nothing\n" + SEP)
        else:
            logging.info("no command line arguments given (see --help)")

    elif args.subcommand == "reset":
        if not os.access(config, os.W_OK):
            logging.info("no permission to modify" + config)
            sys.exit()
        if user.confirm("reset the package settings to the default settings? (y/n)"):
            reset_pkg_settings(settings.DEFAULT_PATH)
            logging.info(SEP + "\npackage settings after reset:\n" + SEP)
            show(settings.DEFAULT_PATH, colored=args.no_color)


if __name__ == '__main__':
    main()
