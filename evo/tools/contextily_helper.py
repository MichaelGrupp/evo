"""
Helper functions for using the contextily lib.
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

import logging

import contextily as cx
import xyzservices.lib

from evo import EvoException
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)


class ContextilyHelperException(EvoException):
    pass


# https://xyzservices.readthedocs.io/en/stable/api.html#xyzservices.TileProvider.requires_token
API_TOKEN_PLACEHOLDER = "<insert your "


def add_api_token(
        provider: xyzservices.TileProvider) -> xyzservices.TileProvider:
    """
    Adds the API token stored in the settings, if the provider requires one.
    No-op if the provider requires none.
    :param provider: provider to which the API token shall be added
    :return: provider, either unchanged or with token set
    """
    if not provider.requires_token():
        return provider

    if SETTINGS.map_tile_api_token == "":
        raise ContextilyHelperException(
            f"Map tile provider {provider.name} requires an API token. "
            "Please set it with: evo_config set map_tile_api_token <token>")

    # Attribute name of API token varies, search it using the placeholder
    # defined by the xyzservices documentation and corresponding to:
    # https://github.com/geopandas/xyzservices/blob/8865842123316699feb7e98215c7644533340f83/xyzservices/lib.py#L506
    # TODO: can this be solved smarter in the xyzservices lib?
    api_key = None
    for key, value in provider.items():
        if isinstance(
                value, str
        ) and API_TOKEN_PLACEHOLDER in value and key in provider.url:
            api_key = key
            break
    if not api_key:
        raise ContextilyHelperException(
            "Failed to find API key attribute "
            f"in map tile provider {provider.name}")

    provider[api_key] = SETTINGS.map_tile_api_token
    return provider


def get_provider(provider_str: str) -> xyzservices.TileProvider:
    """
    Retrieve the tile provider from the contextily provider dictionary
    using a string representation of the provider, e.g.:
        - "OpenStreetMap.Mapnik"
        - "MapBox"
    :param provider_str: provider as string
    :return: tile provider corresponding to the string
    """
    # Expects either <bunch>.<provider> or <provider> syntax.
    parts = provider_str.split(".")
    if len(parts) == 1:
        # e.g. "MapBox"
        provider = getattr(cx.providers, parts[0])
    elif len(parts) == 2:
        # e.g. "OpenStreetMap.Mapnik"
        provider = getattr(getattr(cx.providers, parts[0]), parts[1])
    else:
        raise ContextilyHelperException(
            "Expected tile provider in a format "
            "like: 'OpenStreetMap.Mapnik' or 'MapBox'.")

    if type(provider) is xyzservices.Bunch:
        raise ContextilyHelperException(
            f"{provider_str} points to Bunch, not a TileProvider")

    provider = add_api_token(provider)

    return provider
