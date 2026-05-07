"""Validate generated KBO season JSON before committing it.

This script is intentionally conservative. Its job is not to prove every
baseball fact is correct; it catches schema drift, partial debug scrapes,
unknown teams/statuses/categories, duplicate IDs, and obviously impossible
future/completed-state combinations before bad data reaches Vercel.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ALLOWED_TEAMS = {"KIA", "SS", "LG", "OB", "KT", "SSG", "LT", "HH", "NC", "WO"}
ALLOWED_STATUSES = {"completed", "tied", "cancelled", "postponed", "scheduled"}
ALLOWED_CATEGORIES = {"regular", "postseason", "preseason", "unknown"}

# Full-season scrape should be roughly 720 regular games plus cancellations,
# postseason, and a little API/category noise. If this drops below 300, it is
# almost certainly a partial/manual month scrape or API wrapper breakage.
MIN_MAIN_GAMES_PER_SEASON = 300
MAX_MAIN_GAMES_PER_SEASON = 1000
MAX_UNKNOWN_CATEGORY_GAMES = 40

ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[A-Z0-9]+-[A-Z0-9]+(?:-\d+)?$")


def today_kst() -> dt.date:
    return dt.datetime.now(ZoneInfo("Asia/Seoul")).date()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: JSON parse failed: {exc}") from exc


def parse_date(path: Path, game: dict, index: int) -> dt.date:
    raw = game.get("date")
    if not isinstance(raw, str):
        raise ValueError(f"{path}: games[{index}].date must be YYYY-MM-DD string")
    try:
        return dt.date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{path}: games[{index}].date is invalid: {raw!r}") from exc


def validate_score(path: Path, game: dict, index: int, field: str) -> int | None:
    value = game.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path}: games[{index}].{field} must be int or null")
    if value < 0:
        raise ValueError(f"{path}: games[{index}].{field} must not be negative")
    return value


def validate_file(path: Path, current_date: dt.date) -> list[str]:
    payload = load_json(path)
    warnings: list[str] = []

    year = payload.get("year")
    if not isinstance(year, int):
        raise ValueError(f"{path}: payload.year must be an integer")
    if path.stem.isdigit() and int(path.stem) != year:
        raise ValueError(f"{path}: filename year and payload.year differ")

    games = payload.get("games")
    if not isinstance(games, list):
        raise ValueError(f"{path}: payload.games must be a list")
    if not games:
        raise ValueError(f"{path}: games is empty")

    seen_ids: set[str] = set()
    main_count = 0
    unknown_count = 0
    future_finished: list[str] = []

    for i, game in enumerate(games):
        if not isinstance(game, dict):
            raise ValueError(f"{path}: games[{i}] must be an object")

        game_id = game.get("id")
        if not isinstance(game_id, str) or not ID_RE.match(game_id):
            raise ValueError(f"{path}: games[{i}].id has unexpected format: {game_id!r}")
        if game_id in seen_ids:
            raise ValueError(f"{path}: duplicate game id: {game_id}")
        seen_ids.add(game_id)

        date = parse_date(path, game, i)
        if date.year != year:
            raise ValueError(f"{path}: {game_id} date year does not match payload.year")

        away = game.get("awayTeam")
        home = game.get("homeTeam")
        if away not in ALLOWED_TEAMS:
            raise ValueError(f"{path}: {game_id} unknown awayTeam: {away!r}")
        if home not in ALLOWED_TEAMS:
            raise ValueError(f"{path}: {game_id} unknown homeTeam: {home!r}")
        if away == home:
            raise ValueError(f"{path}: {game_id} has same away/home team")

        status = game.get("status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"{path}: {game_id} unknown status: {status!r}")

        category = game.get("category", "unknown")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"{path}: {game_id} unknown category: {category!r}")
        if category != "preseason":
            main_count += 1
        if category == "unknown":
            unknown_count += 1

        away_score = validate_score(path, game, i, "awayScore")
        home_score = validate_score(path, game, i, "homeScore")
        if status in {"completed", "tied"}:
            if away_score is None or home_score is None:
                raise ValueError(f"{path}: {game_id} is {status} but score is null")
            if status == "tied" and away_score != home_score:
                raise ValueError(f"{path}: {game_id} is tied but scores differ")
            if status == "completed" and away_score == home_score:
                raise ValueError(f"{path}: {game_id} is completed but scores are tied")
        if date > current_date and status in {"completed", "tied"}:
            future_finished.append(game_id)

        naver_url = game.get("naverRecordUrl")
        if naver_url is not None:
            if not isinstance(naver_url, str) or not naver_url.startswith("https://m.sports.naver.com/game/"):
                raise ValueError(f"{path}: {game_id} has unexpected naverRecordUrl: {naver_url!r}")

    if main_count < MIN_MAIN_GAMES_PER_SEASON:
        raise ValueError(
            f"{path}: only {main_count} regular/postseason/unknown games. "
            "This looks like a partial scrape or API schema break."
        )
    if main_count > MAX_MAIN_GAMES_PER_SEASON:
        raise ValueError(
            f"{path}: {main_count} regular/postseason/unknown games exceeds safety limit"
        )
    if unknown_count > MAX_UNKNOWN_CATEGORY_GAMES:
        raise ValueError(
            f"{path}: {unknown_count} games have unknown category; category detection likely broke"
        )
    if future_finished:
        sample = ", ".join(future_finished[:5])
        raise ValueError(f"{path}: future games marked completed/tied: {sample}")

    warnings.append(
        f"{path.name}: ok — {len(games)} total, {main_count} main, "
        f"{unknown_count} unknown-category"
    )
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent.parent / "data" / "seasons"),
        help="Directory containing YYYY.json season files",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(data_dir.glob("*.json"))
    if not files:
        print(f"No season files found in {data_dir}", file=sys.stderr)
        return 1

    current_date = today_kst()
    all_messages: list[str] = []
    try:
        for path in files:
            all_messages.extend(validate_file(path, current_date))
    except ValueError as exc:
        print(f"KBO data validation failed: {exc}", file=sys.stderr)
        return 1

    print("KBO data validation passed.")
    for msg in all_messages:
        print(f"  - {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
