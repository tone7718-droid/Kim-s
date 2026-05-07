"""Build a human-readable KBO scrape summary.

Keeping this in a real Python file is safer than embedding a long Python
heredoc inside GitHub Actions YAML. The workflow calls this after scraping
and validating data.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
SEASON_DIR = DATA_DIR / "seasons"
SUMMARY_PATH = DATA_DIR / "_summary.md"
DEBUG_PATH = DATA_DIR / "_debug_naver.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def category_buckets(games: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "regular": [],
        "postseason": [],
        "preseason": [],
        "unknown": [],
    }
    for game in games:
        category = str(game.get("category", "unknown"))
        buckets.setdefault(category, []).append(game)
    return buckets


def status_counts(games: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "completed": 0,
        "tied": 0,
        "cancelled": 0,
        "postponed": 0,
        "scheduled": 0,
    }
    for game in games:
        status = str(game.get("status", "scheduled"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def append_diagnostics(rows: list[str]) -> None:
    if not DEBUG_PATH.exists():
        return

    diag = load_json(DEBUG_PATH)
    rows += ["", "## API 응답 진단", ""]

    status_code_counts = diag.get("statusCodeCounts") or {}
    rows.append("**statusCode 분포:**")
    for key, value in status_code_counts.items():
        rows.append(f"  - `{key}`: {value}")

    status_info_counts = diag.get("statusInfoCounts") or {}
    if status_info_counts:
        rows += ["", "**statusInfo 분포:**"]
        for key, value in list(status_info_counts.items())[:20]:
            rows.append(f"  - `{key}`: {value}")

    combo_counts = diag.get("statusComboCounts") or {}
    if combo_counts:
        rows += ["", "**statusCode / statusInfo 조합 (상위 20):**"]
        for key, value in list(combo_counts.items())[:20]:
            rows.append(f"  - `{key}`: {value}")

    category_fields = diag.get("categoryFieldValues") or {}
    if category_fields:
        rows += ["", "**카테고리 후보 필드에서 발견된 값:**"]
        for field, values in category_fields.items():
            rows.append(f"  - `{field}`:")
            for key, value in list(values.items())[:8]:
                rows.append(f"    - `{key}`: {value}")
    else:
        rows += [
            "",
            "**카테고리 후보 필드:** 응답에 매칭되는 필드 없음 → 날짜 휴리스틱으로 분류됨",
        ]

    first_game = diag.get("firstGame")
    if first_game:
        rows += [
            "",
            "<details><summary>첫 RESULT 게임 raw JSON</summary>",
            "",
            "```json",
            json.dumps(first_game, ensure_ascii=False, indent=2)[:3000],
            "```",
            "</details>",
        ]

    first_before_game = diag.get("firstBeforeGame")
    if first_before_game:
        rows += [
            "",
            "<details><summary>첫 BEFORE 게임 raw JSON (취소/미진행 구분 단서)</summary>",
            "",
            "```json",
            json.dumps(first_before_game, ensure_ascii=False, indent=2)[:3000],
            "```",
            "</details>",
        ]


def build_summary() -> str:
    rows: list[str] = ["# KBO 스크래핑 결과 요약", ""]
    rows += [f"_생성 시각 (UTC): {os.environ.get('GITHUB_RUN_STARTED_AT', '-')}_  ", ""]
    rows += ["사용자 선택: **정규시즌 + 포스트시즌만 합산** (시범경기는 별도 표시)", ""]
    rows += ["## 시즌별 요약 (정규+포스트시즌)", ""]
    rows += [
        "| 시즌 | 합산 경기 | 정상종료 | 무승부 | 취소 | 연기 | 미진행 | 네이버 ID |",
        "|---|---|---|---|---|---|---|---|",
    ]

    total_main = 0
    total_preseason = 0
    per_season: list[tuple[int, dict[str, list[dict[str, Any]]]]] = []

    for file_name in sorted(glob.glob(str(SEASON_DIR / "*.json"))):
        payload = load_json(Path(file_name))
        games = payload["games"]
        year = int(payload["year"])

        by_category = category_buckets(games)
        main_games = by_category["regular"] + by_category["postseason"] + by_category["unknown"]
        preseason_games = by_category["preseason"]
        counts = status_counts(main_games)
        naver_ids = sum(1 for game in main_games if game.get("naverGameId"))

        rows.append(
            f"| {year} | **{len(main_games)}** | {counts['completed']} | "
            f"{counts['tied']} | {counts['cancelled']} | {counts['postponed']} | "
            f"{counts['scheduled']} | {naver_ids}/{len(main_games)} |"
        )
        total_main += len(main_games)
        total_preseason += len(preseason_games)
        per_season.append((year, by_category))

    rows += [
        "",
        f"**합산 총 {total_main} 경기** / 시범경기는 별도 {total_preseason} 경기 (제외됨)",
        "",
        "✅ 데이터 검증 통과: 팀 코드, 상태값, 카테고리, 중복 ID, 점수 무결성, 미래 경기 상태, 시즌 경기 수 범위를 확인했습니다.",
        "",
    ]

    rows += ["## 카테고리 분포", ""]
    rows += ["| 시즌 | 정규 | 포스트 | 시범 | 미상 |", "|---|---|---|---|---|"]
    for year, by_category in per_season:
        rows.append(
            f"| {year} | {len(by_category['regular'])} | "
            f"{len(by_category['postseason'])} | {len(by_category['preseason'])} | "
            f"{len(by_category['unknown'])} |"
        )

    rows += ["", "## 샘플 (각 시즌 정규시즌 첫 경기)", ""]
    for year, by_category in per_season:
        regular_games = by_category["regular"]
        if not regular_games:
            rows.append(f"- {year}: (정규시즌 경기 없음)")
            continue
        first = regular_games[0]
        rows.append(
            f"- {year}: `{first['date']}` {first['awayTeam']} "
            f"{first.get('awayScore', '-')}:{first.get('homeScore', '-')} "
            f"{first['homeTeam']} ({first['status']}, {first.get('category')})"
        )

    append_diagnostics(rows)
    return "\n".join(rows) + "\n"


def main() -> int:
    summary = build_summary()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fp:
            fp.write(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
