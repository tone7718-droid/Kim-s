"""Unit tests for the KBO scraper's pure parsing/classification logic.

Run with:
    pip install -r requirements.txt -r requirements-dev.txt
    pytest
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import scrape_kbo

from scrape_kbo import (
    Game,
    ScrapeResult,
    _classify_category,
    _coerce_score,
    _normalize_game,
    games_from_kbo_payload,
    merge_games,
)
from teams import naver_game_code, normalize_code

FIXTURE = Path(__file__).parent / "fixtures" / "kbo_schedule_sample.json"


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

    def test_postseason_detected_from_naver_game_id_prefix(self):
        # Date alone says regular here (season not configured, before Oct 22).
        for prefix in ("4444", "3333", "5555", "7777"):
            raw = {"gameId": f"{prefix}1017LGHT02099"}
            assert _classify_category(raw, "2099-10-17") == "postseason"

    def test_regular_and_allstar_game_ids_are_not_postseason(self):
        assert _classify_category({"gameId": "20990717LGHT02099"}, "2099-07-17") == "regular"
        assert _classify_category({"gameId": "66660712EAWE02099"}, "2099-07-12") == "regular"

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

    def test_finished_game_without_scores_is_not_scheduled(self):
        g = _normalize_game(
            self._raw(statusCode="RESULT", statusInfo="종료", homeTeamScore=None, awayTeamScore=None)
        )
        assert g.status == "unknown_result"

    def test_unknown_team_is_dropped(self):
        assert _normalize_game(self._raw(awayTeamCode="ZZZ", awayTeamName="")) is None

    def test_bad_date_is_dropped(self):
        assert _normalize_game(self._raw(gameDate="", gameDateTime="")) is None


def _sample_game(**overrides) -> Game:
    game = Game(
        id="2026-04-01-LG-NC",
        date="2026-04-01",
        awayTeam="LG",
        homeTeam="NC",
        awayScore=5,
        homeScore=3,
        status="completed",
        stadium="잠실",
        category="regular",
        naverGameId="20260401LGNC02026",
        naverRecordUrl="https://m.sports.naver.com/game/20260401LGNC02026/record",
    )
    return game if not overrides else scrape_kbo.replace(game, **overrides)


def test_month_diagnostic_does_not_overwrite_season(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrape_kbo.py", "--year", "2024", "--month", "4"])
    monkeypatch.setattr(
        scrape_kbo,
        "scrape_year",
        lambda year, months, source="kbo": ScrapeResult([], [], []),
    )
    monkeypatch.setattr(scrape_kbo, "_flush_debug", lambda: None)

    def fail_if_written(*args):
        raise AssertionError("monthly diagnostic must not write data/seasons")

    monkeypatch.setattr(scrape_kbo, "write_season", fail_if_written)
    assert scrape_kbo.main() == 0


def test_empty_season_is_not_written(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrape_kbo.py", "--years", "2026-2027"])
    monkeypatch.setattr(scrape_kbo, "current_season_year", lambda: 2026)

    def fake_scrape(year, months, source="kbo"):
        if year == 2027:
            return ScrapeResult([], [], [3])
        return ScrapeResult([_sample_game()], [], [4])

    monkeypatch.setattr(scrape_kbo, "scrape_year", fake_scrape)
    monkeypatch.setattr(scrape_kbo, "load_existing_games", lambda year: [])
    monkeypatch.setattr(scrape_kbo, "_flush_debug", lambda: None)
    written = []
    monkeypatch.setattr(scrape_kbo, "write_season", lambda y, g, **kwargs: written.append(y) or y)
    assert scrape_kbo.main() == 0
    assert written == [2026]


def test_current_season_with_no_games_exits_nonzero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrape_kbo.py", "--year", "2026"])
    monkeypatch.setattr(scrape_kbo, "current_season_year", lambda: 2026)
    monkeypatch.setattr(
        scrape_kbo,
        "scrape_year",
        lambda year, months, source="kbo": ScrapeResult([], [3, 4, 5], []),
    )
    monkeypatch.setattr(scrape_kbo, "_flush_debug", lambda: None)

    def fail_if_written(*args):
        raise AssertionError("a failed current season must not rewrite the file")

    monkeypatch.setattr(scrape_kbo, "write_season", fail_if_written)
    assert scrape_kbo.main() == 1


def test_past_season_failure_does_not_fail_the_run(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrape_kbo.py", "--year", "2024"])
    monkeypatch.setattr(scrape_kbo, "current_season_year", lambda: 2026)
    monkeypatch.setattr(
        scrape_kbo,
        "scrape_year",
        lambda year, months, source="kbo": ScrapeResult([], [4], []),
    )
    monkeypatch.setattr(scrape_kbo, "_flush_debug", lambda: None)
    monkeypatch.setattr(
        scrape_kbo,
        "write_season",
        lambda *args: (_ for _ in ()).throw(AssertionError("must not write")),
    )
    assert scrape_kbo.main() == 0


def test_failed_month_does_not_abort(monkeypatch):
    april = ("2026-04-01T18:30", _sample_game())

    def fake_fetch(year, month, source):
        if month == 5:
            raise RuntimeError("Read timed out")
        return [april]

    monkeypatch.setattr(scrape_kbo, "_fetch_month", fake_fetch)
    result = scrape_kbo.scrape_year(2026, [4, 5], source="kbo")
    assert result.failed_months == [5]
    assert result.succeeded_months == [4]
    assert [game.id for game in result.games] == ["2026-04-01-LG-NC"]


def _fixture_slices():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["slices"]


def _games_by_slice_index():
    return [games_from_kbo_payload(item["payload"], item["year"], item["srIdList"]) for item in _fixture_slices()]


class TestKboScheduleFixture:
    """Parser coverage against a saved GetScheduleList response."""

    def test_playoff_scores_status_stadium_and_naver_id(self):
        games = {game.id: game for game in _games_by_slice_index()[0]}
        cancelled = games["2026-10-25-KIA-SS"]
        assert cancelled.status == "cancelled"
        assert cancelled.awayScore is None and cancelled.homeScore is None
        assert cancelled.stadium == "대구"
        assert cancelled.category == "postseason"
        assert cancelled.naverGameId == "55551025HTSS02026"

        first = games["2026-10-26-KIA-SS"]
        assert first.status == "completed"
        assert (first.awayScore, first.homeScore) == (5, 1)
        assert first.stadium == "대구"
        assert first.naverGameId == "55551026HTSS02026"
        assert first.naverRecordUrl.endswith("/55551026HTSS02026/record")

        third = games["2026-10-29-SS-KIA"]
        assert (third.awayTeam, third.homeTeam) == ("SS", "KIA")
        assert (third.awayScore, third.homeScore) == (6, 4)
        assert third.stadium == "광주"
        assert third.category == "postseason"
        assert third.naverGameId == "55551029SSHT02026"

    def test_korean_series_scheduled_without_a_published_game_id(self):
        games = {game.id: game for game in _games_by_slice_index()[1]}
        opener = games["2026-11-03-SS-KT"]
        assert opener.status == "scheduled"
        assert opener.awayScore is None and opener.homeScore is None
        assert opener.stadium == "수원"
        assert opener.category == "postseason"
        assert opener.naverGameId == "77771103SSKT02026"

        # 11.10 has teams, a stadium, and no gameId link yet. Sequence 0 is
        # the only pattern seen on single postseason games.
        later = games["2026-11-10-SS-KT"]
        assert later.status == "scheduled"
        assert later.stadium == "수원"
        assert later.naverGameId == "77771110SSKT02026"

    def test_cancelled_continuation_rows_keep_the_rowspan_date(self):
        games = {game.id: game for game in _games_by_slice_index()[2]}
        assert games["2026-04-09-WO-OB"].status == "cancelled"
        assert games["2026-04-09-WO-OB"].stadium == "잠실"
        assert games["2026-04-09-KT-LT"].stadium == "사직"
        assert games["2026-04-09-HH-SSG"].status == "cancelled"
        assert games["2026-04-09-HH-SSG"].stadium == "문학"
        assert games["2026-04-09-HH-SSG"].naverGameId == "20260409HHSK02026"
        assert all(game.category == "regular" for game in games.values())

    def test_same_score_class_is_a_tie_and_preseason(self):
        games = {game.id: game for game in _games_by_slice_index()[3]}
        tie = games["2026-03-13-KT-LT"]
        assert tie.status == "tied"
        assert (tie.awayScore, tie.homeScore) == (6, 6)
        assert tie.stadium == "사직"
        assert tie.category == "preseason"
        assert tie.naverGameId == "20260313KTLT02026"

    def test_ground_condition_is_cancelled(self):
        games = {game.id: game for game in _games_by_slice_index()[4]}
        assert games["2026-08-28-WO-OB"].status == "cancelled"
        assert games["2026-08-28-WO-OB"].stadium == "잠실"
        assert games["2026-08-16-HH-SS"].status == "cancelled"
        assert games["2026-08-16-HH-SS"].stadium == "대구"

    def test_doubleheader_ids_follow_start_time_and_naver_sequence(self):
        games = [game for game in _games_by_slice_index()[5] if game.awayTeam == "LG"]
        assert [game.id for game in games] == ["2025-05-10-LG-SS", "2025-05-10-LG-SS-2"]
        assert games[0].naverGameId == "20250510LGSS12025"
        assert games[1].naverGameId == "20250510LGSS22025"
        assert (games[0].awayScore, games[0].homeScore) == (5, 4)
        assert (games[1].awayScore, games[1].homeScore) == (4, 1)

    def test_postponed_note_maps_to_postponed(self):
        payload = copy.deepcopy(_fixture_slices()[2]["payload"])
        replaced = False
        for row in payload["rows"]:
            for cell in row["row"]:
                if cell.get("Text") == "우천취소":
                    cell["Text"] = "연기"
                    replaced = True
                    break
            if replaced:
                break
        assert replaced
        games = games_from_kbo_payload(payload, 2026, "0,9,6")
        postponed = next(game for game in games if game.status == "postponed")
        assert postponed.awayScore is None and postponed.homeScore is None


def test_naver_game_code_uses_schedule_letters():
    assert naver_game_code("KIA") == "HT"
    assert naver_game_code("SSG") == "SK"
    assert naver_game_code("LG") == "LG"
    assert naver_game_code("드림") == ""


def test_merge_updates_result_and_keeps_identity():
    existing = _sample_game(
        id="2026-10-26-KIA-SS",
        date="2026-10-26",
        awayTeam="KIA",
        homeTeam="SS",
        awayScore=0,
        homeScore=0,
        status="scheduled",
        stadium=None,
        category="postseason",
        naverGameId="55551026HTSS02026",
        naverRecordUrl="https://m.sports.naver.com/game/55551026HTSS02026/record",
    )
    fetched = _sample_game(
        id="2026-10-26-KIA-SS",
        date="2026-10-26",
        awayTeam="KIA",
        homeTeam="SS",
        awayScore=5,
        homeScore=1,
        status="completed",
        stadium="대구",
        category="regular",  # must not overwrite the stored category
        naverGameId="55551026HTSS02026",
        naverRecordUrl="https://m.sports.naver.com/game/WRONG/record",
    )
    merged = merge_games([existing], [fetched], set())
    assert len(merged) == 1
    game = merged[0]
    assert game.id == "2026-10-26-KIA-SS"
    assert (game.awayScore, game.homeScore, game.status, game.stadium) == (5, 1, "completed", "대구")
    assert game.category == "postseason"
    assert game.naverGameId == "55551026HTSS02026"
    assert game.naverRecordUrl.endswith("/55551026HTSS02026/record")


def test_merge_matches_doubleheader_by_naver_id_and_keeps_failed_month():
    cancelled = _sample_game(
        id="2025-05-10-KIA-SSG",
        date="2025-05-10",
        awayTeam="KIA",
        homeTeam="SSG",
        awayScore=0,
        homeScore=0,
        status="cancelled",
        stadium=None,
        naverGameId="20250510HTSK12025",
    )
    played = _sample_game(
        id="2025-05-10-KIA-SSG-2",
        date="2025-05-10",
        awayTeam="KIA",
        homeTeam="SSG",
        awayScore=0,
        homeScore=0,
        status="scheduled",
        stadium=None,
        naverGameId="20250510HTSK02025",
    )
    # KBO only returned the played game, so its provisional id is the bare one.
    fetched = _sample_game(
        id="2025-05-10-KIA-SSG",
        date="2025-05-10",
        awayTeam="KIA",
        homeTeam="SSG",
        awayScore=5,
        homeScore=4,
        status="completed",
        stadium="문학",
        naverGameId="20250510HTSK02025",
    )
    october = _sample_game(
        id="2025-10-02-LG-OB",
        date="2025-10-02",
        awayTeam="LG",
        homeTeam="OB",
        awayScore=1,
        homeScore=2,
        status="completed",
        stadium=None,
        naverGameId="20251002LGOB02025",
    )
    merged = merge_games([cancelled, played, october], [fetched], {10})
    by_id = {game.id: game for game in merged}
    assert by_id["2025-05-10-KIA-SSG"].status == "cancelled"
    assert by_id["2025-05-10-KIA-SSG"].awayScore == 0
    assert by_id["2025-05-10-KIA-SSG-2"].status == "completed"
    assert (by_id["2025-05-10-KIA-SSG-2"].awayScore, by_id["2025-05-10-KIA-SSG-2"].homeScore) == (5, 4)
    assert by_id["2025-05-10-KIA-SSG-2"].stadium == "문학"
    assert by_id["2025-05-10-KIA-SSG-2"].naverGameId == "20250510HTSK02025"
    # October was not refetched, so the stored game stays byte-for-field identical.
    assert by_id["2025-10-02-LG-OB"] == october


def test_merge_appends_games_that_were_not_on_disk():
    existing = _sample_game()
    added = _sample_game(
        id="2026-11-03-SS-KT",
        date="2026-11-03",
        awayTeam="SS",
        homeTeam="KT",
        awayScore=None,
        homeScore=None,
        status="scheduled",
        stadium="수원",
        category="postseason",
        naverGameId="77771103SSKT02026",
        naverRecordUrl="https://m.sports.naver.com/game/77771103SSKT02026/record",
    )
    merged = merge_games([existing], [existing, added], set())
    assert [game.id for game in merged] == ["2026-04-01-LG-NC", "2026-11-03-SS-KT"]

