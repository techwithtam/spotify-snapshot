#!/usr/bin/env python3
"""Create a Spotify playlist from tracks you liked in a target month.

Default target: previous calendar month.
Playlist name: Your Favorites YYYY-MM (override with --name-template).
Re-running for the same month replaces the existing playlist's contents
instead of duplicating it.

Env vars required:
  SPOTIFY_CLIENT_ID
  SPOTIFY_CLIENT_SECRET
  SPOTIFY_REFRESH_TOKEN
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing env: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def access_token() -> str:
    basic = base64.b64encode(
        f"{env('SPOTIFY_CLIENT_ID')}:{env('SPOTIFY_CLIENT_SECRET')}".encode()
    ).decode()
    r = httpx.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": env("SPOTIFY_REFRESH_TOKEN"),
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, **kwargs) -> Any:
    r = httpx.request(
        method,
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
        **kwargs,
    )
    r.raise_for_status()
    return None if r.status_code == 204 else r.json()


def prior_month() -> tuple[int, int]:
    now = datetime.now().astimezone()
    year, month = now.year, now.month - 1
    if month == 0:
        year, month = year - 1, 12
    return year, month


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    return start, end


def liked_tracks_in_month(token: str, year: int, month: int) -> list[dict]:
    start, end = month_bounds(year, month)
    out, seen = [], set()
    offset, limit = 0, 50
    while True:
        page = api("GET", f"/me/tracks?limit={limit}&offset={offset}&market=US", token)
        items = page.get("items") or []
        if not items:
            break
        stop = False
        for item in items:
            added_raw = item.get("added_at")
            track = item.get("track") or {}
            tid = track.get("id")
            if not added_raw or not tid:
                continue
            added = datetime.fromisoformat(added_raw.replace("Z", "+00:00"))
            if start <= added < end and tid not in seen:
                out.append(item)
                seen.add(tid)
            elif added < start:
                stop = True
        offset += limit
        if stop or offset >= int(page.get("total") or 0):
            break
    out.sort(key=lambda i: i.get("added_at") or "")
    return out


def find_playlist_by_name(token: str, name: str) -> dict | None:
    offset, limit = 0, 50
    while True:
        page = api("GET", f"/me/playlists?limit={limit}&offset={offset}", token)
        for p in page.get("items") or []:
            if p.get("name") == name:
                return p
        offset += limit
        if offset >= int(page.get("total") or 0):
            break
    return None


def chunked(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--month", type=int, choices=range(1, 13))
    ap.add_argument("--name-template", default="Your Favorites {year}-{month:02d}")
    ap.add_argument(
        "--public",
        action="store_true",
        help="Make the playlist public. Default is private.",
    )
    args = ap.parse_args()

    year, month = (args.year, args.month) if args.year and args.month else prior_month()
    name = args.name_template.format(year=year, month=month)

    token = access_token()
    tracks = liked_tracks_in_month(token, year, month)
    if not tracks:
        print(f"No liked tracks for {year}-{month:02d}. Nothing to do.")
        return 0

    uris = [t["track"]["uri"] for t in tracks if t.get("track", {}).get("uri")]

    existing = find_playlist_by_name(token, name)
    if existing:
        full = api("GET", f"/playlists/{existing['id']}?market=US", token)
        old_uris = [
            i["track"]["uri"]
            for i in (full.get("tracks") or {}).get("items", [])
            if i.get("track", {}).get("uri")
        ]
        for group in chunked(old_uris, 100):
            api(
                "DELETE",
                f"/playlists/{existing['id']}/tracks",
                token,
                json={"tracks": [{"uri": u} for u in group]},
            )
        playlist_id = existing["id"]
        action = "updated"
    else:
        me = api("GET", "/me", token)
        created = api(
            "POST",
            f"/users/{me['id']}/playlists",
            token,
            json={
                "name": name,
                "public": args.public,
                "description": f"Songs you liked in {year}-{month:02d}.",
            },
        )
        playlist_id = created["id"]
        action = "created"

    for group in chunked(uris, 100):
        api(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            token,
            json={"uris": group},
        )

    print(f"{action} '{name}' with {len(uris)} tracks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
