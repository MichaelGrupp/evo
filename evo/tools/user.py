"""
user interaction functions
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
import logging

logger = logging.getLogger(__name__)

# Python 2/3 compatibility
try:
    input = raw_input
except NameError:
    pass


def prompt_val(msg="enter a value:"):
    return input(msg + "\n")


def confirm(msg="enter 'y' to confirm or any other key to cancel", key='y'):
    if input(msg + "\n") != key:
        return False
    else:
        return True


def check_and_confirm_overwrite(file_path):
    if os.path.isfile(file_path):
        logger.warning(file_path + " exists, overwrite?")
        return confirm("enter 'y' to overwrite or any other key to cancel")
    else:
        return True
