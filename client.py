"""Strava API client with automatic token refresh."""

import os
import time
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

BASE_URL = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self):
        self.client_id = os.environ["STRAVA_CLIENT_ID"]
        self.client_secret = os.environ["STRAVA_CLIENT_SECRET"]
        self.access_token = os.environ["STRAVA_ACCESS_TOKEN"]
        self.refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]
        self._rate_limit_remaining = 100

    def _refresh_token(self):
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        set_key(".env", "STRAVA_ACCESS_TOKEN", self.access_token)
        set_key(".env", "STRAVA_REFRESH_TOKEN", self.refresh_token)

    def get(self, path, **params):
        for attempt in range(10):  # More attempts for rate limiting
            resp = requests.get(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
            )
            self._rate_limit_remaining = int(
                resp.headers.get("X-RateLimit-Limit", "100").split(",")[0]
            )
            usage = resp.headers.get("X-RateLimit-Usage", "0,0").split(",")
            per_15min = int(usage[0])

            if resp.status_code == 401:
                self._refresh_token()
                continue

            if resp.status_code == 429:
                # Use reset header if available, else wait 15 min
                reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                if reset_time:
                    wait = max(reset_time - int(time.time()), 1)
                else:
                    wait = 900  # 15 minutes
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            # Skip deleted/private activities
            if resp.status_code in (404, 403):
                return None

            # Back off gently near the 15-min limit (90 req/15min)
            if per_15min >= 90:
                wait = 15 * 60 - (time.time() % (15 * 60))  # Wait until reset
                if wait > 2:
                    print(f"  Approaching rate limit, waiting {int(wait)}s...")
                    time.sleep(wait)
                    continue

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Failed to GET {path} after retries (status unknown)")

    def paginate(self, path, per_page=200, **params):
        page = 1
        while True:
            results = self.get(path, page=page, per_page=per_page, **params)
            if not results:
                break
            yield from results
            if len(results) < per_page:
                break
            page += 1
