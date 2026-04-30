"""
OAuth flow to get Strava access + refresh tokens.
Run once: python auth.py
"""

import os
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:8080/callback"
SCOPE = "read,read_all,profile:read_all,activity:read_all"

_auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        _auth_code = params.get("code")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>Auth complete! You can close this tab.</h1>")

    def log_message(self, *args):
        pass


def run():
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={SCOPE}"
    )
    print(f"Opening browser for Strava authorization...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not _auth_code:
        raise RuntimeError("No authorization code received.")

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": _auth_code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    tokens = resp.json()

    env_path = ".env"
    lines = open(env_path).readlines() if os.path.exists(env_path) else []

    def upsert(lines, key, value):
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                return lines
        lines.append(f"{key}={value}\n")
        return lines

    lines = upsert(lines, "STRAVA_ACCESS_TOKEN", tokens["access_token"])
    lines = upsert(lines, "STRAVA_REFRESH_TOKEN", tokens["refresh_token"])

    with open(env_path, "w") as f:
        f.writelines(lines)

    print(f"Tokens saved to .env")
    print(f"  Athlete: {tokens['athlete']['firstname']} {tokens['athlete']['lastname']}")


if __name__ == "__main__":
    run()
