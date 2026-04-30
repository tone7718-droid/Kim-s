# web

KBO 직관 승률 계산 PWA. Next.js 14 (App Router) + Tailwind.

## 로컬 실행

```bash
cd web
npm install
npm run dev
# http://localhost:3000
```

`npm run dev` / `npm run build` 전에 자동으로 `scripts/prepare-data.mjs` 가
돌아 `../data/seasons/*.json` 을 `public/data/seasons/` 로 복사합니다.

## 배포 (Vercel)

1. https://vercel.com/new 에서 이 GitHub 레포 임포트
2. **Root Directory** = `web`
3. 그 외 설정은 자동(Next.js 감지)
4. Deploy 누르고 끝

배포된 URL을 모바일에서 열고 "홈 화면에 추가" → 앱처럼 사용.

## 데이터 흐름

```
GitHub Actions (매일)
  └─ scraper/scrape_kbo.py → data/seasons/<year>.json (커밋)
                                 │
                                 ▼
              Vercel 빌드 시 prepare-data.mjs 가
              web/public/data/seasons/ 로 복사
                                 │
                                 ▼
                  브라우저에서 fetch('/data/seasons/<year>.json')
```

직관 기록 자체는 사용자 브라우저의 LocalStorage에만 저장됩니다 (서버 X).
