# scraper

KBO schedule/result scraper. Outputs `data/seasons/<year>.json`.

기본 소스는 KBO 공식 사이트 일정 페이지가 쓰는
`POST /ws/Schedule.asmx/GetScheduleList` 입니다. 응답은 JSON 안에 HTML
조각이 들어 있는 비공식 엔드포인트라 형식이 바뀔 수 있습니다.

네이버 스포츠 API(`api-gw.sports.naver.com`)는 GitHub Actions 러너에서
읽기 타임아웃이 나서, 예약 실행의 기본값은 `--source kbo` 입니다.
`--source naver` 또는 `--source kbo-naver`(KBO 실패 시 네이버)로 바꿀 수 있습니다.

## 로컬 실행

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 한 달만 빠르게 테스트
python scrape_kbo.py --year 2021 --month 4  # 진단 전용: 시즌 JSON을 덮어쓰지 않음

# 한 시즌 (기본 소스: KBO)
python scrape_kbo.py --year 2026

# 네이버만, 또는 KBO가 실패한 달에 네이버로 폴백
python scrape_kbo.py --year 2026 --source naver
python scrape_kbo.py --years 2021-2026 --source kbo-naver
```

## 자동 갱신과 연도 전환

`.github/workflows/scrape.yml`이 매일 00:17 KST에 올해 시즌만 다시 받습니다.
해가 바뀌어도 손댈 것은 없습니다.

- 새 시즌 파일(`data/seasons/<올해>.json`)이 생기기 전에는 지난 시즌도 함께
  갱신합니다. 이 커밋이 저장소 활동을 유지합니다. public 저장소는 60일간
  활동이 없으면 GitHub가 예약 실행을 끕니다.
- 1~2월에 새 시즌 경기가 0건인 것은 실패가 아닙니다. 3월 이후, 이미 파일이
  있는 시즌, 요청 자체가 실패한 경우에만 실행이 실패로 끝납니다.
- 검증(`validate_kbo_data.py`)은 진행 중인 시즌에 300경기 하한을 적용하지
  않습니다. 대신 "미확인" 경기가 20건을 넘으면 실패합니다. KBO 페이지 형식이
  바뀌어 종료 경기를 인식하지 못하는 상황을 잡기 위한 것입니다.

실행이 실패하면 Actions 탭에 빨갛게 표시되고, 데이터는 커밋되지 않습니다.

## 출력 데이터 형식

```json
{
  "year": 2021,
  "generatedAt": "2025-04-30T09:00:00+0900",
  "games": [
    {
      "id": "2021-04-03-LG-NC",
      "date": "2021-04-03",
      "awayTeam": "LG",
      "homeTeam": "NC",
      "awayScore": 5,
      "homeScore": 3,
      "status": "completed",
      "stadium": "창원NC파크"
    }
  ]
}
```

`status` 값:
- `completed` — 정상 종료
- `tied` — 무승부
- `cancelled` — 우천/노게임 취소
- `postponed` — 연기
- `scheduled` — 아직 안 한 경기

팀 코드는 `teams.py`의 canonical code를 따릅니다 (KIA, SS, LG, OB, KT, SSG,
LT, HH, NC, WO). 네이버에서 다른 코드(HT, SK 등)가 와도 alias로 매핑됩니다.

## 디버깅

응답이 비어 있거나 새 팀 코드가 들어오면 다음으로 원본 JSON을 확인:

```bash
python -c "from scrape_kbo import fetch_range; import json; \
  print(json.dumps(fetch_range('2021-04-03','2021-04-03'), ensure_ascii=False, indent=2))"
```
