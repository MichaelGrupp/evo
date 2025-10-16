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

from evo.tools._typing import PathStr

logger = logging.getLogger(__name__)


def prompt_val(msg: str = "enter a value:") -> str:
    return input(msg + "\n")


def confirm(
    msg: str = "enter 'y' to confirm or any other key to cancel",
    key: str = "y",
) -> bool:
    if input(msg + "\n") != key:
        return False
    else:
        return True


def check_and_confirm_overwrite(file_path: PathStr) -> bool:
    if os.path.isfile(file_path):
        logger.warning("%s exists, overwrite?", file_path)
        return confirm("enter 'y' to overwrite or any other key to cancel")
    else:
        return True
