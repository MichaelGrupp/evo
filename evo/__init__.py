import logging
import sys
from pathlib import Path

# https://docs.python.org/3/howto/logging.html#library-config
from logging import NullHandler

if sys.version_info < (3, 10):
    raise Exception("evo requires Python 3.10 or higher.")

logging.getLogger(__name__).addHandler(NullHandler())

PACKAGE_BASE_PATH = Path(__file__).absolute().parent

__version__ = "v1.34.1"


class EvoException(Exception):
    def __init__(self, *args, **kwargs):
        # Python 3 base exception doesn't have "message" anymore, only args.
        # We restore it here for convenience.
        self.message = args[0] if len(args) >= 1 else ""
        super(EvoException, self).__init__(*args, **kwargs)
