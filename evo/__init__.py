import logging
import os

# https://docs.python.org/3/howto/logging.html#library-config
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:

    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


logging.getLogger(__name__).addHandler(NullHandler())

PACKAGE_BASE_PATH = os.path.dirname(os.path.abspath(__file__))

__version__ = open(os.path.join(PACKAGE_BASE_PATH,
                                "version")).read().splitlines()[0]


class EvoException(Exception):
    def __init__(self, *args, **kwargs):
        # Python 3 base exception doesn't have "message" anymore, only args.
        # We restore it here for convenience.
        self.message = args[0] if len(args) >= 1 else ""
        super(EvoException, self).__init__(*args, **kwargs)
