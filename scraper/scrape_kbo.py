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
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import requests

from teams import normalize_code

API_URL = "https://api-gw.sports.naver.com/schedule/games"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seasons"
DEBUG_DUMP_PATH = Path(os.environ.get("KBO_DEBUG_DUMP", "/tmp/kbo_debug_response.json"))

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


def fetch_range(from_date: str, to_date: str, retries: int = 3) -> dict:
    """Fetch a date-range of KBO games from Naver Sports.

    Returns the full JSON payload (caller extracts the games list) so the
    first response can be inspected for diagnostics.
    """
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
            print(f"    HTTP {r.status_code}, {len(r.content)} bytes", file=sys.stderr)
            r.raise_for_status()
            try:
                return r.json()
            except Exception as je:
                # Save raw text for inspection if JSON parse fails.
                DEBUG_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
                DEBUG_DUMP_PATH.write_text(r.text[:200_000], encoding="utf-8")
                raise RuntimeError(
                    f"JSON parse failed; raw saved to {DEBUG_DUMP_PATH}"
                ) from je
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {from_date}..{to_date}: {last_err}")


def _extract_games(payload: dict) -> list[dict]:
    """Pull a list of game records out of the payload.

    Naver wraps the data in `result.games` in the schedule endpoint, but we
    accept a few likely alternatives so a small wrapper change doesn't make
    every season silently empty.
    """
    if not isinstance(payload, dict):
        return []
    candidates: list = []
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("games", "gameList", "scheduleList", "items"):
            v = result.get(key)
            if isinstance(v, list):
                candidates = v
                break
        if not candidates:
            # Some Naver endpoints return result.dates -> list of {games: [...]}
            for key in ("dates", "groups"):
                v = result.get(key)
                if isinstance(v, list):
                    flat: list = []
                    for entry in v:
                        if isinstance(entry, dict):
                            inner = entry.get("games") or entry.get("gameList")
                            if isinstance(inner, list):
                                flat.extend(inner)
                    if flat:
                        candidates = flat
                        break
    if not candidates:
        for key in ("games", "gameList", "scheduleList"):
            v = payload.get(key)
            if isinstance(v, list):
                candidates = v
                break
    return [g for g in candidates if isinstance(g, dict)]


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


def _pluck(d: dict, *keys: str):
    """Find the first non-empty value among nested dot-paths."""
    for key in keys:
        node: object = d
        ok = True
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                ok = False
                break
        if ok and node not in (None, ""):
            return node
    return None


def _normalize_game(raw: dict) -> Game | None:
    game_date_raw = _pluck(raw, "gameDate", "gmkey", "date") or ""
    if isinstance(game_date_raw, (int, float)):
        game_date_raw = str(int(game_date_raw))
    game_date_raw = str(game_date_raw)
    # Accept YYYY-MM-DD or YYYYMMDD or ISO datetimes.
    digits = "".join(c for c in game_date_raw if c.isdigit())[:8]
    if len(digits) != 8:
        return None
    date_str = f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"

    away_raw = (
        _pluck(raw, "awayTeamCode", "awayTeam.code", "away.code", "awayTeamName", "awayTeam.name")
        or ""
    )
    home_raw = (
        _pluck(raw, "homeTeamCode", "homeTeam.code", "home.code", "homeTeamName", "homeTeam.name")
        or ""
    )
    away_code = normalize_code(str(away_raw))
    home_code = normalize_code(str(home_raw))
    if not away_code or not home_code:
        return None

    away_score = _coerce_score(_pluck(raw, "awayTeamScore", "awayTeam.score", "away.score"))
    home_score = _coerce_score(_pluck(raw, "homeTeamScore", "homeTeam.score", "home.score"))

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

    stadium = _pluck(raw, "stadium", "place", "ballpark") or None
    if stadium is not None:
        stadium = str(stadium)

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


_debug_saved = False


def _save_debug(payload: dict, raws: list[dict]) -> None:
    """Write a compact diagnostics file for the first month of the first year."""
    global _debug_saved
    if _debug_saved:
        return
    try:
        DEBUG_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        diag = {
            "topLevelKeys": list(payload.keys()) if isinstance(payload, dict) else None,
            "resultKeys": (
                list(payload["result"].keys())
                if isinstance(payload, dict) and isinstance(payload.get("result"), dict)
                else None
            ),
            "extractedGameCount": len(raws),
            "firstGame": raws[0] if raws else None,
            "firstGameKeys": sorted(raws[0].keys()) if raws else None,
        }
        DEBUG_DUMP_PATH.write_text(
            json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _debug_saved = True
    except Exception as e:
        print(f"  (debug dump failed: {e})", file=sys.stderr)


def scrape_year(year: int, months: Iterable[int] = range(3, 12)) -> list[Game]:
    seen: set[str] = set()
    out: list[Game] = []
    for month in months:
        first = dt.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        last = dt.date(year, month, last_day)
        print(f"  fetching {first}..{last} ...", file=sys.stderr)
        payload = fetch_range(first.isoformat(), last.isoformat())
        raws = _extract_games(payload)
        _save_debug(payload, raws)
        kept = 0
        for r in raws:
            g = _normalize_game(r)
            if g and g.id not in seen:
                seen.add(g.id)
                out.append(g)
                kept += 1
        print(f"    -> {len(raws)} raw, {kept} kept", file=sys.stderr)
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
