# Debtrix Frontend (Next.js)

Responsive web app — works on desktop and mobile browsers via one
codebase, and installs as a home-screen PWA on mobile (no native app
needed, see `public/manifest.json`).

## Setup

```bash
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your backend
```

## Run

```bash
npm run dev
```

Open `http://localhost:3000`. You'll be redirected to `/login` →
"Continue with GitHub" → backend OAuth flow → `/dashboard`.

## Structure

```
src/
  app/
    login/            # GitHub sign-in
    auth/callback/     # receives JWT from backend redirect
    dashboard/          # main executive dashboard
  components/
    MetricCard.tsx       # health score / $ loss / hours wasted
    PriorityFixList.tsx  # top 3 ranked fixes
    RepoSelector.tsx     # pick repo + trigger scan (polls until done)
  lib/api.ts              # typed client for the FastAPI backend
```

## Design tokens

Ink-navy background, gold/amber accent (financial ledger feel),
monospace numerals for all figures — see `tailwind.config.js`.
