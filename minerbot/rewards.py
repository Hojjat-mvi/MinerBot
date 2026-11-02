"""Identity-bound VIP admission. Never distribute the legacy shared invite."""

import hashlib
import logging
import time
from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .xt import XTUnavailable

logger = logging.getLogger(__name__)


class RewardConflict(Exception):
    """A UID or Telegram account is already bound or the request is stale."""


def invite_digest(link: str) -> str:
    return hashlib.sha256(link.encode()).hexdigest()


async def issue_reward(context: ContextTypes.DEFAULT_TYPE, user_id: int, uid: str) -> tuple[str, str | None]:
    settings = context.bot_data["settings"]
    store = context.bot_data["contacts"]
    if store.binding_conflicts(user_id, uid):
        return "conflict", None
    if settings.xt_reward_channel_id is None:
        return "unconfigured", None
    chat = await context.bot.get_chat(settings.xt_reward_channel_id)
    if chat.type != "channel" or chat.username or getattr(chat, "active_usernames", None):
        return "unconfigured", None
    try:
        store.claim_binding(user_id, uid)
    except RewardConflict:
        return "conflict", None
    expires = int(time.time()) + 600
    invite = await context.bot.create_chat_invite_link(
        chat_id=settings.xt_reward_channel_id,
        name=f"vip-{user_id}",
        expire_date=datetime.fromtimestamp(expires, timezone.utc),
        creates_join_request=True,
    )
    try:
        store.save_admission(user_id, uid, settings.xt_reward_channel_id, invite_digest(invite.invite_link), expires)
    except Exception:
        # A database failure must never result in an untracked usable invitation.
        try:
            await context.bot.revoke_chat_invite_link(settings.xt_reward_channel_id, invite.invite_link)
        except TelegramError:
            logger.warning("Could not revoke untracked VIP join-request link")
        raise
    return "invite", invite.invite_link


async def reward_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    request = update.chat_join_request
    settings = context.bot_data["settings"]
    if request is None or settings.xt_reward_channel_id is None or request.chat.id != settings.xt_reward_channel_id:
        return
    store = context.bot_data["contacts"]
    user_id = request.from_user.id
    link = request.invite_link
    record = store.admission_for(invite_digest(link.invite_link)) if link else None
    # Check the sender before consuming: a forwarded link must not lock out its rightful owner.
    if (record is None or record["telegram_user_id"] != user_id or
            record["channel_id"] != request.chat.id or record["expires_at"] <= time.time() or
            not store.has_contact(user_id) or not store.binding_matches(user_id, record["xt_uid"])):
        await context.bot.decline_chat_join_request(request.chat.id, user_id)
        return
    if not store.consume_admission(record["invite_hash"], user_id, time.time()):
        await context.bot.decline_chat_join_request(request.chat.id, user_id)
        return
    try:
        accepted = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
        for channel, _ in settings.required_channels:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status not in accepted:
                await context.bot.decline_chat_join_request(request.chat.id, user_id)
                return
        result = await context.bot_data["xt_verifier"].verify(record["xt_uid"])
        if not result.eligible:
            await context.bot.decline_chat_join_request(request.chat.id, user_id)
            return
        # Re-check local registration after external calls, including any concurrent deletion.
        if not store.has_contact(user_id) or not store.binding_matches(user_id, record["xt_uid"]):
            await context.bot.decline_chat_join_request(request.chat.id, user_id)
            return
        await context.bot.approve_chat_join_request(request.chat.id, user_id)
    except (XTUnavailable, TelegramError):
        # Ambiguous API failures never trigger an approval or a fallback shared link.
        logger.warning("VIP join verification unavailable")
        try:
            await context.bot.decline_chat_join_request(request.chat.id, user_id)
        except TelegramError:
            pass
    finally:
        try:
            await context.bot.revoke_chat_invite_link(request.chat.id, link.invite_link)
        except TelegramError:
            logger.warning("Could not revoke consumed VIP join-request link")
