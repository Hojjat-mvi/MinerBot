# Git-based deployment to ParsPack

Repository: git@github.com:Hojjat-mvi/MinerBot.git
Branch: main
Deploy in `/opt/minerbot` as a separate Docker Compose project. No ports are
published; the existing website keeps its current configuration.

## First deployment

On the VPS (replace SERVER_IP):

```bash
ssh root@SERVER_IP
git --version
docker compose version
free -h
df -h
```

For a private repository, give the VPS access using a read-only GitHub deploy
key. Add only its public key in GitHub → repository Settings → Deploy keys.
Never copy your PC private SSH key to the VPS. Check access with
`git ls-remote git@github.com:Hojjat-mvi/MinerBot.git HEAD`.

Clone and configure on the VPS:

```bash
git clone --branch main git@github.com:Hojjat-mvi/MinerBot.git /opt/minerbot
cd /opt/minerbot
chmod 700 /opt/minerbot
cp .env.example .env
chmod 600 .env
nano .env
```

Enter your bot token, channel settings, XT affiliate key/secret, referral code
`7YX74I`, and registration URL. Replace credentials previously shared in chat.
Configure `XT_REWARD_CHANNEL_ID` with the private numeric channel ID and
`TRADE_ADMIN_IDS` with trusted Telegram admin IDs. The bot needs Invite Users
permission in the private channel. Revoke the old shared invite in Telegram;
`XT_REWARD_CHANNEL_URL` is legacy and is no longer distributed.
The bot must be an administrator in both required public channels. If XT has an
IP allowlist, authorize the VPS public outbound IP. Enable server time sync for
signed API requests. `.env` is local to each machine and never committed.

Build before stopping the PC instance:

```bash
docker compose config --quiet
docker compose build bot
```

After a successful build, stop the PC instance from the PC project directory:

```bash
docker compose stop bot
```

Then start on the VPS:

```bash
cd /opt/minerbot
docker compose up -d bot
docker compose ps
docker compose logs --tail 100 -f bot
```

Ctrl+C leaves log following without stopping the bot. Run only one polling
instance per bot token. Test `/menu`, both channel gates, all four devices, and XT
eligibility in Telegram. A running container alone is not a connectivity check.
The bot needs outbound HTTPS to Telegram, XT, and its media hosts.

## Updates through Git

Commit and push changes from the PC. Then on the VPS:

```bash
cd /opt/minerbot
git pull --ff-only origin main
docker compose up -d --build bot
docker compose logs --tail 100 bot
```

After editing server `.env`, `docker compose up -d bot` recreates the container
when its resolved configuration changes; using `--force-recreate` makes that
explicit. No source archive or manual source upload is used.
If a pull fails because of local changes, inspect them rather than overwriting.
Keep the previous working commit SHA for rollback. Stop the VPS bot before
restarting a PC fallback instance.

## Secure reward rollout

1. Revoke all old shared automatic-entry VIP invites in Telegram. Review members
   already admitted through them. New code cannot revoke an invite made by another
   administrator or undo previous admissions automatically.
2. Add the bot as an administrator of the VIP channel with Invite Users rights.
3. Set `XT_REWARD_CHANNEL_ID=-100...` and `TRADE_ADMIN_IDS=123456,...` in server `.env`.
4. Back up SQLite before deploying its additive security-table migration.
5. After an eligible user's ownership is independently verified, a trusted admin
   sends `/approveuid TELEGRAM_USER_ID XT_UID` to the bot in a private chat.
6. The user repeats the check and gets a 10-minute identity-bound join-request
   link. Membership and XT conditions are checked again before approval.

Do not approve ownership merely because someone supplies a working UID.
The API cannot prove control of the exchange account. Existing eligible rows
require review; no automatic first-claim ownership is accepted. A UID cannot
be approved for two Telegram IDs. Binding reassignment has no public command.

Unknown/foreign/expired requests to the configured VIP channel are declined.
Coordinate paid/manual member admissions with channel administrators; requests
using external links are not auto-approved. Avoid other auto-entry invites or
manual approvals that bypass the checks. This bot guards new requests, not
existing member access or continuous balance conditions. Total-deposit rules and
XT's historical coverage limitation remain unchanged.

Phone deletion invalidates pending links but retains the security binding and
persistent rate limit, so it cannot reset a used UID. Back up the complete SQLite
file; do not restore only contact rows. All these records survive Docker rebuilds.
The bot stores link hashes, not generated invite URLs, and redacts invite URLs in logs.

## Operational limits

The container limits RAM to 256 MB and CPU to half a core, rotates logs, and
restarts unless stopped. Monitor with `docker stats --no-stream`. Slow XT queries
can delay replies. Restarts reset pending UID conversations and cooldowns.
XT history coverage/valuation needs confirmation. A live referred account below
100 was tested; a live qualifying account has not yet been tested. The 10-channel
model currently uses a text card. No remote deployment has been performed yet.

## Phone database deployment

The updated Compose file provisions `minerbot_bot_data` and mounts it writable
at `/app/data`; the rest of the container remains read-only. The Dockerfile sets
ownership for the bot's non-root user on first volume creation. A normal
`git pull --ff-only origin main` plus `docker compose up -d --build bot` provisions
this on first upgrade. No additional packages or database server are required.

Preserve the Compose project name `minerbot` so updates reuse the same volume.
Never use `down -v` or delete the data volume during upgrades. Rebuilding the
image and recreating the container preserve saved contacts. Back up the database
with the bot stopped and keep backups private. `/deletephone` removes the user's
active record, but historical operator backups require a separate retention policy.

## Discover a private channel ID with forwarding disabled

1. In a private chat with this bot, send `/myid`. It returns only your own numeric
   Telegram user ID and does not require the VIP channel to be configured.
2. Put that ID in server `.env`: `TRADE_ADMIN_IDS=YOUR_ID`. Restart the bot to load it.
3. Privately send `/channelid`. Only configured admins receive a 10-minute code.
4. Publish the exact code as a new text post in the VIP channel. Both you and the
   bot must be channel administrators. Forwarding is not used or required.
5. The bot privately reports `XT_REWARD_CHANNEL_ID=-100...`. Save it in server
   `.env` and recreate the container. Discovery does not change configuration itself.

Unknown and expired codes are ignored. The requester must also be a channel
administrator before its ID is disclosed. Codes are one-time and kept in memory;
after a restart, request a new code. The bot attempts to delete the setup post
when permissions permit. Discovery results go only to the requesting admin. The setup-code post is visible
to channel subscribers until it is deleted; it is not an invite or account credential.
