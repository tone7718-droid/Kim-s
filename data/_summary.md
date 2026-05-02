# KBO 스크래핑 결과 요약

_생성 시각 (UTC): -_  

사용자 선택: **정규시즌 + 포스트시즌만 합산** (시범경기는 별도 표시)

## 시즌별 요약 (정규+포스트시즌)

| 시즌 | 합산 경기 | 정상종료 | 무승부 | 취소 | 연기 | 미진행 |
|---|---|---|---|---|---|---|
| 2021 | **824** | 646 | 47 | 131 | 0 | 0 |
| 2022 | **785** | 724 | 12 | 49 | 0 | 0 |
| 2023 | **815** | 710 | 12 | 93 | 0 | 0 |
| 2024 | **803** | 715 | 9 | 79 | 0 | 0 |
| 2025 | **808** | 702 | 20 | 86 | 0 | 0 |
| 2026 | **675** | 140 | 2 | 8 | 0 | 525 |

**합산 총 4710 경기** / 시범경기는 별도 348 경기 (제외됨)

## 카테고리 분포

| 시즌 | 정규 | 포스트 | 시범 | 미상 |
|---|---|---|---|---|
| 2021 | 776 | 48 | 35 | 0 |
| 2022 | 774 | 11 | 80 | 0 |
| 2023 | 802 | 13 | 70 | 0 |
| 2024 | 798 | 5 | 53 | 0 |
| 2025 | 801 | 7 | 50 | 0 |
| 2026 | 675 | 0 | 60 | 0 |

## 샘플 (각 시즌 정규시즌 첫 경기)

- 2021: `2021-04-03` HH 0:0 KT (cancelled, regular)
- 2022: `2022-04-02` HH 4:6 OB (completed, regular)
- 2023: `2023-04-01` HH 2:3 WO (completed, regular)
- 2024: `2024-03-23` HH 2:8 LG (completed, regular)
- 2025: `2025-03-22` HH 4:3 KT (completed, regular)
- 2026: `2026-03-28` KIA 6:7 SSG (completed, regular)

## API 응답 진단

**statusCode 분포:**
  - `RESULT`: 4137
  - `BEFORE`: 1009

**statusInfo 분포:**
  - `9회말`: 1998
  - `9회초`: 1809
  - `경기전`: 530
  - `경기취소`: 479
  - `10회말`: 148
  - `11회말`: 95
  - `12회말`: 56
  - `5회말`: 6
  - `8회초`: 6
  - `7회말`: 5
  - `7회초`: 4
  - `6회말`: 4
  - `6회초`: 3
  - `8회말`: 1
  - `5회초`: 1
  - `10회초`: 1

**statusCode / statusInfo 조합 (상위 20):**
  - `RESULT / 9회말`: 1998
  - `RESULT / 9회초`: 1809
  - `BEFORE / 경기전`: 530
  - `BEFORE / 경기취소`: 479
  - `RESULT / 10회말`: 148
  - `RESULT / 11회말`: 95
  - `RESULT / 12회말`: 56
  - `RESULT / 5회말`: 6
  - `RESULT / 8회초`: 6
  - `RESULT / 7회말`: 5
  - `RESULT / 7회초`: 4
  - `RESULT / 6회말`: 4
  - `RESULT / 6회초`: 3
  - `RESULT / 8회말`: 1
  - `RESULT / 5회초`: 1
  - `RESULT / 10회초`: 1

**카테고리 후보 필드:** 응답에 매칭되는 필드 없음 → 날짜 휴리스틱으로 분류됨

<details><summary>첫 RESULT 게임 raw JSON</summary>

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

<details><summary>첫 BEFORE 게임 raw JSON (취소/미진행 구분 단서)</summary>

```json
{
  "gameId": "20210403HHKT02021",
  "categoryId": "kbo",
  "gameDate": "2021-04-03",
  "gameDateTime": "2021-04-03T14:00:00",
  "homeTeamCode": "KT",
  "homeTeamName": "KT",
  "homeTeamScore": 0,
  "awayTeamCode": "HH",
  "awayTeamName": "한화",
  "awayTeamScore": 0,
  "winner": "DRAW",
  "statusCode": "BEFORE",
  "statusInfo": "경기취소",
  "cancel": true,
  "suspended": false,
  "reversedHomeAway": true,
  "homeTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/KT.png",
  "awayTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/HH.png",
  "widgetEnable": false
}
```
</details>
