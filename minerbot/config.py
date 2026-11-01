"""Load runtime settings without exposing the bot token."""

import os
import re
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = BASE_DIR / "asset"


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    data_dir: Path = BASE_DIR / "data"
    required_channel_id: str = "@Ahuraminenode"
    channel_url: str = "https://t.me/Ahuraminenode"
    additional_channel_ids: tuple[str, ...] = ("@ahuramine",)

    xt_api_key: str = field(default="", repr=False)
    xt_api_secret: str = field(default="", repr=False)
    xt_referral_code: str = ""
    xt_referral_url: str = ""
    xt_reward_channel_url: str = field(default="", repr=False)

    @property
    def xt_ready(self) -> bool:
        return bool(self.xt_api_key and self.xt_api_secret and self.xt_referral_code)

    @property
    def required_channels(self) -> tuple[tuple[str, str], ...]:
        channels = [(self.required_channel_id, self.channel_url)]
        seen = {self.required_channel_id.casefold()}
        for channel in self.additional_channel_ids:
            if channel.casefold() not in seen:
                channels.append((channel, f"https://t.me/{channel.lstrip('@')}"))
                seen.add(channel.casefold())
        return tuple(channels)


def load_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("Set BOT_TOKEN in the project .env file or environment.")
    reward_url = os.getenv("XT_REWARD_CHANNEL_URL", "").strip()
    if reward_url:
        parsed = urlsplit(reward_url)
        if (parsed.scheme != "https" or parsed.netloc != "t.me" or parsed.query or parsed.fragment
                or not re.fullmatch(r"/(?:\+|joinchat/)[A-Za-z0-9_-]+", parsed.path)):
            raise ValueError("XT_REWARD_CHANNEL_URL must be a private Telegram invite URL (https://t.me/+...).")
    return Settings(
        token=token,
        data_dir=Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).expanduser().resolve(),
        required_channel_id=os.getenv("REQUIRED_CHANNEL_ID", "@Ahuraminenode"),
        channel_url=os.getenv("CHANNEL_URL", "https://t.me/Ahuraminenode"),
        xt_api_key=os.getenv("XT_API_KEY", "").strip(),
        xt_api_secret=os.getenv("XT_API_SECRET", "").strip(),
        xt_referral_code=os.getenv("XT_REFERRAL_CODE", "").strip(),
        xt_referral_url=os.getenv("XT_REFERRAL_URL", "").strip(),
        xt_reward_channel_url=reward_url,
        additional_channel_ids=tuple(
            channel.strip() for channel in os.getenv("ADDITIONAL_CHANNEL_IDS", "@ahuramine").split(",")
            if channel.strip()
        ),
    )
