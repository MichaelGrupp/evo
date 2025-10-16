"""
Provides functionality for loading and resetting the package settings.
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

import json
import logging
import typing
from pathlib import Path

from colorama import Fore

from evo import EvoException, __version__

logger = logging.getLogger(__name__)

USER_ASSETS_PATH = Path.home() / ".evo"
USER_ASSETS_VERSION_PATH = USER_ASSETS_PATH / "assets_version"
DEFAULT_PATH = USER_ASSETS_PATH / "settings.json"
GLOBAL_LOGFILE_PATH = USER_ASSETS_PATH / "evo.log"


class SettingsException(EvoException):
    pass


class SettingsContainer(dict):
    def __init__(self, data: dict, lock: bool = True):
        super(SettingsContainer, self).__init__()
        for k, v in data.items():
            setattr(self, k, v)
        setattr(self, "__locked__", lock)

    @classmethod
    def from_json_file(cls, settings_path: Path) -> "SettingsContainer":
        with open(settings_path) as settings_file:
            data = json.load(settings_file)
        return SettingsContainer(data)

    def locked(self) -> bool:
        if "__locked__" in self:
            return self["__locked__"]
        return False

    def __getattr__(self, attr):
        # allow dot access
        if attr not in self:
            raise SettingsException("unknown settings parameter: " + str(attr))
        return self[attr]

    def __setattr__(self, attr, value):
        # allow dot access
        if self.locked() and attr not in self:
            raise SettingsException(
                "write-access locked, can't add new parameter {}".format(attr)
            )
        else:
            self[attr] = value

    def update_existing_keys(self, other: dict):
        self.update((key, other[key]) for key in self.keys() & other.keys())


def merge_dicts(first: dict, second: dict, soft: bool = False) -> dict:
    if soft:
        first.update({k: v for k, v in second.items() if k not in first})
    else:
        first.update(second)
    return first


def write_to_json_file(json_path: Path, dictionary: dict) -> None:
    with open(json_path, "w") as json_file:
        json_file.write(json.dumps(dictionary, indent=4, sort_keys=True))


def reset(
    destination: Path = DEFAULT_PATH,
    parameter_subset: typing.Optional[typing.Sequence] = None,
) -> None:
    from evo.tools.settings_template import DEFAULT_SETTINGS_DICT

    if not destination.exists() or parameter_subset is None:
        write_to_json_file(destination, DEFAULT_SETTINGS_DICT)
    elif parameter_subset:
        reset_settings = json.load(open(destination))
        for parameter in parameter_subset:
            if parameter not in DEFAULT_SETTINGS_DICT:
                continue
            reset_settings[parameter] = DEFAULT_SETTINGS_DICT[parameter]
        write_to_json_file(destination, reset_settings)


def initialize_if_needed() -> None:
    """
    Initialize evo user folder after first installation
    (or if it was deleted).
    """
    if not USER_ASSETS_PATH.exists():
        USER_ASSETS_PATH.mkdir()

    if not USER_ASSETS_VERSION_PATH.exists():
        open(USER_ASSETS_VERSION_PATH, "w").write(__version__)

    if not DEFAULT_PATH.exists():
        try:
            reset(destination=DEFAULT_PATH)
            print(
                "{}Initialized new {}{}".format(
                    Fore.LIGHTYELLOW_EX, DEFAULT_PATH, Fore.RESET
                )
            )
        except:
            logger.error(
                "Fatal: failed to write package settings file {}".format(
                    DEFAULT_PATH
                )
            )
            raise


def update_if_outdated() -> None:
    """
    Update user settings to a new version if needed.
    """
    if open(USER_ASSETS_VERSION_PATH).read() == __version__:
        return
    from evo.tools.settings_template import DEFAULT_SETTINGS_DICT

    old_settings = json.loads(open(DEFAULT_PATH).read())
    updated_settings = merge_dicts(
        old_settings, DEFAULT_SETTINGS_DICT, soft=True
    )
    write_to_json_file(DEFAULT_PATH, updated_settings)
    open(USER_ASSETS_VERSION_PATH, "w").write(__version__)
    print(
        "{}Updated outdated {}{}".format(
            Fore.LIGHTYELLOW_EX, DEFAULT_PATH, Fore.RESET
        )
    )


# Load the user settings into this container.
initialize_if_needed()
update_if_outdated()
SETTINGS = SettingsContainer.from_json_file(DEFAULT_PATH)
