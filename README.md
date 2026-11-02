# MinerBot

Persian Telegram product catalog and FAQ bot using polling and async python-telegram-bot.
Requires Python 3.10 or newer; developed and tested with Python 3.11.

## Run locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
```

If `.env` does not exist, copy `.env.example` to `.env`. Set `BOT_TOKEN` to your
existing bot's token. Optional settings are `REQUIRED_CHANNEL_ID` and `CHANNEL_URL`.
Environment variables take precedence over `.env`.

```bash
python bot.py
```

Open the same bot in Telegram and send `/start`. Keep the process running; stop
with Ctrl+C and restart after code changes. Only one polling instance may use the
token. Add the bot as a channel administrator for reliable membership checks.
Polling requires outbound access to Telegram, with no exposed ports or public IP.

The old `wvenv` is a Windows environment; use the new `.venv` on this computer.

## Code map

- `bot.py`: executable entry point.
- `minerbot/application.py`: application construction and handler registration.
- `minerbot/config.py`: environment settings and absolute asset paths.
- `minerbot/content.py`: catalog snapshot, FAQ, commercial figures, and media references.
- `minerbot/catalog.py`: shared USDT price, income, and comparison rendering.
- `minerbot/keyboards.py`: menu and inline keyboard builders.
- `minerbot/handlers.py`: async menu, catalog, and trade eligibility conversations.
- `minerbot/xt.py`: signed read-only XT affiliate API verification.
- `requirements.txt`: direct runtime dependencies.
- `requirements.lock`: exact versions of the installed runtime dependency tree.

## Offline tests

```bash
python -m unittest discover -s tests -v
python -m pip check
```

Tests use mocked Telegram calls and do not contact users or start polling.
Live Telegram connectivity and channel permissions need a manual check.

## Scope of this refactor

The first pass cleans Git tracking, updates dependencies, and separates code by
responsibility. Legacy callback identifiers remain supported on older bot messages.
The async migration also acknowledges callbacks, uses the correct owner status,
closes local media files, and registers a shared error handler.

Membership is checked for menu, message, and callback access.
Further work: add inquiry capture,
verify product specifications and commercial figures with the seller. Sending order
details still receive menu guidance; inquiries are not yet
saved or forwarded.

`.env` and virtual environments are ignored and removed from the Git index, but
remain on disk. This does not remove files from existing Git history. If a real
token was committed previously, revoke it through BotFather and set a new token.

## Telegram interface

The catalog combines a persistent bottom menu with native inline detail buttons,
with blue product choices and green primary actions. Telegram clients control button transparency, blur, and theme;
the bot cannot apply CSS or custom glass materials. Older clients may ignore
button colors. Product cards include short Persian specifications, price, monthly
income estimate, and navigation. Existing models use local photos; the 10-channel
model currently uses a text card because no local photo has been downloaded.

Persian messages use HTML headings and Unicode direction marks. Latin terms
and phone numbers are isolated to preserve reading order. Check the visual
result on your Telegram clients; the API has no paragraph-alignment setting.
Restart the process and send `/start` or `/menu` to restore the persistent bottom
keyboard and see the new interface. Old messages retain their original keyboards.

## Catalog figures

Source: https://ahuraminer.com/products/lightning-nodes (checked 2026-10-27).
This is a local snapshot, not an automatic website sync. Update the product data
in `minerbot/content.py` when the source changes. All cards, detail views, and the
comparison screen render from the same numeric fields.

| Channels | Catalog price (USDT) | Site monthly income estimate (USD) |
| --- | ---: | ---: |
| 2 | 1020 | 50 |
| 4 | 1400 | 75 |
| 6 | 4050 | 250 |
| 10 | 6750 | 410 |

The source labels these catalog figures provisional. Prices are already in USDT;
income is given in USD on the source. The bot labels income as an approximate
USDT equivalent assuming 1 USD ≈ 1 USDT, before expenses, rather than implying
a guaranteed payout in USDT. No exchange-rate API is used. Old prices, stock
claims, and income figures have been replaced.

Use the bottom-menu price/income button to compare all four models. `/menu` and
the Home action restore the persistent keyboard if the user has hidden it.

## Deploy through Git

Follow [DEPLOY.md](DEPLOY.md) to clone this repository on your ParsPack VPS and
run it with Docker Compose. Updates use `git pull --ff-only origin main` followed
by `docker compose up -d --build bot`. Configure `.env` directly on the VPS;
secrets and local virtual environments are not tracked. Stop local polling before
starting the server instance. The website requires no port/proxy changes.

Required membership includes the primary `REQUIRED_CHANNEL_ID` and the comma-separated
usernames in `ADDITIONAL_CHANNEL_IDS` (default: `@ahuramine`). Make the bot an
administrator in every required channel. Users must join all listed channels.

## Two-section menu and XT eligibility

The first menu offers only **Lightning nodes** and **Trade with Ahuramine**.
The existing device menu is inside Lightning nodes; Home and `/menu` return to
the two-section menu. Both channel-membership requirements still apply.

XT verification is optional. The catalog works without XT configuration. Add
the following to your local or server `.env` when the affiliate account is ready:

```dotenv
XT_API_KEY=
XT_API_SECRET=
XT_REFERRAL_CODE=
```

Use credentials from Ahuramine's own XT affiliate account with access to the
referral query endpoints. End users supply only their numeric XT UID. The bot
never asks them for passwords, API keys, or funds. These credentials are sent
only to `https://api.xt.com`, with signed GET requests and redirects disabled.
No XT trade, transfer, or withdrawal API is implemented. If any setting is
missing, the trade screen clearly reports that verification is not yet active.

The user chooses Trade room → Free subscription → Check account → enters their UID. The bot:

1. Calls `GET /v4/referal/invite/check` with that UID.
2. Calls `GET /v4/referal/invite/single/user/info` and compares
   `registerInviteCode` with the configured exact referral code. This extra
   endpoint is necessary because the first endpoint returns only a boolean.
3. Calls `GET /v4/referal/invite/user/data` without time filters and sums
   `depositDetails[].amountU` using exact arithmetic (Decimal parsing and rational summation). Eligibility requires a sum of at
   least 100 USDT-equivalent, including exactly 100. It does not use account
   balance or subtract withdrawals. It does not require trading volume.

The rule is total deposits returned by XT. The docs show `amountU` but do not
specify the endpoint's default historical coverage/retention or valuation
method; confirm complete historical coverage and units with XT before treating
the result as proof of lifetime deposits. Missing fields, wrong UID, invalid
amounts, API errors, and timeouts never approve eligibility.

Checks use a 15-second per-Telegram-user cooldown and shared request pacing.
Telegram input is handled in private chats only. No exact deposit amounts,
financial records, or credentials are sent to Telegram or written to bot logs.
UID entry expires after 10 minutes and is cancelled by navigation.

The XT API checks the submitted UID; it cannot prove account ownership. Secure
VIP admission therefore requires independent admin ownership review before a
persistent binding is approved. No exchange trading or fund-transfer operations
are implemented.

A read-only live check on 2026-10-29 confirmed affiliate API access, an exact
referral-code match, and a below-threshold deposit response for a sample referred
UID. A live above-threshold account has not yet been tested. Tests use synthetic API responses with no live accounts.
After configuring `.env`, restart locally and test with known referred and
unreferred UIDs, plus accounts above and below the threshold.

API references:
- https://doc.xtfarsi.site/docs/Referral%20Commission/Referral%20Commission/CheckIfTheUserIsInvited
- https://doc.xtfarsi.site/docs/Referral%20Commission/Referral%20Commission/GetDepositTradingDataOfUsers
- https://doc.xt.com/docs/Referral%20Commission/Referral%20Commission/QueryUserInformation
- https://doc.xt.com/docs/Referral%20Commission/Access%20Description/SignatureGeneration

### Phone Back button and keyboard dismissal

Both reply menus set `is_persistent=False`, so Telegram can hide them. The menu
buttons remain available via the keyboard icon or `/menu`. Rebuild the Docker
container and send `/menu` to replace the old persistent markup on the client.
The phone Back button is handled by Telegram, not by bot callbacks; the first
press may dismiss an open keyboard before another press leaves the chat.

Set `XT_REFERRAL_URL` to show the registration button in the trade screen.
The configured registration link is https://www.xtfarsi.net/ref/7YX74I.

Deployment review (2026-10-29): exact threshold arithmetic and credential redaction
are covered by regression tests. See `DEPLOY.md` for the ParsPack/root workflow.

## Secure private-channel rewards

Shared invite delivery has been removed. Configure `XT_REWARD_CHANNEL_ID` with
the private channel's numeric `-100...` ID and `TRADE_ADMIN_IDS` with trusted
admin Telegram user IDs (comma-separated). The bot must be channel administrator
with Invite Users permission. `XT_REWARD_CHANNEL_URL` is legacy and is never sent.
Revoke the previously shared invite in Telegram; existing messages cannot be
made safe merely by deploying new code. Review already admitted members manually.

A new eligible UID requires independent account-ownership review by support.
The applicant receives their Telegram ID and contacts support; a configured admin
must confirm control of the XT account before sending the bot:

```text
/approveuid TELEGRAM_USER_ID XT_UID
```

This is an administrative attestation, not automated ownership verification.
UID knowledge or an eligibility result alone is not ownership evidence. The
command accepts only pending requests, checks XT eligibility again, and records
a durable one-UID/one-Telegram-account binding. Pre-existing eligible contact rows
are not silently trusted or bound; they require this review too.

The user then repeats the eligibility check. The bot creates a 10-minute
join-request link, stores only its hash, and associates it with that Telegram ID.
At admission it rechecks phone registration, binding, both public channels, and
XT referral/deposit conditions. Forwarded, expired, unknown, consumed, or replaced
links do not authorize another user. A wrong user's request does not consume
the intended recipient's link. Missing configuration or API failures never fall
back to the legacy shared link. Consumed links are revoked where Telegram allows.

Only links recorded by this flow are auto-approved in the configured channel.
Other join requests are declined; coordinate manual paid admissions separately.
Other admins must not distribute automatic-entry links or approve unverified
users. The bot cannot prevent another channel admin from bypassing these controls.
The condition remains **total deposits**, not current balance or net deposits.
Existing memberships are not automatically removed or continuously monitored.

Deleting a phone invalidates pending invitations and ownership requests but
preserves reward bindings and rate-limit records to prevent UID reuse and reset
abuse. This retained security record is disclosed in the registration/deletion
messages. It is included in the same private SQLite volume and its backups.

## Trade phone registration

Trade entry requires consent-based Telegram contact sharing in a private chat.
The contact's `user_id` must match the sender; typed numbers, other people's
contacts, expired requests, and unsolicited contacts are not saved. Registration
lasts across restarts. Public-channel membership remains required. Lightning
catalog access does not require a phone number. Existing users register once on
their next trade entry; there is no database of prior phones to migrate.

The SQLite database stores Telegram user ID, normalized international phone,
consent/update timestamps, and the submitted XT UID with its latest check status. `/deletephone` removes the contact record and gates
trade entry again. The bot attempts to delete the contact message after saving;
Telegram may prevent message deletion. Bot-database deletion does not erase any
copies already retained by Telegram or previous operator backups.

Docker mounts the named `bot_data` volume at `/app/data`. The database is
`/app/data/contacts.sqlite3`, owned by the non-root bot user with mode 600.
Source-only runs default to `data/contacts.sqlite3`; optional `DATA_DIR` changes
that location. Local databases are excluded from Git and the Docker build context.
Numbers are not included in normal bot logs or echoed back in chat. The database
is not encrypted by the app: restrict host/backup access and protect VPS storage.

Do not use `docker compose down -v` or remove the `minerbot_bot_data` volume:
that deletes the contact database. Keep encrypted access-controlled backups;
stop the bot while copying its database to obtain a consistent backup. There is
no public phone-list/export endpoint. Administrators with server access can
manage the SQLite database directly; do not publish it or commit it to Git.

## Subscription navigation and saved exchange UIDs

Trade-room menu order: دریافت اشتراک → برآیند معاملات → آموزش کار با صرافی XT.
The subscription submenu contains عضویت رایگان کانال VIP and اشتراک با پرداخت هزینه.
The results screen is a placeholder until reports are provided.

A valid submitted XT UID is saved on the registered contact row before its API
check, together with the latest result (`submitted`, `unavailable`, `not_referred`,
`below_threshold`, or `eligible`) and last check-attempt time. A new UID replaces
the previous one for that Telegram account. No raw financial records are stored.
These are self-reported UIDs, not verified account ownership. API errors remain
unavailable and never approve rewards. The user is informed before UID entry.

Existing SQLite phone databases migrate automatically by adding nullable UID
columns, without replacing phone rows. Back up the database before deploying a
schema change. `/deletephone` deletes the contact row and pending admission rights; durable reward bindings remain to prevent reuse.
The existing persistent Docker volume and backup requirements still apply.

### Trade performance and trade support

The performance screen displays the supplied 45-day report with a bold period
heading; it is manually maintained content, not a live exchange performance feed.
Trade support has a single destination, `@Ahurasupport_trading`, including the
paid-subscription screen, account-check screens, and trade-specific errors.
Existing support/sales contacts are retained only in the Lightning section.
Configure secure VIP admission with `XT_REWARD_CHANNEL_ID` and `TRADE_ADMIN_IDS`
on each running machine. Legacy shared invites are never distributed.

Private-channel ID discovery: use `/myid`, configure `TRADE_ADMIN_IDS`, then
`/channelid` and publish its one-time setup code in the channel. See `DEPLOY.md`.
Forwarding is not required; the bot reports the ID privately to the authorized admin.
