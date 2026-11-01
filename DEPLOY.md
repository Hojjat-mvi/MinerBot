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
Leave `XT_REWARD_CHANNEL_URL` blank until the reward channel is ready. Later set
it to a private invite URL such as `https://t.me/+INVITE_CODE`.
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

## Reward behavior

- Fresh XT eligibility success plus a configured reward URL shows a private join button.
- A blank URL shows that eligibility is met and the reward link is not ready.
- Referral/deposit failure or an API error never sends the reward link.
- This is a static invite URL; recipients can forward it. Single-use invites,
  join-request approval, and Telegram-to-XT account ownership verification are
  not implemented. An entered UID alone is not proof of ownership.

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
