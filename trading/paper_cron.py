"""Render Cron entry point for the authenticated paper-trading scheduler."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    url = os.getenv("NOVA_TRADING_WORKER_URL", "").strip()
    token = os.getenv("TRADE_CONTROL_TOKEN", "").strip()
    if not url.startswith("https://") or not token:
        print("Trade worker configuration missing; refusing to run.")
        return 2

    request = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Trade-Control-Token": token,
            "User-Agent": "NOVA-Trade-Paper-Scheduler/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            payload = response.read().decode("utf-8")
            print(json.dumps(json.loads(payload), ensure_ascii=False))
            return 0
    except urllib.error.HTTPError as error:
        # Never print request headers or environment values.
        print(f"Trade worker returned HTTP {error.code}.")
        return 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Trade worker request failed: {type(error).__name__}.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
