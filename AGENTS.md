# AGENTS.md

This file is for AI coding agents (Claude Code, Codex, Hermes, Open Code,
etc.). It contains the exact setup procedure so the human owner of this repo
does not have to walk you through it. Follow the steps below in order.

## What you're setting up

A monthly cron-style automation that creates a Spotify playlist named
`Your Favorites YYYY-MM` containing every track the user saved in the prior
calendar month. The script is idempotent: re-running for the same month
replaces the playlist's contents instead of duplicating.

## Setup procedure

You will need to do all of the following. **Pause and ask the user** at each
step that requires their input. Do not assume.

### Step 1. Confirm Python and httpx

Check Python 3.10+ is installed:

```sh
python3 --version
```

If missing, instruct the user to install it (Homebrew on Mac, apt on Linux,
python.org installer on Windows).

Install `httpx`:

```sh
python3 -m pip install -r requirements.txt
```

Or in a virtualenv if the user prefers (recommended on Mac to avoid
`externally-managed-environment` errors):

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Step 2. Spotify Developer app

Ask the user to:

1. Go to https://developer.spotify.com/dashboard
2. Click **Create app**.
3. Fill in any name and description.
4. **Redirect URI:** use `http://127.0.0.1:43827/spotify/callback` exactly.
   Do NOT suggest `localhost`. Spotify rejects `localhost` on many accounts.
5. Check **Web API** only.
6. Save, then open the app's **Settings** page.
7. Copy the **Client ID** and **Client Secret** and paste them back to you.

### Step 3. One-time refresh token

Run the helper with the user's Client ID and Secret in env. The redirect URI
MUST be the same value the user set in the dashboard.

```sh
SPOTIFY_CLIENT_ID=<from user> \
SPOTIFY_CLIENT_SECRET=<from user> \
SPOTIFY_REDIRECT_URI=http://127.0.0.1:43827/spotify/callback \
python3 get_refresh_token.py
```

The user's browser will open to Spotify. They click **Agree**. A refresh
token prints in the terminal. Capture it.

Common failure: `redirect_uri_mismatch`. This means the redirect URI in the
dashboard does not exactly match the one you passed via env. Same scheme,
port, and path, character for character.

### Step 4. Smoke test

Before scheduling, prove the script actually works against the user's account.
Run with a TEST name template so it does not collide with their real
playlists:

```sh
SPOTIFY_CLIENT_ID=<id> \
SPOTIFY_CLIENT_SECRET=<secret> \
SPOTIFY_REFRESH_TOKEN=<token> \
python3 spotify_monthly_snapshot.py \
  --year <last completed year> --month <last completed month> \
  --name-template "TEST Snapshot {year}-{month:02d}"
```

Expected output: `created 'TEST Snapshot YYYY-MM' with N tracks.`

Ask the user to confirm the test playlist appears in their Spotify. If yes,
delete it (right-click in Spotify -> Delete). Then proceed.

### Step 5. Schedule it for the 1st of each month

Pick the right scheduler for the user's OS. Do not ask which one to use; pick
based on their machine.

**macOS:** Use `launchd`. Copy `launchd.plist.example`, replace the
placeholders (paths, env vars), save to
`~/Library/LaunchAgents/com.<user>.spotify-snapshot.plist`, then:

```sh
launchctl load ~/Library/LaunchAgents/com.<user>.spotify-snapshot.plist
```

**Linux:** Use `cron`. Add this line via `crontab -e`:

```
5 0 1 * * SPOTIFY_CLIENT_ID=<id> SPOTIFY_CLIENT_SECRET=<secret> SPOTIFY_REFRESH_TOKEN=<token> /usr/bin/env python3 /absolute/path/to/spotify_monthly_snapshot.py
```

(For security, the user may prefer storing env vars in a separate sourced
file rather than inline.)

**Windows:** Use Task Scheduler. Create a task that runs monthly on day 1 at
12:05 AM, action = start `python.exe` with argument
`spotify_monthly_snapshot.py`, working directory = the repo, with the three
env vars set on the action's environment.

### Step 6. Tell the user what's done

Confirm:

- What scheduler was set up (`launchd` plist path, crontab line, Task Scheduler entry).
- When the next run will fire.
- Where logs will go (e.g. `/tmp/spotify-snapshot.log` for `launchd`).
- That the user can re-run any prior month by hand with `--year YYYY --month MM` for backfills.

## Boundaries

- **Do not** commit the user's `SPOTIFY_CLIENT_SECRET` or
  `SPOTIFY_REFRESH_TOKEN` to any git repo. Treat them like passwords.
- **Do not** modify `spotify_monthly_snapshot.py` or `get_refresh_token.py`
  to change the auth flow. If something is wrong, surface the actual error
  to the user.
- **Do not** push the user's edited `launchd.plist` (with their real
  credentials) to a public repo. The `.gitignore` excludes `*.plist`
  precisely to prevent this. Confirm the file is gitignored before doing
  anything with git.
- If the user is on Windows and Python 3 is not installed, stop and tell
  them. Do not try to install it silently.

## Reference: known gotchas

1. Spotify dashboard rejects `localhost`. Always use `127.0.0.1`.
2. The redirect URI in the dashboard and in the env var passed to
   `get_refresh_token.py` must match character-for-character.
3. Spotify's Web API does not expose playlist folders. The script cannot
   automatically file the new playlist into a folder; the user moves it
   manually the first time.
4. Recent `httpx` works fine; older `requests`-based forks need rewrites.

## Companion resource page

The story version of this project, plus a live archive of the original
author's monthly snapshots, lives at:
https://techwithtam.com/resources/spotify-snapshot
