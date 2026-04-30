# scraper

KBO schedule/result scraper using the Naver Sports JSON API. Outputs
`data/seasons/<year>.json`.

원래는 스탯티즈를 쓰려 했지만, 클라우드 IP에서 DNS가 풀리지 않아 자동화가
불가능해 네이버 스포츠 공개 API로 전환했습니다 (`api-gw.sports.naver.com`).
JSON이라 HTML 셀렉터 깨질 일도 없고 GitHub Actions에서 잘 동작합니다.

## 로컬 실행

```bash
cd scraper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 한 달만 빠르게 테스트
python scrape_kbo.py --year 2021 --month 4

# 한 시즌
python scrape_kbo.py --year 2021

# 여러 시즌
python scrape_kbo.py --years 2021-2026
```

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
