"""Unit tests for the KBO scraper's pure parsing/classification logic.

Run with:
    pip install -r requirements.txt -r requirements-dev.txt
    pytest
"""

from __future__ import annotations

from scrape_kbo import (
    _classify_category,
    _coerce_score,
    _normalize_game,
)
from teams import normalize_code


class TestNormalizeCode:
    def test_known_aliases_map_to_canonical(self):
        assert normalize_code("HT") == "KIA"   # Naver code for KIA
        assert normalize_code("SK") == "SSG"   # SK Wyverns -> SSG Landers
        assert normalize_code("넥센") == "WO"  # Nexen -> Kiwoom
        assert normalize_code("두산") == "OB"

    def test_unknown_is_empty(self):
        assert normalize_code("ZZZ") == ""
        assert normalize_code("") == ""


class TestCoerceScore:
    def test_int_passthrough(self):
        assert _coerce_score(5) == 5
        assert _coerce_score(0) == 0

    def test_numeric_string(self):
        assert _coerce_score("3") == 3
        assert _coerce_score(" 7 ".strip()) == 7

    def test_non_numeric_and_missing(self):
        assert _coerce_score(None) is None
        assert _coerce_score("") is None
        assert _coerce_score("-") is None
        assert _coerce_score("abc") is None


class TestClassifyCategory:
    def test_preseason_before_regular_opening(self):
        assert _classify_category({}, "2024-03-08") == "preseason"

    def test_regular_on_and_after_opening(self):
        assert _classify_category({}, "2024-03-23") == "regular"  # 2024 opening
        assert _classify_category({}, "2024-07-01") == "regular"

    def test_postseason_uses_configured_wildcard_date(self):
        # 2024 와일드카드 결정전 1차전 = 2024-10-02
        assert _classify_category({}, "2024-10-01") == "regular"
        assert _classify_category({}, "2024-10-02") == "postseason"
        assert _classify_category({}, "2024-10-22") == "postseason"  # 한국시리즈

    def test_2021_extended_regular_season_not_postseason(self):
        # 2021 regular season ran late (Olympics break); 와카 was 2021-11-01.
        # The old fixed Oct-22 cutoff misfiled these late-October games.
        assert _classify_category({}, "2021-10-30") == "regular"
        assert _classify_category({}, "2021-10-31") == "regular"
        assert _classify_category({}, "2021-11-01") == "postseason"

    def test_all_configured_seasons_boundary(self):
        boundaries = {
            2021: "2021-11-01",
            2022: "2022-10-13",
            2023: "2023-10-19",
            2024: "2024-10-02",
            2025: "2025-10-06",
        }
        for year, opening in boundaries.items():
            assert _classify_category({}, opening) == "postseason"

    def test_unconfigured_season_falls_back_to_heuristic(self):
        # A season with no hardcoded dates uses the late-October heuristic.
        assert _classify_category({}, "2099-10-25") == "postseason"
        assert _classify_category({}, "2099-05-01") == "regular"

    def test_explicit_category_field_wins_over_dates(self):
        assert _classify_category({"seriesName": "시범경기"}, "2024-06-01") == "preseason"
        assert _classify_category({"gameKindName": "한국시리즈"}, "2024-06-01") == "postseason"

    def test_bad_date_is_unknown(self):
        assert _classify_category({}, "not-a-date") == "unknown"


class TestNormalizeGame:
    def _raw(self, **overrides):
        raw = {
            "gameId": "20240323HTSS02024",
            "gameDate": "2024-03-23",
            "gameDateTime": "2024-03-23T14:00:00",
            "homeTeamCode": "SS",
            "homeTeamName": "삼성",
            "homeTeamScore": 3,
            "awayTeamCode": "HT",
            "awayTeamName": "KIA",
            "awayTeamScore": 5,
            "statusCode": "RESULT",
            "statusInfo": "종료",
            "stadium": "대구",
        }
        raw.update(overrides)
        return raw

    def test_completed_game_basic_fields(self):
        g = _normalize_game(self._raw())
        assert g is not None
        assert g.awayTeam == "KIA"  # HT normalized
        assert g.homeTeam == "SS"
        assert g.awayScore == 5 and g.homeScore == 3
        assert g.status == "completed"
        assert g.category == "regular"
        assert g.id == "2024-03-23-KIA-SS"
        assert g.naverGameId == "20240323HTSS02024"
        assert g.naverRecordUrl.endswith("/20240323HTSS02024/record")

    def test_equal_scores_when_finished_is_tie(self):
        g = _normalize_game(self._raw(homeTeamScore=4, awayTeamScore=4))
        assert g.status == "tied"

    def test_future_game_with_zero_scores_stays_scheduled(self):
        # The important regression: a 0:0 BEFORE game must not be a tie.
        g = _normalize_game(
            self._raw(
                gameDate="2026-08-01",
                statusCode="BEFORE",
                statusInfo="",
                homeTeamScore=0,
                awayTeamScore=0,
            )
        )
        assert g.status == "scheduled"

    def test_status_info_overrides_before_code(self):
        # statusCode stuck at BEFORE but statusInfo says rain-cancelled.
        g = _normalize_game(
            self._raw(statusCode="BEFORE", statusInfo="우천취소", homeTeamScore=None, awayTeamScore=None)
        )
        assert g.status == "cancelled"

    def test_postpone_detected_from_status_info(self):
        g = _normalize_game(
            self._raw(statusCode="BEFORE", statusInfo="연기", homeTeamScore=None, awayTeamScore=None)
        )
        assert g.status == "postponed"

    def test_unknown_team_is_dropped(self):
        assert _normalize_game(self._raw(awayTeamCode="ZZZ", awayTeamName="")) is None

    def test_bad_date_is_dropped(self):
        assert _normalize_game(self._raw(gameDate="", gameDateTime="")) is None
