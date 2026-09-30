# KBO 스크래핑 결과 요약

_생성 시각 (UTC): 2026-09-30T19:46:52+00:00_

사용자 선택: **정규시즌 + 포스트시즌만 합산** (시범경기는 별도 표시)

## 시즌별 요약 (정규+포스트시즌)

| 시즌 | 합산 경기 | 정상종료 | 무승부 | 취소 | 연기 | 미진행 | 결과 미상 | 네이버 ID | 구장 정보 |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | **867** | 682 | 50 | 135 | 0 | 0 | 0 | 867/867 | 0/867 |
| 2022 | **785** | 724 | 12 | 49 | 0 | 0 | 0 | 785/785 | 0/785 |
| 2023 | **827** | 722 | 12 | 93 | 0 | 0 | 0 | 827/827 | 0/827 |
| 2024 | **818** | 727 | 10 | 81 | 0 | 0 | 0 | 818/818 | 0/818 |
| 2025 | **822** | 714 | 22 | 86 | 0 | 0 | 0 | 822/822 | 0/822 |
| 2026 | **793** | 664 | 16 | 73 | 0 | 40 | 0 | 793/793 | 0/793 |

**합산 총 4912 경기** / 시범경기는 별도 348 경기 (제외됨)

✅ 데이터 검증 통과: 팀 코드, 상태값, 카테고리, 중복 ID, 점수 무결성, 미래 경기 상태, 시즌 경기 수 범위를 확인했습니다.
구장 정보가 비어 있으면 원본 일정 응답에서 확인되지 않은 것입니다. 홈팀의 통상 구장을 실제 경기장으로 추정해 채우지 않습니다.

## 카테고리 분포

| 시즌 | 정규 | 포스트 | 시범 | 미상 |
|---|---|---|---|---|
| 2021 | 856 | 11 | 35 | 0 |
| 2022 | 769 | 16 | 80 | 0 |
| 2023 | 813 | 14 | 70 | 0 |
| 2024 | 799 | 19 | 53 | 0 |
| 2025 | 804 | 18 | 50 | 0 |
| 2026 | 793 | 0 | 60 | 0 |

## 샘플 (각 시즌 정규시즌 첫 경기)

- 2021: `2021-04-03` HH 0:0 KT (cancelled, regular)
- 2022: `2022-04-02` HH 4:6 OB (completed, regular)
- 2023: `2023-04-01` HH 2:3 WO (completed, regular)
- 2024: `2024-03-23` HH 2:8 LG (completed, regular)
- 2025: `2025-03-22` HH 4:3 KT (completed, regular)
- 2026: `2026-03-28` KIA 6:7 SSG (completed, regular)

## API 응답 진단

**statusCode 분포:**
  - `RESULT`: 4676
  - `BEFORE`: 589

**statusInfo 분포:**
  - `9회말`: 2267
  - `9회초`: 2043
  - `경기취소`: 544
  - `10회말`: 162
  - `11회말`: 114
  - `12회말`: 56
  - `경기전`: 45
  - `7회말`: 7
  - `5회말`: 6
  - `8회초`: 6
  - `6회말`: 5
  - `7회초`: 4
  - `6회초`: 3
  - `8회말`: 1
  - `5회초`: 1
  - `10회초`: 1

**statusCode / statusInfo 조합 (상위 20):**
  - `RESULT / 9회말`: 2267
  - `RESULT / 9회초`: 2043
  - `BEFORE / 경기취소`: 544
  - `RESULT / 10회말`: 162
  - `RESULT / 11회말`: 114
  - `RESULT / 12회말`: 56
  - `BEFORE / 경기전`: 45
  - `RESULT / 7회말`: 7
  - `RESULT / 5회말`: 6
  - `RESULT / 8회초`: 6
  - `RESULT / 6회말`: 5
  - `RESULT / 7회초`: 4
  - `RESULT / 6회초`: 3
  - `RESULT / 8회말`: 1
  - `RESULT / 5회초`: 1
  - `RESULT / 10회초`: 1

**카테고리 후보 필드:** 응답에 매칭되는 필드 없음 → 연도별 개막일·포스트시즌 시작일(미등록 연도는 날짜 휴리스틱)로 분류됨

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
  "neutralGround": false,
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
  "neutralGround": false,
  "homeTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/KT.png",
  "awayTeamEmblemUrl": "https://sports-phinf.pstatic.net/team/kbo/default/HH.png",
  "widgetEnable": false
}
```
</details>
