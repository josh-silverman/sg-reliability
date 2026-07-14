"""Fetch round-level strokes-gained data from the DataGolf API.

Pulls per-round scoring for all PGA Tour events with SG categories,
2017-2026, from the historical-raw-data endpoints. Raw JSON responses are
cached in data/raw/ (gitignored) so the script is resumable; the flattened
result is written to data/rounds.parquet.

Usage: python scripts/fetch_data.py
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_URL = "https://feeds.datagolf.com/historical-raw-data"
YEARS = range(2017, 2027)
TOUR = "pga"
REQUEST_DELAY_S = 1.0
MAX_RETRIES = 5
BACKOFF_BASE_S = 30  # 429 backoff: 30s, 60s, 120s, ...

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PARQUET_PATH = ROOT / "data" / "rounds.parquet"
EVENT_LIST_PATH = ROOT / "data" / "raw" / "event_list.json"

ROUND_KEYS = ["round_1", "round_2", "round_3", "round_4"]


def get_api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("DATAGOLF_API_KEY")
    if not key:
        sys.exit("DATAGOLF_API_KEY not set in .env")
    return key


def fetch_json(url: str, params: dict) -> dict | list:
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 429:
            wait = BACKOFF_BASE_S * 2**attempt
            print(f"    rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


def fetch_event_list(key: str) -> list[dict]:
    if EVENT_LIST_PATH.exists():
        return json.loads(EVENT_LIST_PATH.read_text())
    events = fetch_json(f"{BASE_URL}/event-list", {"file_format": "json", "key": key})
    EVENT_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LIST_PATH.write_text(json.dumps(events))
    return events


def sg_events(events: list[dict]) -> list[dict]:
    return [
        e
        for e in events
        if e["tour"] == TOUR
        and e["calendar_year"] in YEARS
        and e["sg_categories"] == "yes"
    ]


def fetch_event_rounds(event: dict, key: str) -> dict:
    """Fetch (or load cached) raw rounds JSON for one event."""
    cache = RAW_DIR / f"rounds_{event['calendar_year']}_{event['event_id']}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    data = fetch_json(
        f"{BASE_URL}/rounds",
        {
            "tour": TOUR,
            "event_id": event["event_id"],
            "year": event["calendar_year"],
            "file_format": "json",
            "key": key,
        },
    )
    cache.write_text(json.dumps(data))
    time.sleep(REQUEST_DELAY_S)
    return data


def flatten_event(event: dict, data: dict) -> list[dict]:
    """One output row per player-round."""
    rows = []
    for player in data.get("scores", []):
        for i, rk in enumerate(ROUND_KEYS, start=1):
            rnd = player.get(rk)
            if not rnd:
                continue
            rows.append(
                {
                    "calendar_year": event["calendar_year"],
                    "season": data.get("season"),
                    "event_id": event["event_id"],
                    "event_name": event["event_name"],
                    "event_date": event["date"],
                    "event_completed": data.get("event_completed"),
                    "dg_id": player["dg_id"],
                    "player_name": player["player_name"],
                    "fin_text": player.get("fin_text"),
                    "round_num": i,
                    **rnd,
                }
            )
    return rows


def main() -> None:
    key = get_api_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    events = sg_events(fetch_event_list(key))
    print(f"{len(events)} {TOUR.upper()} events with SG categories, "
          f"{min(YEARS)}-{max(YEARS)}")

    rows: list[dict] = []
    failures: list[str] = []
    for n, event in enumerate(sorted(events, key=lambda e: e["date"]), start=1):
        label = f"{event['calendar_year']} {event['event_name']} (id {event['event_id']})"
        try:
            data = fetch_event_rounds(event, key)
        except requests.RequestException as exc:
            failures.append(f"{label}: {exc}")
            print(f"  [{n}/{len(events)}] FAILED {label}: {exc}")
            continue
        rows.extend(flatten_event(event, data))
        if n % 25 == 0 or n == len(events):
            print(f"  [{n}/{len(events)}] {label} — {len(rows):,} rows so far")

    df = pd.DataFrame(rows)
    df.to_parquet(PARQUET_PATH, index=False)
    print(f"\nWrote {len(df):,} player-rounds to {PARQUET_PATH}")
    if failures:
        print(f"\n{len(failures)} events failed:")
        for f in failures:
            print(f"  {f}")


if __name__ == "__main__":
    main()
