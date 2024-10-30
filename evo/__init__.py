import logging
from pathlib import Path

# https://docs.python.org/3/howto/logging.html#library-config
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())

PACKAGE_BASE_PATH = Path(__file__).absolute().parent

__version__ = "v1.30.2"


class EvoException(Exception):
    def __init__(self, *args, **kwargs):
        # Python 3 base exception doesn't have "message" anymore, only args.
        # We restore it here for convenience.
        self.message = args[0] if len(args) >= 1 else ""
        super(EvoException, self).__init__(*args, **kwargs)
