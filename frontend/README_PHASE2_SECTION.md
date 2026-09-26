
---

## Phase 2 — Next.js foundation (Under Development)

Next.js (App Router) + TypeScript + Tailwind CSS skeleton. It only proves the
frontend ↔ backend connection; there are no maps, charts, auth, or business features yet.

### Setup and run (from `frontend/`)

```bash
npm install
cp .env.example .env.local     # then edit if the backend is not at http://127.0.0.1:8000
npm run dev                    # http://localhost:3000
```

Start the FastAPI backend separately (see `backend/README.md`):

```bash
cd ../backend && source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The home page shows **Loading**, **Connected** (backend `GET /health` returned `{"status":"ok"}`),
or **Connection Error**.

### Checks

```bash
npm run lint
npx tsc --noEmit
npm run build
```

### Configuration

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the FastAPI backend, e.g. `http://127.0.0.1:8000` |

`NEXT_PUBLIC_*` values are inlined at build time; restart `npm run dev` (or rebuild) after changing it.

### Why the health check goes through `/api/backend-health`

The backend sends no CORS headers, so a browser on `localhost:3000` cannot read a direct
response from `127.0.0.1:8000`. The page therefore calls a same-origin Next.js route handler
(`app/api/backend-health/route.ts`), which performs the `GET /health` request server-side
(5 s timeout, response validated). If the backend later adds CORS, this can be revisited.

### Layout

```
app/            layout.tsx, page.tsx, api/backend-health/route.ts
components/     BackendStatus.tsx (client component: loading / connected / error)
lib/            api.ts (reads the env var), health.ts (types + validation)
```
