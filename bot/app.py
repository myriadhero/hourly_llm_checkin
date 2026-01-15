import logging
import os
from pathlib import Path

from xai_sdk import Client

import track

from .bot import create_application
from .config import get_timezone, load_config
from .logging_utils import configure_logging
from .state import load_state


def main() -> None:
    configure_logging()
    config = load_config()
    tzinfo = get_timezone(config)
    state_path = Path(os.getenv("STATE_PATH", "bot_state.json"))
    state = load_state(state_path)
    track.init_db()
    timeout_raw = os.getenv("XAI_TIMEOUT_SECONDS")
    client_kwargs = {"api_key": config.xai_api_key}
    if timeout_raw:
        try:
            client_kwargs["timeout"] = int(timeout_raw)
        except ValueError:
            logging.warning("Invalid XAI_TIMEOUT_SECONDS=%r, ignoring.", timeout_raw)
    client = Client(**client_kwargs)
    application = create_application(config, state, state_path, tzinfo, client)
    application.run_polling(allowed_updates=None)
