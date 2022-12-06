#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
launch a custom IPython shell for evo
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
import os
import shutil
import subprocess as sp
import sys

from evo import PACKAGE_BASE_PATH

DESC = '''
Launches an IPython shell with pre-loaded evo modules
(c) evo authors

Unknown command line arguments are forwarded to the ipython executable
'''


def main() -> None:
    main_parser = argparse.ArgumentParser(
        description=DESC, formatter_class=argparse.RawTextHelpFormatter)
    args, other_args = main_parser.parse_known_args()
    other_args = [] if other_args is None else other_args
    FNULL = open(os.devnull, 'w')

    # check if IPython is installed properly
    ipython = "ipython3"
    if shutil.which(ipython) is None:
        # fall back to the non-explicit ipython name if ipython3 is not in PATH
        ipython = "ipython"
        if shutil.which(ipython) is None:
            print("IPython is not installed", file=sys.stderr)
            sys.exit(1)

    python = ipython[1:]

    try:
        sp.check_call([ipython, "profile", "locate", "evo"], stdout=FNULL,
                      stderr=FNULL)
    except sp.CalledProcessError:
        print("IPython profile for evo is not installed", file=sys.stderr)
        sp.call([ipython, "profile", "create", "evo"])
        config = os.path.join(PACKAGE_BASE_PATH, "ipython_config.py")
        profile_dir = sp.check_output([ipython, "profile", "locate",
                                       "evo"]).decode("utf-8")
        profile_dir = profile_dir.rstrip()
        shutil.copy(config, os.path.join(profile_dir, "ipython_config.py"))
    try:
        sp.check_call([python, "-m", "IPython", "--profile", "evo"] +
                      other_args)
    except sp.CalledProcessError as e:
        print("IPython error", e.output, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
