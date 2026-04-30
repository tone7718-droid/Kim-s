# KBO 스크래핑 결과 요약

_생성 시각 (UTC): -_  

사용자 선택: **정규시즌 + 포스트시즌만 합산** (시범경기는 별도 표시)

## 시즌별 요약 (정규+포스트시즌)

| 시즌 | 합산 경기 | 정상종료 | 무승부 | 취소 | 연기 | 미진행 |
|---|---|---|---|---|---|---|
| 2021 | **844** | 663 | 50 | 0 | 0 | 131 |
| 2022 | **810** | 741 | 17 | 0 | 0 | 52 |
| 2023 | **835** | 728 | 14 | 0 | 0 | 93 |
| 2024 | **793** | 706 | 9 | 0 | 0 | 78 |
| 2025 | **798** | 692 | 20 | 0 | 0 | 86 |
| 2026 | **675** | 135 | 2 | 0 | 0 | 538 |

**합산 총 4755 경기** / 시범경기는 별도 303 경기 (제외됨)

## 카테고리 분포

| 시즌 | 정규 | 포스트 | 시범 | 미상 |
|---|---|---|---|---|
| 2021 | 796 | 48 | 15 | 0 |
| 2022 | 799 | 11 | 55 | 0 |
| 2023 | 822 | 13 | 50 | 0 |
| 2024 | 788 | 5 | 63 | 0 |
| 2025 | 791 | 7 | 60 | 0 |
| 2026 | 675 | 0 | 60 | 0 |

## 샘플 (각 시즌 정규시즌 첫 경기)

- 2021: `2021-03-25` HH 5:12 KT (completed, regular)
- 2022: `2022-03-25` HH 3:0 SSG (completed, regular)
- 2023: `2023-03-25` HH 5:1 LT (completed, regular)
- 2024: `2024-03-26` HH 6:0 SSG (completed, regular)
- 2025: `2025-03-25` HH 0:5 LG (completed, regular)
- 2026: `2026-03-28` KIA 6:7 SSG (completed, regular)

## API 응답 진단

**statusCode 분포:**
  - `RESULT`: 4132
  - `BEFORE`: 1014

**카테고리 후보 필드:** 응답에 매칭되는 필드 없음 → 날짜 휴리스틱으로 분류됨

<details><summary>첫 게임 raw JSON</summary>

```json
{
  "gameId": "20210321HTSS02021",
  "categoryId": "kbo",
  "gameDate": "2021-03-21",
  "gameDateTime": "2021-03-21T13:00:00",
  "homeTeamCode": "SS",
  "homeTeamName": "삼성",
  "homeTeamScore": 10,
  "awayTeamCode": "HT",
  "awayTeamName": "KIA",
  "awayTeamScore": 7,
  "winner": "HOME",
  "statusCode": "RESULT",
  "statusInfo": "9회초",
  "cancel": false,
  "suspended": false,
  "reversedHomeAway": true,
  "homeTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/SS.png",
  "awayTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/HT.png",
  "widgetEnable": false
}
```
</details>
