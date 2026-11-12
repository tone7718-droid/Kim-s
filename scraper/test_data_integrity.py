import datetime as dt
import json
from dataclasses import replace
from pathlib import Path

import pytest
import scrape_kbo as s
import validate_kbo_data as v

def game(**kwargs):
    values=dict(id="2099-11-11-SS-KT",date="2099-11-11",awayTeam="SS",homeTeam="KT",
                awayScore=None,homeScore=None,status="scheduled",stadium="수원",category="postseason",
                naverGameId="77771111SSKT02099",naverRecordUrl=None)
    values.update(kwargs)
    return s.Game(**values)

def test_removed_schedule_keeps_identity_but_is_not_advertised_as_confirmed():
    old=game()
    merged=s.merge_games([old],[],set())
    assert merged[0].id==old.id
    assert merged[0].status=="unconfirmed"

@pytest.mark.parametrize("away,home",[(0,0),(3,1)])
def test_scores_without_a_review_are_not_final(away,home):
    assert s._status_from_note(None,away,home,"")==("scheduled",None,None)
    assert s._status_from_note(None,away,home,"문자중계")==("scheduled",None,None)

def test_zero_zero_is_a_tie_only_after_a_review_is_available():
    assert s._status_from_note(None,0,0,"리뷰")==("tied",0,0)

def test_incomplete_response_does_not_erase_previously_confirmed_result():
    old=game(status="completed",awayScore=3,homeScore=1)
    merged=s.merge_games([old],[game()],set())
    assert (merged[0].status,merged[0].awayScore,merged[0].homeScore)==("completed",3,1)

def test_failed_month_does_not_change_existing_pending_game():
    old=game()
    assert s.merge_games([old],[],{11})==[old]

def test_clinched_korean_series_marks_remaining_games_unnecessary():
    completed=[game(id=f"2099-11-0{day}-SS-KT",date=f"2099-11-0{day}",
                    status="completed",awayScore=3,homeScore=1,
                    naverGameId=f"7777110{day}SSKT02099") for day in [3,4,6,7]]
    merged=s.merge_games(completed+[game()],completed+[game()],set())
    remaining=next(g for g in merged if g.date=="2099-11-11")
    assert remaining.status=="not_required"
    assert remaining.homeScore is None
    assert all(g.status=="completed" for g in merged if g.date<"2099-11-11")

def test_series_is_not_clinched_after_only_three_wins():
    played=[game(id=f"2099-11-0{day}-SS-KT",date=f"2099-11-0{day}",status="completed",awayScore=3,homeScore=1)
            for day in [3,4,6]]
    assert next(g for g in s.merge_games(played+[game()],played+[game()],set()) if g.date=="2099-11-11").status=="scheduled"

def test_partial_refresh_preserves_last_complete_timestamp(tmp_path,monkeypatch):
    monkeypatch.setattr(s,"DATA_DIR",tmp_path)
    path=tmp_path/"2099.json"
    path.write_text(json.dumps({"generatedAt":"2026-10-01T00:00:00+00:00"}))
    s.write_season(2099,[game()],[11])
    payload=json.loads(path.read_text())
    assert payload["generatedAt"]=="2026-10-01T00:00:00+00:00"
    assert payload["refresh"]["failedMonths"]==[11]
    s.write_season(2099,[game()],[])
    payload=json.loads(path.read_text())
    assert payload["generatedAt"]!="2026-10-01T00:00:00+00:00"
    assert payload["refresh"]["failedMonths"]==[]

def test_parser_keeps_kst_start_time():
    fixture=json.loads((Path(__file__).parent/"fixtures/kbo_schedule_sample.json").read_text())
    for sl in fixture["slices"]:
        if sl["year"]==2026 and sl["srIdList"]=="7":
            parsed=s.games_from_kbo_payload(sl["payload"],2026,"7")
            assert next(g for g in parsed if g.date=="2026-11-03").startTime=="18:30"
            assert all(g.startTime is not None for g in parsed)
            break
    else:
        pytest.fail("Missing Korean Series fixture")

def test_validator_rejects_expired_pending_game_but_allows_unconfirmed(tmp_path,monkeypatch):
    monkeypatch.setattr(v,"MIN_MAIN_GAMES_PER_SEASON",1)
    path=tmp_path/"2099.json"
    old=game(date="2099-01-01",id="2099-01-01-SS-KT")
    def save(g):
        path.write_text(json.dumps({"year":2099,"games":[g.__dict__]}))
    save(old)
    with pytest.raises(ValueError,match="expired scheduled"):
        v.validate_file(path,dt.date(2099,2,1))
    save(replace(old,status="unconfirmed"))
    v.validate_file(path,dt.date(2099,2,1))

def _season(tmp_path,games,year=2099):
    path=tmp_path/f"{year}.json"
    path.write_text(json.dumps({"year":year,"games":[g.__dict__ for g in games]}))
    return path

def test_validator_exempts_only_the_season_in_progress_from_the_minimum(tmp_path):
    path=_season(tmp_path,[game(category="preseason",status="cancelled")])
    v.validate_file(path,dt.date(2099,2,1))
    with pytest.raises(ValueError,match="partial scrape"):
        v.validate_file(path,dt.date(2100,2,1))

def test_validator_rejects_mass_unconfirmed_results(tmp_path):
    def games(count):
        return [game(id=f"2099-04-{day:02d}-SS-KT",date=f"2099-04-{day:02d}",status="unconfirmed")
                for day in range(1,count+1)]
    v.validate_file(_season(tmp_path,games(v.MAX_UNCONFIRMED_GAMES)),dt.date(2099,6,1))
    with pytest.raises(ValueError,match="unconfirmed"):
        v.validate_file(_season(tmp_path,games(v.MAX_UNCONFIRMED_GAMES+1)),dt.date(2099,6,1))
