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

The user chooses Trade → Check account → enters their UID. The bot:

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

This checks the **submitted UID**, not ownership of that XT account. It does not
bind a Telegram identity to an exchange identity or grant trading privileges or access to funds. Account-ownership verification would
need an additional agreed process before introducing such privileges.

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

## Optional private-channel reward

Set `XT_REWARD_CHANNEL_URL` in the machine's `.env` when your private channel is
ready (for example `https://t.me/+INVITE_CODE`). Until then, keep it blank: users
who pass both XT conditions see an eligibility-confirmed/reward-pending message.
With a link configured, a fresh successful check shows the private-channel join
button. Failed referrals, low deposits, and API errors never receive that link.
The reward link is redacted from logs and hidden in Settings representations.

This is a shareable static invite, not identity binding or single-use admission.
People may submit someone else's eligible UID or forward the invite. Before
using this as strict access control, add account-ownership verification and
controlled channel admission. These are not provided by the XT UID endpoints.
