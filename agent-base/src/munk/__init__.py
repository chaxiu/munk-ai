import sys
from pkgutil import extend_path

if not getattr(sys, "frozen", False):
    __path__ = extend_path(__path__, __name__)
