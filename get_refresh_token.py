#!/usr/bin/env python3
"""One-time helper. Get a long-lived Spotify refresh token.

Usage:
  SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... \
  SPOTIFY_REDIRECT_URI=http://127.0.0.1:43827/spotify/callback \
  python3 get_refresh_token.py

Prereqs:
  1. https://developer.spotify.com/dashboard -> Create app.
  2. Add the SAME redirect URI you'll pass via SPOTIFY_REDIRECT_URI (exact
     match, character for character). Prefer 127.0.0.1 over localhost.
  3. Copy Client ID + Client Secret.

The refresh token does not expire under normal use. If you revoke the
Spotify app authorization or change your password, re-run this.
"""
from __future__ import annotations

import base64
import http.server
import os
import secrets
import sys
import urllib.parse
import webbrowser

import httpx

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get(
    "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"
)
SCOPES = "user-library-read playlist-modify-public playlist-modify-private playlist-read-private user-top-read"

if not CLIENT_ID or not CLIENT_SECRET:
    print(
        "Missing env. Run with:\n"
        "  SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... python3 get_refresh_token.py",
        file=sys.stderr,
    )
    sys.exit(1)

state = secrets.token_hex(16)
parsed_redirect = urllib.parse.urlparse(REDIRECT_URI)
PORT = parsed_redirect.port or 8888
CALLBACK_PATH = parsed_redirect.path or "/callback"

auth_url = (
    "https://accounts.spotify.com/authorize?"
    + urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "scope": SCOPES,
        }
    )
)

received: dict = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if not self.path.startswith(CALLBACK_PATH):
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(qs))
        code = params.get("code")
        returned_state = params.get("state")
        error = params.get("error")
        if error or not code or returned_state != state:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(
                f"Auth failed: {error or 'missing code or bad state'}".encode()
            )
            received["err"] = error or "missing code or bad state"
            return
        basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        r = httpx.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            timeout=20,
        )
        if r.status_code != 200:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Token exchange failed: {r.text}".encode())
            received["err"] = r.text
            return
        token = r.json().get("refresh_token")
        if not token:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            msg = (
                "Token exchange returned no refresh_token. "
                "Revoke this app at https://www.spotify.com/account/apps and re-run."
            )
            self.wfile.write(msg.encode())
            received["err"] = msg
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h1>Got it.</h1><p>Refresh token printed in your terminal. You can close this tab.</p>"
        )
        received["token"] = token

    def log_message(self, *args) -> None:  # noqa: D401
        pass


def main() -> int:
    print(f"Listening on http://127.0.0.1:{PORT}{CALLBACK_PATH}")
    print("Opening Spotify authorize page in your browser...")
    print(f"If the browser didn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    while "token" not in received and "err" not in received:
        server.handle_request()
    if "err" in received:
        print(f"\nFailed: {received['err']}", file=sys.stderr)
        return 1
    print("\n--- SPOTIFY REFRESH TOKEN ---")
    print(received["token"])
    print("-----------------------------\n")
    print("Add to your env as SPOTIFY_REFRESH_TOKEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
