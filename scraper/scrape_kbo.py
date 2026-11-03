"""Scrape KBO schedule + results.

The default source is the KBO schedule endpoint used by
koreabaseball.com/Schedule/Schedule.aspx. Naver's API
(api-gw.sports.naver.com) times out from GitHub-hosted runners, so scheduled
runs use KBO and keep Naver as an optional fallback.

Usage:
    python scrape_kbo.py --year 2026
    python scrape_kbo.py --year 2026 --month 10
    python scrape_kbo.py --year 2021 --source naver
    python scrape_kbo.py --years 2021-2026 --source kbo-naver

Output: data/seasons/<year>.json

Each game looks like:
    {
        "id": "2021-04-03-LG-NC",
        "date": "2021-04-03",
        "awayTeam": "LG",
        "homeTeam": "NC",
        "awayScore": 5,
        "homeScore": 3,
        "status": "completed" | "tied" | "cancelled" | "postponed" | "scheduled" | "unknown_result",
        "stadium": "창원NC파크" | null,
        "category": "regular" | "preseason" | "postseason" | "unknown",
        "naverGameId": "20210403LGNC02021" | null,
        "naverRecordUrl": "https://m.sports.naver.com/game/.../record" | null
    }
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, replace
from html import unescape
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import requests

from teams import naver_game_code, normalize_code

API_URL = "https://api-gw.sports.naver.com/schedule/games"
KBO_URL = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seasons"
DEBUG_DUMP_PATH = Path(os.environ.get("KBO_DEBUG_DUMP", "/tmp/kbo_debug_response.json"))

# Form fields posted by Schedule.aspx (`getTableGridList`). Confirmed against
# the live page and responses on 2026-11-02:
#   leId=1 (KBO 1군)
#   srIdList  1       시범경기
#             0,9,6   정규시즌 (9 is the 올스타전 드림/나눔 game; unknown clubs are dropped)
#             3       준플레이오프
#             4       와일드카드
#             5       플레이오프
#             7       한국시리즈
#   seasonId  four-digit year
#   gameMonth zero-padded month
# Postseason series are requested separately. The combined value "3,4,5,7"
# that the postseason tab sends omits rainouts (2026-10-25 PO 우천취소 was
# missing there and present on srIdList=5).
# classify_as is fed to _classify_category so stored categories stay inside
# regular / preseason / postseason / unknown. naver_prefix replaces the date
# on postseason Naver ids (3333 준PO, 4444 WC, 5555 PO, 7777 KS).
KBO_SERIES: tuple[tuple[str, str, str | None], ...] = (
    ("1", "시범경기", None),
    ("0,9,6", "정규", None),
    ("3", "준플레이오프", "3333"),
    ("4", "와일드카드", "4444"),
    ("5", "PO", "5555"),
    ("7", "한국시리즈", "7777"),
)
_KBO_SERIES_BY_KEY = {key: (name, prefix) for key, name, prefix in KBO_SERIES}

KBO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "Origin": "https://www.koreabaseball.com",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

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
    naverGameId: str | None
    naverRecordUrl: str | None
    startTime: str | None = None  # HH:mm in Asia/Seoul


def fetch_range(from_date: str, to_date: str, retries: int = 4, timeout: float = 30) -> dict:
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
            r = requests.get(API_URL, headers=HEADERS, params=params, timeout=timeout)
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
# Note: these are substring-matched against statusInfo, so we avoid short
# ambiguous tokens like a bare "END" (it lurks inside "SUSPENDED" →
# ...P-END-ED). A finished English status is already caught via statusCode
# (_FINISHED_STATUS_CODES), and Korean strings use "종료"/"경기종료".
_FINISHED_INFO_TOKENS = ("종료", "경기종료", "FINAL")

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
# KBO postseason opening dates (와일드카드 결정전 1차전). The regular
# season and postseason don't split on a fixed calendar date — the
# regular season runs late (makeup games) in some years and the
# postseason ladder (와카 → 준PO → PO → 한국시리즈) starts on a
# schedule KBO announces each season. Hardcoding the actual 와카 1차전
# date per season (like _REGULAR_OPENING) keeps 정규시즌 makeup games
# out of the postseason bucket. Source: KBO 공식 포스트시즌 일정.
_POSTSEASON_OPENING = {
    2021: "2021-11-01",
    2022: "2022-10-13",
    2023: "2023-10-19",
    2024: "2024-10-02",
    2025: "2025-10-06",
    2026: "2026-10-14",
}
# Naver gives postseason games a series prefix instead of the season year
# as the first four digits of gameId (e.g. 33331017LGHT02026 = 준PO).
# Verified against 2021~2026 data: 4444 와일드카드, 3333 준플레이오프,
# 5555 플레이오프, 7777 한국시리즈 (6666 올스타전 is deliberately absent).
# This needs no per-season upkeep, so it is checked before the dates.
_POSTSEASON_ID_PREFIXES = ("4444", "3333", "5555", "7777")
# Fallback for seasons without a configured 와카 date (e.g. a future
# season scraped before its postseason schedule is added above). Oct 22
# is a generous lower bound — late enough to exclude most regular-season
# Octobers but earlier than any recent 한국시리즈.
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
    naver_game_id = _extract_naver_game_id(raw)
    if naver_game_id and naver_game_id[:4] in _POSTSEASON_ID_PREFIXES:
        return "postseason"

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

    # Postseason: on/after the season's 와일드카드 결정전 1차전. Prefer
    # the hardcoded per-season date; fall back to the late-October
    # heuristic only when the season isn't configured yet.
    postseason_opening = _POSTSEASON_OPENING.get(y)
    if postseason_opening is not None:
        if date_str >= postseason_opening:
            return "postseason"
    else:
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


def _extract_naver_game_id(raw: dict) -> str | None:
    """Return Naver's own game id when present in the schedule payload."""
    v = _pluck(
        raw,
        "gameId",
        "gameID",
        "gameKey",
        "gamekey",
        "gameCenterId",
        "gameCenterID",
        "gmkey",
        "gmid",
    )
    if v is None:
        return None
    s = str(v).strip()
    return s or None


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
            # The API says the game ended, but does not provide a usable
            # result. It must not appear as a future scheduled game.
            status = "unknown_result"
    else:
        # BEFORE / READY / LIVE / 알 수 없는 코드 — 점수 0:0이 들어와도
        # 미래 경기를 무승부로 오분류하지 않도록 무조건 scheduled.
        status = "scheduled"

    stadium = _pluck(raw, "stadium", "place", "ballpark") or None
    if stadium is not None:
        stadium = str(stadium)

    category = _classify_category(raw, date_str)
    naver_game_id = _extract_naver_game_id(raw)
    naver_record_url = (
        f"https://m.sports.naver.com/game/{naver_game_id}/record"
        if naver_game_id
        else None
    )

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
        naverGameId=naver_game_id,
        naverRecordUrl=naver_record_url,
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


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PLAY_RE = re.compile(
    r"<span>(?P<away>[^<]+)</span>\s*<em>(?P<em>.*?)</em>\s*<span>(?P<home>[^<]+)</span>",
    re.S,
)
_SCORE_RE = re.compile(r'<span class="(win|lose|same)">(\d+)</span>')
_KBO_GAME_ID_RE = re.compile(r"gameId=(\d{8}[A-Za-z]{2}[A-Za-z]{2}\d)")
_DAY_RE = re.compile(r"(\d{1,2})\.(\d{1,2})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_SERIES_NOTE_RE = re.compile(
    r"^(WC|준PO|PO|KS|와일드카드|준플레이오프|플레이오프|한국시리즈)\b"
)
# The schedule page prints these in the last column instead of a series label
# when the game is not played. 2026 had 우천취소, 폭염취소, and 그라운드사정.
# 연기/순연 did not appear that season; they are mapped so a later postponement
# is not stored as a final score.
_CANCEL_NOTES = ("취소", "노게임", "그라운드사정", "몰수")
_POSTPONE_NOTES = ("연기", "순연", "서스펜디드", "중단")


@dataclass
class ScrapeResult:
    games: list[Game]
    failed_months: list[int]
    succeeded_months: list[int]


def current_season_year() -> int:
    return dt.datetime.now(ZoneInfo("Asia/Seoul")).year


def _html_text(raw: str) -> str:
    return _WS_RE.sub(" ", unescape(_TAG_RE.sub(" ", raw or ""))).strip()


def _parse_play(raw: str) -> tuple[str, str, int | None, int | None] | None:
    match = _PLAY_RE.search(raw or "")
    if not match:
        return None
    away = unescape(match.group("away")).strip()
    home = unescape(match.group("home")).strip()
    scores = _SCORE_RE.findall(match.group("em"))
    away_score = home_score = None
    if len(scores) >= 2:
        away_score = int(scores[0][1])
        home_score = int(scores[1][1])
    if not away or not home:
        return None
    return away, home, away_score, home_score


def _note_and_stadium(extras: list[str]) -> tuple[str | None, str | None]:
    note = None
    stadium = None
    for text in extras:
        if text in {"-", "리뷰", "프리뷰", "하이라이트"}:
            continue
        if any(tok in text for tok in _CANCEL_NOTES + _POSTPONE_NOTES) or "이동일" in text:
            note = text
            continue
        if _SERIES_NOTE_RE.search(text):
            continue
        if re.search(r"[A-Za-z]", text):
            continue
        if re.search(r"[가-힣]", text):
            stadium = text
    return note, stadium


def _status_from_note(
    note: str | None,
    away_score: int | None,
    home_score: int | None,
    relay: str,
) -> tuple[str, int | None, int | None]:
    note = note or ""
    relay = relay or ""
    if any(tok in note for tok in _CANCEL_NOTES):
        return "cancelled", None, None
    if any(tok in note for tok in _POSTPONE_NOTES):
        return "postponed", None, None
    # "프리뷰" contains "리뷰", so the preview label has to win first.
    if "프리뷰" in relay:
        return "scheduled", None, None
    # win/lose/same spans are the final result.
    if away_score is not None and home_score is not None:
        if away_score == home_score:
            return "tied", away_score, home_score
        return "completed", away_score, home_score
    if "리뷰" in relay:
        return "unknown_result", None, None
    return "scheduled", None, None


def derive_naver_game_id(
    kbo_game_id: str | None,
    date_str: str,
    away_code: str,
    home_code: str,
    series_key: str,
) -> str | None:
    """Build a Naver game id when the KBO id and series follow the known pattern.

    Regular/preseason: ``YYYYMMDD + away + home + seq + year``
    (``20250510LGSS12025``). Postseason swaps the year-month-day prefix for
    4444/3333/5555/7777 (``55551029SSHT02026``). Team letters are the Naver
    codes (HT, SK), which is what ``gameId`` on the KBO page already uses.
    Without a ``gameId``, only sequence 0 is assumed, and only for one game.
    """
    info = _KBO_SERIES_BY_KEY.get(series_key)
    if info is None:
        return None
    _name, prefix = info
    year = date_str[:4]
    ymd = date_str.replace("-", "")
    if kbo_game_id:
        match = re.fullmatch(r"(\d{8})([A-Za-z]{2})([A-Za-z]{2})(\d)", kbo_game_id)
        if not match:
            return None
        id_ymd, away_raw, home_raw, seq = match.groups()
        away_raw = away_raw.upper()
        home_raw = home_raw.upper()
        if id_ymd != ymd:
            return None
        if normalize_code(away_raw) != away_code or normalize_code(home_raw) != home_code:
            return None
    else:
        away_raw = naver_game_code(away_code)
        home_raw = naver_game_code(home_code)
        if not away_raw or not home_raw:
            return None
        seq = "0"
    if prefix:
        return f"{prefix}{ymd[4:]}{away_raw}{home_raw}{seq}{year}"
    return f"{ymd}{away_raw}{home_raw}{seq}{year}"


def parse_kbo_schedule(
    payload: dict, year: int, series_key: str
) -> list[tuple[str, Game]]:
    """Parse one GetScheduleList payload into provisional games.

    Each item is ``(sort_key, game)``. Game ids do not yet have a
    doubleheader suffix; ``assign_game_ids`` adds those in time order.
    Rows that only mark a travel day (이동일) are skipped. A date cell uses
    rowspan for the rest of that day, so later rows reuse the previous date.
    """
    if series_key not in _KBO_SERIES_BY_KEY:
        raise ValueError(f"unknown KBO series {series_key!r}")
    series_name, _prefix = _KBO_SERIES_BY_KEY[series_key]
    current_date: str | None = None
    out: list[tuple[str, Game]] = []
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        cells = row.get("row") or []
        day = time_text = relay = None
        play_raw = ""
        extras: list[str] = []
        raw_bits: list[str] = []
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            raw = cell.get("Text") or ""
            raw_bits.append(raw)
            text = _html_text(raw)
            kind = cell.get("Class") or ""
            if kind == "day" and text:
                day = text
            elif kind == "time":
                time_text = text
            elif kind == "play":
                play_raw = raw
            elif kind == "relay":
                relay = text
            elif text:
                extras.append(text)
        if day:
            day_match = _DAY_RE.search(day)
            if day_match:
                current_date = (
                    f"{year:04d}-{int(day_match.group(1)):02d}-{int(day_match.group(2)):02d}"
                )
        if not current_date or not play_raw:
            continue
        note, stadium = _note_and_stadium(extras)
        if note and "이동일" in note:
            continue
        parsed = _parse_play(play_raw)
        if not parsed:
            continue
        away_name, home_name, away_score, home_score = parsed
        away_code = normalize_code(away_name)
        home_code = normalize_code(home_name)
        if not away_code or not home_code or away_code == home_code:
            continue
        status, away_score, home_score = _status_from_note(
            note, away_score, home_score, relay or ""
        )
        id_match = _KBO_GAME_ID_RE.search(" ".join(raw_bits))
        kbo_game_id = id_match.group(1).upper() if id_match else None
        naver_id = derive_naver_game_id(
            kbo_game_id, current_date, away_code, home_code, series_key
        )
        category = _classify_category(
            {"seriesName": series_name, **({"gameId": naver_id} if naver_id else {})},
            current_date,
        )
        time_match = _TIME_RE.search(time_text or "")
        sort_time = (
            f"{int(time_match.group(1)):02d}:{time_match.group(2)}" if time_match else "99:99"
        )
        game = Game(
            id=f"{current_date}-{away_code}-{home_code}",
            date=current_date,
            awayTeam=away_code,
            homeTeam=home_code,
            awayScore=away_score,
            homeScore=home_score,
            status=status,
            stadium=stadium,
            category=category,
            naverGameId=naver_id,
            naverRecordUrl=(
                f"https://m.sports.naver.com/game/{naver_id}/record" if naver_id else None
            ),
            startTime=sort_time if time_match else None,
        )
        out.append((f"{current_date}T{sort_time}", game))
    return out


def assign_game_ids(entries: list[tuple[str, Game]]) -> list[Game]:
    """Give the earlier game the bare id and later ones ``-2``, ``-3``, ...

    Same rule as the Naver scraper: LocalStorage keys for single games stay
    stable, and a doubleheader does not collapse into one object.
    """
    ordered = sorted(entries, key=lambda item: (item[0], item[1].awayTeam, item[1].homeTeam, item[1].naverGameId or ""))
    seen: dict[str, int] = {}
    out: list[Game] = []
    for _sort_key, game in ordered:
        base = f"{game.date}-{game.awayTeam}-{game.homeTeam}"
        count = seen.get(base, 0)
        game_id = base if count == 0 else f"{base}-{count + 1}"
        seen[base] = count + 1
        out.append(game if game.id == game_id else replace(game, id=game_id))
    counts: dict[str, int] = {}
    for game in out:
        if game.naverGameId:
            counts[game.naverGameId] = counts.get(game.naverGameId, 0) + 1
    cleaned: list[Game] = []
    for game in out:
        if game.naverGameId and counts.get(game.naverGameId, 0) > 1:
            cleaned.append(replace(game, naverGameId=None, naverRecordUrl=None))
        else:
            cleaned.append(game)
    return cleaned


def games_from_kbo_payload(payload: dict, year: int, series_key: str) -> list[Game]:
    return assign_game_ids(parse_kbo_schedule(payload, year, series_key))


def fetch_kbo_schedule(year: int, month: int, sr_id_list: str, retries: int = 3, timeout: float = 30) -> dict:
    """POST one month of one series. Raises after the retries are exhausted."""
    form = {
        "leId": "1",
        "srIdList": sr_id_list,
        "seasonId": str(year),
        "gameMonth": f"{month:02d}",
        "teamId": "",
    }
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.post(KBO_URL, headers=KBO_HEADERS, data=form, timeout=timeout)
            print(
                f"    KBO sr={sr_id_list} HTTP {response.status_code}, {len(response.content)} bytes",
                file=sys.stderr,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
                raise RuntimeError("KBO payload has no rows list")
            return payload
        except Exception as exc:
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"KBO {year}-{month:02d} sr={sr_id_list}: {last_err}")


def _fetch_month_kbo(year: int, month: int) -> list[tuple[str, Game]]:
    entries: list[tuple[str, Game]] = []
    for index, (series_key, _name, _prefix) in enumerate(KBO_SERIES):
        if index:
            time.sleep(0.15)
        payload = fetch_kbo_schedule(year, month, series_key)
        entries.extend(parse_kbo_schedule(payload, year, series_key))
    return entries


def _fetch_month_naver(year: int, month: int) -> list[tuple[str, Game]]:
    last_day = calendar.monthrange(year, month)[1]
    first = dt.date(year, month, 1)
    last = dt.date(year, month, last_day)
    payload = fetch_range(first.isoformat(), last.isoformat())
    raws = _extract_games(payload)
    raws.sort(key=lambda raw: str(_pluck(raw, "gameDateTime") or _pluck(raw, "gameDate") or ""))
    _record_debug(payload, raws)
    entries: list[tuple[str, Game]] = []
    for raw in raws:
        game = _normalize_game(raw)
        if game is None:
            continue
        sort_key = str(_pluck(raw, "gameDateTime") or game.date)
        entries.append((sort_key, game))
    return entries


def _fetch_month(year: int, month: int, source: str) -> list[tuple[str, Game]]:
    if source == "naver":
        return _fetch_month_naver(year, month)
    if source == "kbo":
        return _fetch_month_kbo(year, month)
    if source == "kbo-naver":
        try:
            return _fetch_month_kbo(year, month)
        except Exception as exc:
            print(
                f"  warning: KBO {year}-{month:02d} failed ({exc}); trying Naver",
                file=sys.stderr,
            )
            return _fetch_month_naver(year, month)
    raise ValueError(f"unknown --source {source!r}")


def scrape_year(year: int, months: Iterable[int] = range(3, 12), source: str = "kbo") -> ScrapeResult:
    """Fetch each month. A failed month is recorded and does not raise.

    Callers keep the games already on disk for ``failed_months`` and continue
    with the months that returned.
    """
    entries: list[tuple[str, Game]] = []
    failed_months: list[int] = []
    succeeded_months: list[int] = []
    month_list = list(months)
    for index, month in enumerate(month_list):
        print(f"  fetching {year}-{month:02d} via {source} ...", file=sys.stderr)
        try:
            month_entries = _fetch_month(year, month, source)
        except Exception as exc:
            print(
                f"  warning: {year}-{month:02d} failed ({exc}); keeping existing games for this month",
                file=sys.stderr,
            )
            failed_months.append(month)
            continue
        succeeded_months.append(month)
        print(f"    -> {len(month_entries)} games", file=sys.stderr)
        entries.extend(month_entries)
        if index != len(month_list) - 1:
            time.sleep(0.15)
    deduped: list[tuple[str, Game]] = []
    seen_naver: set[str] = set()
    for sort_key, game in entries:
        if game.naverGameId:
            if game.naverGameId in seen_naver:
                continue
            seen_naver.add(game.naverGameId)
        deduped.append((sort_key, game))
    return ScrapeResult(
        games=assign_game_ids(deduped),
        failed_months=failed_months,
        succeeded_months=succeeded_months,
    )


def load_existing_games(year: int) -> list[Game]:
    path = DATA_DIR / f"{year}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  warning: could not read {path}: {exc}", file=sys.stderr)
        return []
    games: list[Game] = []
    for raw in payload.get("games") or []:
        if not isinstance(raw, dict) or "id" not in raw or "date" not in raw:
            continue
        games.append(
            Game(
                id=str(raw["id"]),
                date=str(raw["date"]),
                awayTeam=str(raw.get("awayTeam") or ""),
                homeTeam=str(raw.get("homeTeam") or ""),
                awayScore=raw.get("awayScore"),
                homeScore=raw.get("homeScore"),
                status=str(raw.get("status") or "scheduled"),
                stadium=raw.get("stadium"),
                category=str(raw.get("category") or "unknown"),
                naverGameId=raw.get("naverGameId"),
                naverRecordUrl=raw.get("naverRecordUrl"),
                startTime=raw.get("startTime"),
            )
        )
    return games


def _allocate_id(provisional: str, seen: set[str]) -> str:
    parts = provisional.split("-")
    if len(parts) >= 6 and parts[-1].isdigit():
        base = "-".join(parts[:-1])
    else:
        base = provisional
    if base not in seen:
        return base
    number = 2
    while f"{base}-{number}" in seen:
        number += 1
    return f"{base}-{number}"


def merge_games(existing: list[Game], fetched: list[Game], failed_months: set[int]) -> list[Game]:
    """Update scores, status, and stadium. Keep every other field already on disk.

    Matching prefers ``naverGameId`` so a doubleheader suffix stays put even
    when this run only sees one of the two games. Months in ``failed_months``
    are copied through unchanged. Games that are not in the new payload are
    kept, and games that are only in the new payload are appended.
    """
    def month_of(game: Game) -> int:
        return int(game.date[5:7])

    fresh_pool = [game for game in fetched if month_of(game) not in failed_months]
    by_naver: dict[str, list[int]] = {}
    by_id: dict[str, list[int]] = {}
    for index, game in enumerate(fresh_pool):
        if game.naverGameId:
            by_naver.setdefault(game.naverGameId, []).append(index)
        by_id.setdefault(game.id, []).append(index)

    used: set[int] = set()

    def take(indexes: list[int]) -> Game | None:
        for index in indexes:
            if index not in used:
                used.add(index)
                return fresh_pool[index]
        return None

    out: list[Game] = []
    seen_ids: set[str] = set()
    for old in existing:
        if month_of(old) in failed_months:
            out.append(old)
            seen_ids.add(old.id)
            continue
        fresh = None
        if old.naverGameId and old.naverGameId in by_naver:
            fresh = take(by_naver[old.naverGameId])
        if fresh is None and old.id in by_id:
            for index in by_id[old.id]:
                if index in used:
                    continue
                candidate = fresh_pool[index]
                if old.naverGameId and candidate.naverGameId and candidate.naverGameId != old.naverGameId:
                    continue
                used.add(index)
                fresh = candidate
                break
        if fresh is None:
            # Successful collection no longer confirms this pending game.
            # Keep its stable id for attendance/backup compatibility.
            out.append(replace(old, status="unconfirmed", awayScore=None, homeScore=None)
                       if old.status == "scheduled" else old)
            seen_ids.add(old.id)
            continue
        out.append(
            replace(
                old,
                awayScore=fresh.awayScore,
                homeScore=fresh.homeScore,
                status=fresh.status,
                stadium=fresh.stadium or old.stadium,
                startTime=fresh.startTime or old.startTime,
            )
        )
        seen_ids.add(old.id)

    for index, game in enumerate(fresh_pool):
        if index in used:
            continue
        game_id = _allocate_id(game.id, seen_ids)
        out.append(game if game.id == game_id else replace(game, id=game_id))
        seen_ids.add(game_id)

    # A missing schedule is not proof of cancellation. Only a clinched series
    # can positively establish that later games will not be played.
    # WC and older best-of-seven PO formats deliberately require manual review.
    series_wins: dict[tuple[str, tuple[str, ...]], dict[str, int]] = {}
    clinched: dict[tuple[str, tuple[str, ...]], str] = {}
    for game in sorted(out, key=lambda g: g.date):
        prefix = (game.naverGameId or "")[:4]
        target = 4 if prefix == "7777" else 3 if prefix in {"3333", "5555"} and game.date >= "2022-01-01" else None
        if target is None or game.status != "completed" or game.awayScore is None or game.homeScore is None:
            continue
        key = (prefix, tuple(sorted((game.awayTeam, game.homeTeam))))
        winner = game.awayTeam if game.awayScore > game.homeScore else game.homeTeam
        wins = series_wins.setdefault(key, {})
        wins[winner] = wins.get(winner, 0) + 1
        if wins[winner] >= target:
            clinched.setdefault(key, game.date)
    today = dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    reconciled = []
    for game in out:
        if month_of(game) in failed_months:
            reconciled.append(game)
            continue
        key = ((game.naverGameId or "")[:4], tuple(sorted((game.awayTeam, game.homeTeam))))
        if game.status in {"scheduled", "unconfirmed"} and key in clinched and game.date > clinched[key]:
            game = replace(game, status="not_required", awayScore=None, homeScore=None)
        elif game.status == "scheduled" and dt.date.fromisoformat(game.date) < today - dt.timedelta(days=2):
            game = replace(game, status="unconfirmed", awayScore=None, homeScore=None)
        reconciled.append(game)
    out = reconciled
    out.sort(key=lambda game: (game.date, game.awayTeam, game.id))
    return out


def write_season(year: int, games: list[Game], failed_months: list[int] | None = None) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{year}.json"
    failed_months = failed_months or []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    payload = {
        "year": year,
        "generatedAt": previous.get("generatedAt", "") if failed_months else now,
        "refresh": {"attemptedAt": now, "failedMonths": sorted(set(failed_months))},
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
    ap.add_argument(
        "--source",
        choices=("kbo", "naver", "kbo-naver"),
        default="kbo",
        help="kbo (default, works from GitHub runners), naver, or kbo with a Naver fallback",
    )
    args = ap.parse_args()

    years = [args.year] if args.year else parse_year_range(args.years)
    months = [args.month] if args.month else range(3, 12)
    current_year = current_season_year()
    # Non-zero only when the season that is actually in progress produced
    # nothing. A past season that fails, or one bad month inside an otherwise
    # useful scrape, does not fail the run.
    current_produced_nothing = False

    for y in years:
        print(f"== {y} ({args.source}) ==", file=sys.stderr)
        result = scrape_year(y, months, source=args.source)
        if args.month:
            # A month is a diagnostic subset, not a replacement for a
            # published season. Keep data/seasons/<year>.json untouched.
            print(
                f"  diagnostic month {args.month}: {len(result.games)} games; season file unchanged",
                file=sys.stderr,
            )
            continue
        if not result.games:
            # Nothing fetched (every month failed, or the schedule is empty).
            # Leave the file alone so generatedAt does not look fresh.
            print(f"  no games for {y}; season file not written", file=sys.stderr)
            if y == current_year:
                current_produced_nothing = True
            continue
        existing = load_existing_games(y)
        merged = merge_games(existing, result.games, set(result.failed_months))
        if not merged:
            print(f"  no games for {y}; season file not written", file=sys.stderr)
            if y == current_year:
                current_produced_nothing = True
            continue
        out = write_season(y, merged, failed_months=result.failed_months)
        if result.failed_months:
            print(
                f"  wrote {len(merged)} games -> {out} "
                f"(kept existing games for failed months {result.failed_months})",
                file=sys.stderr,
            )
        else:
            print(f"  wrote {len(merged)} games -> {out}", file=sys.stderr)

    if _debug_state["first_payload_seen"]:
        _flush_debug()
    return 1 if current_produced_nothing else 0


if __name__ == "__main__":
    raise SystemExit(main())

