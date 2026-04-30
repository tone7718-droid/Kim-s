"""Scrape KBO regular-season schedule + results from Naver Sports.

Uses the public Naver Sports schedule endpoint (api-gw.sports.naver.com),
which returns JSON. Far more reliable than HTML scraping — no DOM parsing,
no selector drift, and accessible from cloud CI environments.

Usage:
    python scrape_kbo.py --year 2021
    python scrape_kbo.py --year 2021 --month 4
    python scrape_kbo.py --years 2021-2026

Output: data/seasons/<year>.json

Each game looks like:
    {
        "id": "2021-04-03-LG-NC",
        "date": "2021-04-03",
        "awayTeam": "LG",
        "homeTeam": "NC",
        "awayScore": 5,
        "homeScore": 3,
        "status": "completed" | "tied" | "cancelled" | "postponed" | "scheduled",
        "stadium": "창원NC파크" | null
    }
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import requests

from teams import normalize_code

API_URL = "https://api-gw.sports.naver.com/schedule/games"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seasons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://m.sports.naver.com/",
}


@dataclass
class Game:
    id: str
    date: str
    awayTeam: str
    homeTeam: str
    awayScore: int | None
    homeScore: int | None
    status: str
    stadium: str | None


def fetch_range(from_date: str, to_date: str, retries: int = 3) -> list[dict]:
    """Fetch a date-range of KBO games from Naver Sports."""
    params = {
        "fields": "basic,baseballHome,baseballAway,statusInfo,leagueInfo",
        "upperCategoryId": "kbaseball",
        "categoryId": "kbo",
        "fromDate": from_date,
        "toDate": to_date,
        "size": 500,
    }
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(API_URL, headers=HEADERS, params=params, timeout=20)
            r.raise_for_status()
            payload = r.json()
            return payload.get("result", {}).get("games", []) or []
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {from_date}..{to_date}: {last_err}")


# Naver status codes seen in practice. Anything not listed falls through
# to a score-based heuristic.
_STATUS_MAP = {
    "RESULT": None,           # could be completed or tied — decided by scores
    "RESULT_FINAL": None,
    "FINAL": None,
    "END": None,
    "CANCEL": "cancelled",
    "CANCEL_GAME": "cancelled",
    "POSTPONE": "postponed",
    "PPD": "postponed",
    "BEFORE": "scheduled",
    "READY": "scheduled",
    "STARTED": "scheduled",
    "LIVE": "scheduled",
}


def _coerce_score(v) -> int | None:
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v)
    return None


def _normalize_game(raw: dict) -> Game | None:
    game_date_raw = raw.get("gameDate") or ""
    if len(game_date_raw) != 8 or not game_date_raw.isdigit():
        return None
    date_str = f"{game_date_raw[0:4]}-{game_date_raw[4:6]}-{game_date_raw[6:8]}"

    away_code = (
        normalize_code(raw.get("awayTeamCode") or "")
        or normalize_code(raw.get("awayTeamName") or "")
    )
    home_code = (
        normalize_code(raw.get("homeTeamCode") or "")
        or normalize_code(raw.get("homeTeamName") or "")
    )
    if not away_code or not home_code:
        return None

    away_score = _coerce_score(raw.get("awayTeamScore"))
    home_score = _coerce_score(raw.get("homeTeamScore"))

    status_code = (raw.get("statusCode") or "").upper()
    status = _STATUS_MAP.get(status_code, "scheduled")
    if status is None:  # finished — let scores decide tied vs completed
        if away_score is not None and home_score is not None:
            status = "tied" if away_score == home_score else "completed"
        else:
            status = "scheduled"
    elif status == "scheduled" and away_score is not None and home_score is not None:
        # API sometimes lags on the status flag while scores are present.
        status = "tied" if away_score == home_score else "completed"

    stadium = raw.get("stadium") or None

    game_id = f"{date_str}-{away_code}-{home_code}"
    return Game(
        id=game_id,
        date=date_str,
        awayTeam=away_code,
        homeTeam=home_code,
        awayScore=away_score,
        homeScore=home_score,
        status=status,
        stadium=stadium,
    )


def scrape_year(year: int, months: Iterable[int] = range(3, 12)) -> list[Game]:
    seen: set[str] = set()
    out: list[Game] = []
    for month in months:
        first = dt.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        last = dt.date(year, month, last_day)
        print(f"  fetching {first}..{last} ...", file=sys.stderr)
        raws = fetch_range(first.isoformat(), last.isoformat())
        for r in raws:
            g = _normalize_game(r)
            if g and g.id not in seen:
                seen.add(g.id)
                out.append(g)
        time.sleep(0.3)
    out.sort(key=lambda g: (g.date, g.awayTeam))
    return out


def write_season(year: int, games: list[Game]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{year}.json"
    payload = {
        "year": year,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "games": [asdict(g) for g in games],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def parse_year_range(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(spec)]


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--year", type=int, help="single year, e.g. 2021")
    g.add_argument("--years", type=str, help="range like 2021-2026")
    ap.add_argument("--month", type=int, help="restrict to one month (debugging)")
    args = ap.parse_args()

    years = [args.year] if args.year else parse_year_range(args.years)
    months = [args.month] if args.month else range(3, 12)

    for y in years:
        print(f"== {y} ==", file=sys.stderr)
        games = scrape_year(y, months)
        out = write_season(y, games)
        print(f"  wrote {len(games)} games -> {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
