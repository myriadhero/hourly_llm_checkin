import logging
import os
from pathlib import Path


def _is_verbose() -> bool:
    raw = os.getenv("LOG_VERBOSE", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handlers: list[logging.Handler] = []
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    log_dir = os.getenv("LOG_DIR")
    if log_dir:
        path = Path(log_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path / "hourly_llm_checkin.log")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)

    noisy_loggers = ["telegram", "telegram.ext", "httpx", "httpcore"]
    if _is_verbose():
        for name in noisy_loggers:
            logging.getLogger(name).setLevel(logging.NOTSET)
    else:
        for name in noisy_loggers:
            logging.getLogger(name).setLevel(logging.WARNING)
