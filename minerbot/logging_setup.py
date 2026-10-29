"""Redact configured credentials, including library exception tracebacks."""

import logging
import traceback

from .config import Settings


class SecretFilter(logging.Filter):
    def __init__(self, settings: Settings):
        super().__init__()
        self._secrets = sorted(
            {value for value in (settings.token, settings.xt_api_key, settings.xt_api_secret, settings.xt_reward_channel_url) if value},
            key=len, reverse=True,
        )

    def _redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[REDACTED]")
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = self._redact("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = self._redact(record.exc_text)
        if record.stack_info:
            record.stack_info = self._redact(record.stack_info)
        return True


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(SecretFilter(settings))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
