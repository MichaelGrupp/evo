# -*- coding: UTF8 -*-
"""
cross-compatible functions as a workaround until we can drop Python 2.7
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


def which(executable):
    """
    behaves like shutil.which() from Python 3.3+
    :param executable: string
    :return: path of the executable or None
    """
    if sys.version_info >= (3, 3):
        import shutil
        return shutil.which(executable)
    else:
        from distutils.spawn import find_executable
        path = find_executable(executable)
        if path is not None:
            return path if os.access(path, os.X_OK) else None
        else:
            return path
