"""
stuff related to package settings
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
import json
import logging

from colorama import Fore

from evo.tools.settings_template import DEFAULT_SETTINGS_DICT

logger = logging.getLogger(__name__)

PACKAGE_BASE_PATH = os.path.abspath(__file__ + "/../../")
PACKAGE_VERSION = open(os.path.join(PACKAGE_BASE_PATH, "version")).read()
USER_ASSETS_PATH = os.path.join(os.path.expanduser('~'), ".evo")
USER_ASSETS_VERSION_PATH = os.path.join(USER_ASSETS_PATH, "assets_version")
DEFAULT_PATH = os.path.join(USER_ASSETS_PATH, "settings.json")
DEFAULT_LOGFILE_PATH = os.path.join(USER_ASSETS_PATH, "evo.log")


class SettingsException(Exception):
    pass

    
class SettingsContainer(dict):
    def __init__(self, settings_path, data=None, lock=True):
        super(SettingsContainer, self).__init__()
        try:
            if not data:
                with open(settings_path) as settings_file:
                    data = json.load(settings_file)
            for k, v in data.items():
                setattr(self, k, v)
            setattr(self, "__locked__", lock)
        except Exception as e:
            logger.error(str(e))
            raise SettingsException("fatal: failed to load package settings file " + settings_path)

    def locked(self):
        if "__locked__" in self:
            return self["__locked__"]

    def __getattr__(self, attr):
        # allow dot access
        if not attr in self:
            raise SettingsException("unknown settings parameter: " + str(attr))
        return self[attr]

    def __setattr__(self, attr, value):
        # allow dot access
        if self.locked() and not attr in self:
            raise SettingsException("write-access locked, can't add new parameter {}".format(attr))
        else:
            self[attr] = value


def merge_dicts(first, second, soft=False):
    if soft:
        first.update({k: v for k, v in second.items() if not k in first})
    else:
        first.update(second)
    return first


def reset(dest=DEFAULT_PATH):
    with open(dest, 'w') as cfg_file:
        cfg_file.write(json.dumps(DEFAULT_SETTINGS_DICT, indent=4, sort_keys=True))
    

# initialize .evo user folder after first installation (or if it was deleted)
if not os.path.isdir(USER_ASSETS_PATH):
    os.makedirs(USER_ASSETS_PATH)

if not os.path.exists(USER_ASSETS_VERSION_PATH):
    open(os.path.join(USER_ASSETS_PATH, "assets_version"), 'w').write(PACKAGE_VERSION)

if not os.path.exists(DEFAULT_PATH):
    try:
        reset()
        print(Fore.LIGHTYELLOW_EX + "Initialized new " + DEFAULT_PATH + Fore.RESET)
    except:
        print(Fore.LIGHTRED_EX
            + "fatal: failed to write package settings file " + DEFAULT_PATH + Fore.RESET)
        raise

if not open(USER_ASSETS_VERSION_PATH).read() == PACKAGE_VERSION:
    old_settings = json.loads(open(DEFAULT_PATH).read())
    updated_settings = merge_dicts(old_settings, DEFAULT_SETTINGS_DICT, soft=True)
    with open(DEFAULT_PATH, 'w') as cfg_file:
        cfg_file.write(json.dumps(updated_settings, indent=4, sort_keys=True))
    open(os.path.join(USER_ASSETS_PATH, "assets_version"), 'w').write(PACKAGE_VERSION)
    print(Fore.LIGHTYELLOW_EX + "Updated outdated " + DEFAULT_PATH + Fore.RESET)


# load the user settings into this container
SETTINGS = SettingsContainer(DEFAULT_PATH)
