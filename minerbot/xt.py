"""Read-only XT affiliate eligibility checks; no orders, transfers, or withdrawals."""

import asyncio
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from urllib.parse import urlencode

import httpx

from .config import Settings

UID_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_uid(value: str) -> str | None:
    value = value.strip().translate(UID_TRANSLATION)
    if not re.fullmatch(r"[1-9][0-9]{0,18}", value):
        return None
    return value if int(value) <= 9223372036854775807 else None


class XTUnavailable(Exception):
    """Request failed or returned ambiguous data; never approve eligibility."""


@dataclass(frozen=True)
class Eligibility:
    referred: bool
    sufficient_deposit: bool = False

    @property
    def eligible(self) -> bool:
        return self.referred and self.sufficient_deposit


def signed_headers(app_key: str, secret: str, path: str, query: str, timestamp: int) -> dict[str, str]:
    headers = {
        "validate-algorithms": "HmacSHA256",
        "validate-appkey": app_key,
        "validate-recvwindow": "5000",
        "validate-timestamp": str(timestamp),
    }
    original = "&".join(f"{key}={value}" for key, value in sorted(headers.items()))
    original += f"#GET#{path}#{query}"
    headers["validate-signature"] = hmac.new(secret.encode(), original.encode(), hashlib.sha256).hexdigest()
    headers["Content-Type"] = "application/json"
    return headers


class XTVerifier:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def _get(self, client: httpx.AsyncClient, path: str, uid: str):
        # A shared limit across Telegram users, including every step of a check.
        async with self._lock:
            delay = 0.5 - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            query = urlencode({"uid": uid})
            headers = signed_headers(self.settings.xt_api_key, self.settings.xt_api_secret,
                                     path, query, time.time_ns() // 1_000_000)
            self._last_request = time.monotonic()
            try:
                response = await client.get(f"https://api.xt.com{path}?{query}", headers=headers)
                response.raise_for_status()
                data = json.loads(response.text, parse_float=Decimal)
            except (httpx.HTTPError, ValueError):
                raise XTUnavailable("XT request unavailable") from None
            if not isinstance(data, dict) or type(data.get("rc")) is not int or data["rc"] != 0 or "result" not in data:
                raise XTUnavailable("XT rejected request or returned invalid data")
            return data["result"]

    async def verify(self, uid: str) -> Eligibility:
        if not self.settings.xt_ready or normalize_uid(uid) != uid:
            raise XTUnavailable("XT verification is not configured or UID is invalid")
        # Redirects are disabled so signed headers cannot be forwarded to another host.
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=self.transport) as client:
            invited = await self._get(client, "/v4/referal/invite/check", uid)
            if type(invited) is not bool:
                raise XTUnavailable("Invalid referral response")
            if not invited:
                return Eligibility(referred=False)
            info = await self._get(client, "/v4/referal/invite/single/user/info", uid)
            if not isinstance(info, dict) or str(info.get("uid")) != uid:
                raise XTUnavailable("User identity mismatch")
            code = info.get("registerInviteCode")
            if not isinstance(code, (str, int)) or isinstance(code, bool):
                raise XTUnavailable("Registration referral code unavailable")
            if str(code) != self.settings.xt_referral_code:
                return Eligibility(referred=False)
            deposits = await self._get(client, "/v4/referal/invite/user/data", uid)
            if not isinstance(deposits, dict) or str(deposits.get("userId")) != uid:
                raise XTUnavailable("Deposit identity mismatch")
            details = deposits.get("depositDetails")
            if not isinstance(details, list):
                raise XTUnavailable("Deposit records unavailable")
            total = Fraction(0)
            for record in details:
                if not isinstance(record, dict) or isinstance(record.get("amountU"), bool):
                    raise XTUnavailable("Invalid deposit record")
                try:
                    amount = Decimal(str(record["amountU"]))
                except (KeyError, InvalidOperation, ValueError):
                    raise XTUnavailable("Deposit valuation unavailable") from None
                if not amount.is_finite() or amount < 0:
                    raise XTUnavailable("Invalid deposit valuation")
                # Bound malformed exponent/precision sizes before exact rational conversion.
                if len(amount.as_tuple().digits) > 100 or abs(amount.as_tuple().exponent) > 100:
                    raise XTUnavailable("Unsupported deposit precision")
                total += Fraction(amount)
            return Eligibility(referred=True, sufficient_deposit=total >= 100)
