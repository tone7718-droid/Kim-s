# Kim-s
KBO Attendance Win Rate

KBO 직관 기록을 체크하고, 내가 응원하는 팀의 직관 승률을 자동으로 계산하는 모바일 중심 PWA입니다.

배포 URL: https://kim-s.vercel.app

Overview

KBO Attendance Win Rate는 KBO 팬이 직접 야구장에 방문한 경기만 체크해두면, 응원팀 기준으로 승·패·무·취소/연기 기록과 직관 승률을 자동으로 계산해주는 웹앱입니다.

친구들과 같은 URL을 사용할 수 있지만, 각자의 직관 기록은 각자 브라우저의 LocalStorage에 저장됩니다. 따라서 별도의 회원가입이나 서버 계정 없이 사용할 수 있습니다.

Why this project?

KBO 팬들은 “내가 직관 가면 우리 팀이 이기는가?”라는 이야기를 자주 합니다. 하지만 실제로 시즌별, 상대팀별, 홈/원정별, 월별 직관 성적을 직접 기록하고 계산하기는 번거롭습니다.

이 프로젝트는 그 문제를 해결하기 위해 만들었습니다.

목표는 단순합니다.

* KBO 경기 데이터를 자동으로 수집한다.
* 사용자는 자신이 직관한 경기만 체크한다.
* 응원팀 기준 직관 승률을 자동 계산한다.
* 모바일에서 빠르고 쉽게 사용할 수 있게 만든다.
* 팬들이 자신의 관람 기록을 데이터로 돌아볼 수 있게 한다.

Features

현재 지원 기능

* KBO 시즌별 경기 목록 확인
* 응원팀 선택
* 직관한 경기 체크
* 직관 경기만 필터링
* 정규시즌, 포스트시즌, 시범경기 포함 여부 선택
* 응원팀 기준 승·패·무·결과 없음 계산
* 직관 승률 자동 계산
* 상대팀별 기록
* 홈/원정별 기록
* 월별 기록
* 승패 비율 시각화
* 직관 기록 JSON 내보내기
* 직관 기록 JSON 불러오기
* 브라우저 LocalStorage 기반 개인 기록 저장
* 모바일 중심 UI
* PWA 설치 버튼 제공

How it works

이 프로젝트는 크게 두 부분으로 구성됩니다.

Kim-s/
├── scraper/          # KBO 경기 데이터 수집 도구
├── data/seasons/     # 수집된 시즌별 JSON 데이터
└── web/              # Next.js 기반 PWA

1. Data scraping

scraper/ 디렉터리는 KBO 경기 일정과 결과 데이터를 수집해 data/seasons/<year>.json 형태로 저장합니다.

현재 스크래퍼는 네이버 스포츠 JSON API를 기반으로 KBO 경기 데이터를 수집합니다.

출력 예시는 다음과 같습니다.

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

2. Web app

web/ 디렉터리는 Next.js 기반의 모바일 중심 웹앱입니다.

빌드 또는 개발 서버 실행 전에 data/seasons/*.json 파일을 web/public/data/seasons/로 복사합니다. 이후 웹앱은 정적 JSON 데이터를 불러와 사용자 화면에 경기 목록과 통계를 표시합니다.

사용자의 직관 기록은 서버에 저장하지 않고, 브라우저 LocalStorage에 저장합니다.

Tech Stack

* Next.js
* React
* TypeScript
* Tailwind CSS
* Python scraper
* LocalStorage
* PWA

Getting Started

1. Clone repository

git clone https://github.com/tone7718-droid/Kim-s.git
cd Kim-s

2. Install web dependencies

cd web
npm install

3. Run development server

npm run dev

브라우저에서 다음 주소로 접속합니다.

http://localhost:3000

Scripts

web/package.json 기준으로 다음 명령어를 사용할 수 있습니다.

npm run dev

개발 서버를 실행합니다.

npm run build

프로덕션 빌드를 생성합니다.

npm run start

빌드된 앱을 실행합니다.

npm run lint

Lint 검사를 실행합니다.

Scraper Usage

KBO 데이터를 직접 갱신하려면 scraper/ 디렉터리에서 실행합니다.

cd scraper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

한 달만 테스트하려면 다음 명령어를 사용합니다.

python scrape_kbo.py --year 2021 --month 4

한 시즌 전체를 수집하려면 다음 명령어를 사용합니다.

python scrape_kbo.py --year 2021

여러 시즌을 수집하려면 다음 명령어를 사용합니다.

python scrape_kbo.py --years 2021-2026

Data Policy

이 프로젝트는 사용자의 개인 직관 기록을 서버에 저장하지 않습니다.

직관 기록은 사용자의 브라우저 LocalStorage에만 저장됩니다. 따라서 다음 상황에서는 기록이 사라질 수 있습니다.

* 브라우저 데이터를 삭제한 경우
* 다른 기기에서 접속한 경우
* 다른 브라우저로 접속한 경우
* 휴대폰을 변경한 경우

기록을 보존하려면 앱의 설정 메뉴에서 JSON 파일로 내보내기한 뒤, 새 기기나 새 브라우저에서 다시 불러올 수 있습니다.

Roadmap

앞으로 개선하고 싶은 기능은 다음과 같습니다.

* 시즌 데이터 자동 갱신 안정화
* 경기 데이터 검증 로직 강화
* 더 보기 좋은 모바일 UI 개선
* 팀별 상세 통계 확대
* 구장별 직관 성적 분석
* 연도별 직관 성적 비교
* 데이터 수집 실패 시 알림 또는 로그 개선
* GitHub Issues 기반 버그 리포트 관리
* 기여 가이드 문서 추가
* 테스트 코드 보강

Open Source Goals

이 프로젝트는 개인용 기록 도구에서 출발했지만, KBO 팬들이 함께 사용할 수 있는 공개 도구로 발전시키는 것을 목표로 합니다.

특히 다음 방향을 중요하게 생각합니다.

* 팬들이 쉽게 사용할 수 있는 모바일 경험
* 투명하게 관리되는 공개 경기 데이터
* 유지보수 가능한 코드 구조
* 누구나 개선 제안을 남길 수 있는 오픈소스 프로젝트
* 한국 야구 팬 문화에 맞는 실용적인 데이터 도구

Contributing

버그 제보, 기능 제안, 문서 개선, 데이터 오류 제보는 모두 환영합니다.

기여 방법은 다음과 같습니다.

1. Issue를 생성해 문제나 제안을 남깁니다.
2. 필요한 경우 Fork 후 Pull Request를 보냅니다.
3. 데이터 오류가 있다면 날짜, 팀, 경기 정보를 함께 적어주세요.

아직 프로젝트 초기 단계이므로 작은 제안도 큰 도움이 됩니다.

License

라이선스는 아직 확정되지 않았습니다.

오픈소스 프로젝트로 운영하려면 추후 MIT License 등 명확한 라이선스를 추가할 예정입니다.
