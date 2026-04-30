# scraper

Statiz KBO schedule/result scraper. Outputs `data/seasons/<year>.json`.

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
      "id": "2021-04-03-OB-NC",
      "date": "2021-04-03",
      "awayTeam": "OB",
      "homeTeam": "NC",
      "awayScore": 5,
      "homeScore": 3,
      "status": "completed",
      "stadium": "창원"
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

## 셀렉터 조정

스탯티즈 마크업이 시즌마다 살짝 다를 수 있어요. 파싱 로직은 전부
`parse_month_html()` 과 `_parse_one_game()` 안에 있으니, 한 달치 HTML을 받아서
구조가 바뀌었으면 거기만 손보면 됩니다.

```bash
# 디버깅용: 원본 HTML 저장
python -c "from scrape_kbo import fetch_month; \
  open('debug.html','w').write(fetch_month(2021, 4))"
```
