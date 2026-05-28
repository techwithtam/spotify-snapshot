# Spotify Snapshot

A tiny monthly automation that turns your Liked Songs into a clean, dated
playlist instead of one infinite scroll. On the 1st of every month, this
script finds every track you saved in the prior month and adds them to a
playlist named `Your Favorites YYYY-MM`. Re-running for the same month is
safe; it replaces contents instead of duplicating.

Full write-up + the live archive of my own monthly snapshots:
**https://techwithtam.com/resources/spotify-snapshot**

## Hand this to your agent

The fastest way to use this: open Claude Code, Hermes, Open Code, or Codex,
point it at this repo, and say:

> Read AGENTS.md and set up this Spotify monthly snapshot automation on my
> machine for my Spotify account. Walk me through any permissions I need to
> grant.

`AGENTS.md` is the step-by-step procedure your agent follows. It includes
the Spotify Developer dashboard setup, the one-time OAuth helper, a smoke
test, and the right scheduler for your OS (`launchd` on Mac, `cron` on
Linux, Task Scheduler on Windows). You don't have to read the rest of this
README unless you want to.

## What's in the repo

| File | What it is |
| --- | --- |
| `spotify_monthly_snapshot.py` | The actual automation. Runs once a month. |
| `get_refresh_token.py` | One-time helper to authorize on Spotify. |
| `launchd.plist.example` | macOS scheduler template (`launchd`). |
| `requirements.txt` | Just `httpx`. |

## Manual setup (if you want to do it yourself)

### 1. Spotify Developer app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and click **Create app**.
2. Add a Redirect URI. **Use `127.0.0.1`, not `localhost`**. Spotify now rejects `localhost` on many accounts. Example: `http://127.0.0.1:43827/spotify/callback`.
3. Copy the Client ID and Client Secret.

### 2. One-time refresh token

```sh
pip install -r requirements.txt
SPOTIFY_CLIENT_ID=your_id \
SPOTIFY_CLIENT_SECRET=your_secret \
SPOTIFY_REDIRECT_URI=http://127.0.0.1:43827/spotify/callback \
python3 get_refresh_token.py
```

Your browser opens to Spotify, you click Agree, and a refresh token prints
in the terminal. Save it.

The redirect URI you pass here MUST match what you set in the dashboard, character for character. Same scheme, same port, same path.

### 3. Try it once by hand

```sh
SPOTIFY_CLIENT_ID=your_id \
SPOTIFY_CLIENT_SECRET=your_secret \
SPOTIFY_REFRESH_TOKEN=your_refresh_token \
python3 spotify_monthly_snapshot.py
```

That creates last month's snapshot. Confirm it's in your Spotify library.

### 4. Schedule it

The right tool depends on your OS:

- **macOS:** Edit `launchd.plist.example`, save it as `~/Library/LaunchAgents/com.YOU.spotify-snapshot.plist`, then `launchctl load <that path>`. `launchd` catches up on next wake if your Mac was asleep at fire time.
- **Linux:** Add a crontab line: `5 0 1 * * /usr/bin/env SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... SPOTIFY_REFRESH_TOKEN=... python3 /path/to/spotify_monthly_snapshot.py`.
- **Windows:** Use Task Scheduler. Create a task that runs `python.exe spotify_monthly_snapshot.py` monthly on day 1 with the three env vars set.

## CLI flags

```
--year YYYY          Backfill a specific year.
--month MM           Backfill a specific month (1-12).
--name-template STR  Customize the playlist name. Default: "Your Favorites {year}-{month:02d}".
--public             Make the new playlist public. Default is private.
```

Backfill example:

```sh
python3 spotify_monthly_snapshot.py --year 2024 --month 3
```

## What it does NOT do

- Move the playlist into a folder. Spotify's Web API doesn't expose folders. You'll drag new snapshots into your folder by hand the first time you see them.
- Sync across multiple Spotify accounts. One account per setup.
- Fetch full play counts. Spotify's API only exposes ~50 recent plays.

## License

MIT.
