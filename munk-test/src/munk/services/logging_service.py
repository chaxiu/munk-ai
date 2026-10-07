from __future__ import annotations

import logging
from pathlib import Path

from munk.services.events import LogEvent, RunEventSink

MUNK_LOGGER_NAME = "munk"
_MUNK_HANDLER_KIND = "_munk_handler_kind"
_MUNK_FILE_PATH = "_munk_file_path"


class EventLogHandler(logging.Handler):
    def __init__(self, event_sink: RunEventSink | None) -> None:
        super().__init__(level=logging.INFO)
        self._event_sink = event_sink

    def emit(self, record: logging.LogRecord) -> None:
        if self._event_sink is None:
            return
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self._event_sink(
            LogEvent(
                message=message,
                data={"logger": record.name, "level": record.levelname},
            )
        )

    def set_event_sink(self, event_sink: RunEventSink | None) -> None:
        self._event_sink = event_sink


def _mark_handler(handler: logging.Handler, kind: str) -> logging.Handler:
    setattr(handler, _MUNK_HANDLER_KIND, kind)
    return handler


def _handler_kind(handler: logging.Handler) -> str | None:
    return getattr(handler, _MUNK_HANDLER_KIND, None)


def _build_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s %(levelname)s %(message)s")


def _replace_handler(logger: logging.Logger, *, kind: str, handler: logging.Handler) -> None:
    stale_handlers = [existing for existing in logger.handlers if _handler_kind(existing) == kind]
    for existing in stale_handlers:
        logger.removeHandler(existing)
        existing.close()
    logger.addHandler(handler)


def _ensure_stream_handler(logger: logging.Logger, formatter: logging.Formatter) -> None:
    for handler in logger.handlers:
        if _handler_kind(handler) == "stream":
            handler.setFormatter(formatter)
            return
    stream_handler = _mark_handler(logging.StreamHandler(), "stream")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def _ensure_event_handler(
    logger: logging.Logger,
    *,
    formatter: logging.Formatter,
    event_sink: RunEventSink | None,
) -> None:
    for handler in logger.handlers:
        if isinstance(handler, EventLogHandler) and _handler_kind(handler) == "event":
            handler.setFormatter(formatter)
            handler.set_event_sink(event_sink)
            return
    event_handler = _mark_handler(EventLogHandler(event_sink), "event")
    event_handler.setFormatter(formatter)
    logger.addHandler(event_handler)


def _ensure_file_handler(logger: logging.Logger, *, formatter: logging.Formatter, log_path: Path) -> None:
    resolved_log_path = str(log_path.resolve())
    for handler in logger.handlers:
        if _handler_kind(handler) != "file":
            continue
        if getattr(handler, _MUNK_FILE_PATH, None) == resolved_log_path:
            handler.setFormatter(formatter)
            return
    file_handler = _mark_handler(logging.FileHandler(log_path, encoding="utf-8"), "file")
    setattr(file_handler, _MUNK_FILE_PATH, resolved_log_path)
    file_handler.setFormatter(formatter)
    _replace_handler(logger, kind="file", handler=file_handler)


def _ensure_persistent_file_handler(
    logger: logging.Logger,
    *,
    formatter: logging.Formatter,
    log_path: Path,
) -> None:
    resolved_log_path = str(log_path.resolve())
    for handler in logger.handlers:
        if _handler_kind(handler) != "persistent_file":
            continue
        if getattr(handler, _MUNK_FILE_PATH, None) == resolved_log_path:
            handler.setFormatter(formatter)
            return
    file_handler = _mark_handler(logging.FileHandler(log_path, encoding="utf-8"), "persistent_file")
    setattr(file_handler, _MUNK_FILE_PATH, resolved_log_path)
    file_handler.setFormatter(formatter)
    _replace_handler(logger, kind="persistent_file", handler=file_handler)


def setup_logging(log_path: Path, event_sink: RunEventSink | None = None) -> None:
    logger = logging.getLogger(MUNK_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = _build_formatter()
    _ensure_file_handler(logger, formatter=formatter, log_path=log_path)
    _ensure_stream_handler(logger, formatter=formatter)
    _ensure_event_handler(logger, formatter=formatter, event_sink=event_sink)
    logger.info("run_log=%s", log_path)


def setup_persistent_logging(log_path: Path) -> None:
    logger = logging.getLogger(MUNK_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = _build_formatter()
    _ensure_persistent_file_handler(logger, formatter=formatter, log_path=log_path)
    _ensure_stream_handler(logger, formatter=formatter)
    logger.info("persistent_log=%s", log_path)
