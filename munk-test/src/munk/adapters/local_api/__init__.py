from __future__ import annotations

from typing import Any


def create_local_api_app(*args: Any, **kwargs: Any):  # noqa: ANN201
    from .app import create_local_api_app as _create_local_api_app

    return _create_local_api_app(*args, **kwargs)


def serve_local_api(*args: Any, **kwargs: Any):  # noqa: ANN201
    from .server import serve_local_api as _serve_local_api

    return _serve_local_api(*args, **kwargs)

__all__ = ["create_local_api_app", "serve_local_api"]
