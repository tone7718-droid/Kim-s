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
from dataclasses import dataclass, asdict, replace
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
    category: str  # "regular" | "preseason" | "postseason" | "unknown"


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


_FINISHED_STATUS_CODES = {"RESULT", "RESULT_FINAL", "FINAL", "END", "FINISHED"}
_CANCELLED_STATUS_CODES = {"CANCEL", "CANCEL_GAME", "CANCELED"}
_POSTPONED_STATUS_CODES = {"POSTPONE", "POSTPONED", "PPD", "DELAY"}
# Anything else (BEFORE, READY, STARTED, LIVE, blank, ...) is treated as
# scheduled — even if 0:0 happens to be in the response. This avoids the
# nasty bug where future games with a default 0:0 score get mislabeled
# as ties.

# Naver also exposes a Korean statusInfo string ("우천취소", "노게임",
# "연기" 등). Cancelled/postponed games often arrive with statusCode
# stuck at "BEFORE" but a meaningful statusInfo, so we check both.
_CANCEL_INFO_TOKENS = ("취소", "노게임", "NOGAME", "CANCEL")
_POSTPONE_INFO_TOKENS = ("연기", "POSTPONE", "PPD", "DELAY")
_FINISHED_INFO_TOKENS = ("종료", "경기종료", "FINAL", "END")

# KBO regular-season opening dates (정규시즌 개막일). Used to draw the
# line between 시범경기 and 정규시즌 cleanly when the API doesn't expose
# a category field. Source: KBO 공식 일정.
_REGULAR_OPENING = {
    2021: "2021-04-03",
    2022: "2022-04-02",
    2023: "2023-04-01",
    2024: "2024-03-23",
    2025: "2025-03-22",
    2026: "2026-03-28",
}
# Postseason typically starts mid-to-late October. We use Oct 22 as a
# generous lower bound — earlier than any recent KS but late enough to
# exclude regular-season Octobers reliably.
_POSTSEASON_FROM_MMDD = (10, 22)

# Candidate fields that have appeared in Naver-style sports payloads to
# distinguish 시범경기 / 정규시즌 / 포스트시즌. We probe each in order
# and the first non-empty value wins.
_CATEGORY_FIELDS = (
    "gameKindCode", "gameKindName", "gameKind",
    "seriesType", "seriesCode", "seriesName",
    "seasonCode", "seasonType", "seasonName",
    "leagueInfo.code", "leagueInfo.name", "leagueInfo.seriesType",
    "category",
)

# Tokens we look for inside the candidate value to bucket it.
_PRESEASON_TOKENS = ("PRE", "시범", "EXHIB", "EX", "SPRING")
_POSTSEASON_TOKENS = (
    "POST", "PO", "PLAYOFF", "WC", "WILD",          # 포스트시즌 일반
    "SEMI", "준플", "와일드",                        # 한국식 표현
    "KS", "KOREAN_SERIES", "KOREANSERIES", "한국시리즈",
    "FINAL_SERIES", "CHAMPIONSHIP",
)
_REGULAR_TOKENS = ("REG", "정규", "REGULAR", "SEASON")


def _classify_category(raw: dict, date_str: str) -> str:
    """Return 'regular' / 'preseason' / 'postseason' / 'unknown'.

    Probes likely category-bearing fields first. Falls back to KBO's
    actual opening dates (hardcoded per season) so 시범경기 doesn't
    leak into regular-season counts.
    """
    for field in _CATEGORY_FIELDS:
        v = _pluck(raw, field)
        if v is None:
            continue
        s = str(v).upper()
        if any(tok in s for tok in (t.upper() for t in _PRESEASON_TOKENS)):
            return "preseason"
        if any(tok in s for tok in (t.upper() for t in _POSTSEASON_TOKENS)):
            return "postseason"
        if any(tok in s for tok in (t.upper() for t in _REGULAR_TOKENS)):
            return "regular"

    try:
        y, m, d = (int(x) for x in date_str.split("-"))
    except Exception:
        return "unknown"

    # Postseason: late October onward.
    pmm, pdd = _POSTSEASON_FROM_MMDD
    if (m, d) >= (pmm, pdd) or m >= 11:
        return "postseason"

    opening = _REGULAR_OPENING.get(y)
    if opening is not None:
        if date_str < opening:
            return "preseason"
        return "regular"

    # No opening date configured for this season — best-effort fallback.
    if m == 3 and d <= 24:
        return "preseason"
    if 3 <= m <= 10:
        return "regular"
    return "unknown"


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

    status_code = (raw.get("statusCode") or "").upper().strip()
    status_info_raw = str(raw.get("statusInfo") or "").strip()
    status_info_upper = status_info_raw.upper()

    def _info_has(tokens):
        return any(t in status_info_raw or t.upper() in status_info_upper for t in tokens)

    # statusInfo wins over statusCode: API frequently keeps statusCode at
    # "BEFORE" while statusInfo says "우천취소".
    if _info_has(_CANCEL_INFO_TOKENS) or status_code in _CANCELLED_STATUS_CODES:
        status = "cancelled"
    elif _info_has(_POSTPONE_INFO_TOKENS) or status_code in _POSTPONED_STATUS_CODES:
        status = "postponed"
    elif status_code in _FINISHED_STATUS_CODES or _info_has(_FINISHED_INFO_TOKENS):
        if away_score is not None and home_score is not None:
            status = "tied" if away_score == home_score else "completed"
        else:
            status = "scheduled"
    else:
        # BEFORE / READY / LIVE / 알 수 없는 코드 — 점수 0:0이 들어와도
        # 미래 경기를 무승부로 오분류하지 않도록 무조건 scheduled.
        status = "scheduled"

    stadium = _pluck(raw, "stadium", "place", "ballpark") or None
    if stadium is not None:
        stadium = str(stadium)

    category = _classify_category(raw, date_str)

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
        category=category,
    )


_debug_state = {
    "first_payload_seen": False,
    "status_counts": {},
    "status_info_counts": {},
    "status_combo_counts": {},
    "category_field_values": {f: {} for f in _CATEGORY_FIELDS},
    "first_game": None,
    "first_before_game": None,  # raw of first non-RESULT/finished sample
    "first_payload_top_keys": None,
    "first_payload_result_keys": None,
}


def _record_debug(payload: dict, raws: list[dict]) -> None:
    if not _debug_state["first_payload_seen"]:
        _debug_state["first_payload_top_keys"] = (
            list(payload.keys()) if isinstance(payload, dict) else None
        )
        _debug_state["first_payload_result_keys"] = (
            list(payload["result"].keys())
            if isinstance(payload, dict) and isinstance(payload.get("result"), dict)
            else None
        )
        if raws:
            _debug_state["first_game"] = raws[0]
        _debug_state["first_payload_seen"] = True

    for r in raws:
        sc = (r.get("statusCode") or "").upper().strip() or "(empty)"
        si = (str(r.get("statusInfo") or "")).strip() or "(empty)"
        _debug_state["status_counts"][sc] = _debug_state["status_counts"].get(sc, 0) + 1
        _debug_state["status_info_counts"][si] = _debug_state["status_info_counts"].get(si, 0) + 1
        combo = f"{sc} / {si}"
        _debug_state["status_combo_counts"][combo] = _debug_state["status_combo_counts"].get(combo, 0) + 1
        if _debug_state["first_before_game"] is None and sc not in _FINISHED_STATUS_CODES:
            _debug_state["first_before_game"] = r
        for field in _CATEGORY_FIELDS:
            v = _pluck(r, field)
            if v is None:
                continue
            key = str(v)
            bucket = _debug_state["category_field_values"][field]
            bucket[key] = bucket.get(key, 0) + 1


def _flush_debug() -> None:
    try:
        DEBUG_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)

        def _sorted_desc(d):
            return dict(sorted(d.items(), key=lambda kv: -kv[1]))

        diag = {
            "topLevelKeys": _debug_state["first_payload_top_keys"],
            "resultKeys": _debug_state["first_payload_result_keys"],
            "firstGame": _debug_state["first_game"],
            "firstGameKeys": (
                sorted(_debug_state["first_game"].keys())
                if _debug_state["first_game"]
                else None
            ),
            "firstBeforeGame": _debug_state["first_before_game"],
            "statusCodeCounts": _sorted_desc(_debug_state["status_counts"]),
            "statusInfoCounts": _sorted_desc(_debug_state["status_info_counts"]),
            "statusComboCounts": _sorted_desc(_debug_state["status_combo_counts"]),
            "categoryFieldValues": {
                f: _sorted_desc(vals)
                for f, vals in _debug_state["category_field_values"].items()
                if vals
            },
        }
        DEBUG_DUMP_PATH.write_text(
            json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"  (debug dump failed: {e})", file=sys.stderr)


def scrape_year(year: int, months: Iterable[int] = range(3, 12)) -> list[Game]:
    # base_id -> count of times we've seen it. Same (date, away, home)
    # appearing more than once means a double-header; the 2nd / 3rd / ...
    # game gets a "-2" / "-3" suffix on its id so we don't silently drop
    # one of them. Existing single games keep their original id, so users'
    # LocalStorage records stay valid across the migration.
    seen_count: dict[str, int] = {}
    out: list[Game] = []
    for month in months:
        first = dt.date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        last = dt.date(year, month, last_day)
        print(f"  fetching {first}..{last} ...", file=sys.stderr)
        payload = fetch_range(first.isoformat(), last.isoformat())
        raws = _extract_games(payload)
        # Sort by gameDateTime so a double-header's earlier game gets the
        # bare id and the later one gets -2.
        raws.sort(key=lambda r: str(_pluck(r, "gameDateTime") or _pluck(r, "gameDate") or ""))
        _record_debug(payload, raws)
        kept = 0
        for r in raws:
            g = _normalize_game(r)
            if g is None:
                continue
            base = g.id
            count = seen_count.get(base, 0)
            if count > 0:
                g = replace(g, id=f"{base}-{count + 1}")
            seen_count[base] = count + 1
            out.append(g)
            kept += 1
        print(f"    -> {len(raws)} raw, {kept} kept", file=sys.stderr)
        time.sleep(0.3)
    out.sort(key=lambda g: (g.date, g.awayTeam, g.id))
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

    _flush_debug()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
