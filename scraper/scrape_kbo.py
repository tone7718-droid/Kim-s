"""Scrape KBO regular-season schedule + results from Statiz.

Usage:
    python scrape_kbo.py --year 2021
    python scrape_kbo.py --year 2021 --month 4
    python scrape_kbo.py --years 2021-2026

Output: data/seasons/<year>.json

Each game looks like:
    {
        "id": "2021-04-03-OB-NC",
        "date": "2021-04-03",
        "awayTeam": "OB",
        "homeTeam": "NC",
        "awayScore": 5,
        "homeScore": 3,
        "status": "completed" | "tied" | "cancelled" | "postponed" | "scheduled",
        "stadium": "창원" | null
    }

Statiz markup may shift between seasons; selector logic is concentrated in
parse_month_html() so it can be adjusted in one place.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from teams import to_code

BASE_URL = "https://statiz.sporki.com/schedule/"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seasons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
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


def fetch_month(year: int, month: int, retries: int = 3) -> str:
    url = f"{BASE_URL}?year={year}&month={month:02d}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


_SCORE_RE = re.compile(r"(\d+)\s*[:vs]+\s*(\d+)", re.IGNORECASE)


def _parse_one_game(cell, year: int, date_str: str) -> Game | None:
    """Parse a single game card from a calendar cell.

    Statiz schedule cells contain one or more <a> blocks that look like:
        <a href="/schedule/?m=preview&s_no=...">
            <span>away</span>
            <span>5:3</span>
            <span>home</span>
        </a>
    Cancelled / postponed games may show only team names with status text
    such as '취소', '우천취소', '연기'.
    """
    text = cell.get_text(" ", strip=True)
    if not text:
        return None

    # Heuristic: collect spans within the link, fall back to plain text.
    spans = [s.get_text(strip=True) for s in cell.find_all("span")]
    spans = [s for s in spans if s]

    # Find away/home team names from known aliases.
    teams_found: list[str] = []
    for s in spans:
        for alias in ("KIA", "기아", "삼성", "LG", "두산", "KT", "kt",
                      "SSG", "SK", "롯데", "한화", "NC", "키움"):
            if s == alias:
                teams_found.append(alias)
                break
        if len(teams_found) == 2:
            break

    if len(teams_found) < 2:
        return None

    away_name, home_name = teams_found[0], teams_found[1]

    # Score detection.
    away_score: int | None = None
    home_score: int | None = None
    status = "scheduled"
    for s in spans:
        m = _SCORE_RE.fullmatch(s.replace(" ", ""))
        if m:
            away_score = int(m.group(1))
            home_score = int(m.group(2))
            break

    if away_score is not None and home_score is not None:
        if away_score == home_score:
            status = "tied"
        else:
            status = "completed"
    else:
        if any(k in text for k in ("취소", "우천", "노게임")):
            status = "cancelled"
        elif "연기" in text:
            status = "postponed"

    stadium = None
    # Stadium often appears as a small label; try common class names.
    st_el = cell.find(class_=re.compile(r"(stadium|place|loc)"))
    if st_el:
        stadium = st_el.get_text(strip=True) or None

    away_code = to_code(away_name)
    home_code = to_code(home_name)
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


def parse_month_html(html: str, year: int, month: int) -> list[Game]:
    soup = BeautifulSoup(html, "html.parser")

    games: list[Game] = []
    # Statiz renders a calendar table; each <td> holds a day.
    for td in soup.select("table td"):
        # Day number is the first numeric token in the cell.
        day_el = td.find(class_=re.compile(r"(day|date)")) or td
        day_text = day_el.get_text(" ", strip=True)
        m = re.search(r"\b(\d{1,2})\b", day_text)
        if not m:
            continue
        day = int(m.group(1))
        if not (1 <= day <= 31):
            continue
        date_str = f"{year:04d}-{month:02d}-{day:02d}"

        # Each game block typically lives inside an <a> within the cell.
        game_links = td.find_all("a") or [td]
        for link in game_links:
            try:
                g = _parse_one_game(link, year, date_str)
            except ValueError:
                # Unknown team name — skip rather than crash on a single row.
                continue
            if g is not None:
                games.append(g)

    return games


def scrape_year(year: int, months: Iterable[int] = range(3, 12)) -> list[Game]:
    all_games: list[Game] = []
    seen_ids: set[str] = set()
    for month in months:
        print(f"  fetching {year}-{month:02d} ...", file=sys.stderr)
        html = fetch_month(year, month)
        games = parse_month_html(html, year, month)
        for g in games:
            if g.id in seen_ids:
                continue
            seen_ids.add(g.id)
            all_games.append(g)
        time.sleep(0.5)
    all_games.sort(key=lambda g: (g.date, g.awayTeam))
    return all_games


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
