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

from __future__ import print_function

import os
import six
import sys
import argparse
import argcomplete
import subprocess as sp

from evo.tools.compat import which

DESC = '''
Launches an IPython shell with pre-loaded evo modules
(c) michael.grupp@tum.de

Unknown command line arguments are forwarded to the ipython executable
'''


def main():
    main_parser = argparse.ArgumentParser(description=DESC,
                                          formatter_class=argparse.RawTextHelpFormatter)
    args, other_args = main_parser.parse_known_args()
    other_args = [] if other_args is None else other_args
    FNULL = open(os.devnull, 'w')

    # check if IPython is installed properly
    ipython = "ipython3" if six.PY3 else "ipython2"
    if which(ipython) is None:
        # fall back to the non-explicit ipython name if ipython2/3 is not in PATH
        ipython = "ipython"
        if which(ipython) is None:
            print("IPython is not installed", file=sys.stderr)
            sys.exit(1)

    try:
        sp.check_call([ipython, "profile", "locate", "evo"], stdout=FNULL, stderr=FNULL)
    except sp.CalledProcessError:
        print("IPython profile for evo is not installed", file=sys.stderr)
        sys.exit(1)
    try:
        sp.check_call([ipython, "--profile", "evo"] + other_args)
    except sp.CalledProcessError as e:
        print("IPython error", e.output, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
