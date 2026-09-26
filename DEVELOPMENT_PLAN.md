# HelioScan — Development plan

**Status:** Planning only. Do not start a phase until it is explicitly authorized.  
**Do not implement future phases prematurely.**

Each phase is a checkpoint. After a phase, record completion in git only if the user requests a commit. If a phase fails, use the rollback/checkpoint notes; do not “fix forward” by pulling in later-phase features.

---

## Phase 0 — Environment and project foundation

**Objective:** Prove the development machine can run the intended toolchain. Capture Python, Node, Git, PostgreSQL, NVIDIA/CUDA, and Ollama *facts*. Produce verified (not guessed) dependency files only after those facts exist.

**Prerequisites:** Human authorization to begin Phase 0. Windows host with WSL2 intended (`ENVIRONMENT_SETUP.md`). Specification documents already in repo.

**Files expected:**

- Environment notes (e.g. `docs/environment-actual.md`) with command output summaries (no secrets)
- `.gitignore` (Python, Node, `.env`, checkpoints, data blobs)
- `.env.example` placeholders
- Possibly empty `backend/`, `frontend/`, `ml/` package markers
- `backend/requirements.txt` / `ml/requirements.txt` **only after** version verification

**Functionality:** None of the product pipeline. Tooling only.

**Tests required:** Verification commands from `ENVIRONMENT_SETUP.md` (manual checklist). No application tests yet.

**Definition of done:**

- Python, pip, Node, npm, Git recorded
- PostgreSQL availability recorded (installed or explicitly deferred)
- GPU/driver inspected; CUDA tensor test run **or** CPU-only path documented
- Ollama presence recorded (installed or deferred)
- PyTorch install command chosen from official guidance matching the machine
- Requirements files created from that evidence, not from guesswork

**Possible edge cases:** No NVIDIA GPU; WSL CUDA not wired; Node on Windows vs WSL path mismatch; PostgreSQL not installed; Ollama on Windows host vs WSL networking.

**Rollback/checkpoint:** Keep spec files. Delete any trial venv. Do not leave half-pinned requirements. Tag or branch `phase-0` if the user wants git history.

---

## Phase 1 — FastAPI foundation

**Objective:** A running FastAPI app with health check, settings skeleton, logging, and project package layout. No external APIs.

**Prerequisites:** Phase 0 complete; backend venv; requirements installed and importable.

**Files expected:** `backend/app/main.py` (or equivalent), settings module, health router, pytest for health, README snippet for uvicorn (**tested**).

**Functionality:** `GET /health` (name TBD when implemented—**design then document**; do not invent extra business endpoints). App starts with Uvicorn.

**Tests required:** Health returns documented status; app factory loads without DB if DB is optional at this phase.

**Definition of done:** Tests, lint, type check, `uvicorn` starts and health is hit (curl or TestClient).

**Possible edge cases:** Wrong working directory; missing `PYTHONPATH`; Windows vs WSL port bind.

**Rollback/checkpoint:** Revert backend app files; keep Phase 0 env notes.

---

## Phase 2 — Next.js foundation

**Objective:** Next.js + TypeScript + Tailwind app that can call the backend health endpoint and show an “under development” shell.

**Prerequisites:** Phase 1; Node/npm from Phase 0.

**Files expected:** `frontend/` Next app, Tailwind config, env for API base URL, documented `npm run dev`.

**Functionality:** Home/dashboard shell; displays backend health or a clear connection error. No map yet.

**Tests required:** Production build (`next build`) succeeds; basic page render test if a runner is chosen.

**Definition of done:** Dev server starts; UI shows honest status; lint/tsc pass.

**Possible edge cases:** CORS; API URL `localhost` vs `127.0.0.1`; App Router vs Pages confusion.

**Rollback/checkpoint:** Remove `frontend/` scaffold; backend unchanged.

---

## Phase 3 — Address search / geocoding

**Objective:** User submits an address; backend returns validated coordinates using a **verified** geocoding provider.

**Prerequisites:** Phase 1–2. Written API verification memo (docs URL, auth, limits, ToS).

**Files expected:** Geocoding service module, Pydantic models, FastAPI route(s), frontend search UI, mocked tests, `.env.example` keys if required.

**Functionality:** Search → list or single result → lat/lon. Handle zero and multiple matches.

**Tests required:** Mocked HTTP success, 4xx, timeout, invalid JSON. No live calls in default tests.

**Definition of done:** Documented provider; timeouts and validation in place; UI shows error if geocoding fails (no fake pin).

**Possible edge cases:** Ambiguous addresses; non-UTF8; rate limits; provider requiring attribution.

**Rollback/checkpoint:** Feature-flag or remove geocoding routes; UI search disabled.

---

## Phase 4 — Interactive map

**Objective:** Map centered on geocoded coordinates; user can confirm location / viewport.

**Prerequisites:** Phase 3. Map library chosen after license + Next.js compatibility check.

**Files expected:** Map component, tile attribution, types for lat/lon/bbox.

**Functionality:** Marker and pan/zoom. Persist selected point/bbox to backend if API exists this phase (keep minimal).

**Tests required:** Component test or e2e smoke if available; do not fail CI on missing map tiles if mocked.

**Definition of done:** Map renders for a successful geocode; missing coordinates show empty state.

**Possible edge cases:** SSR/window; tile ToS; invalid lat/lon; dark CSS vs map controls.

**Rollback/checkpoint:** Hide map route; keep geocoding JSON API.

---

## Phase 5 — Esri / ArcGIS imagery

**Objective:** Fetch aerial/satellite imagery for the selected extent using a **verified** Esri/ArcGIS (or documented fallback) API.

**Prerequisites:** Phase 4. Written verification: product, auth, credits, cache/PDF rules.

**Files expected:** Imagery service, storage path, metadata (CRS, size, GSD if provided), attribution in UI.

**Functionality:** Request image for bbox; show on map or side panel; persist file + metadata.

**Tests required:** Mocked export/tile responses; 401/429/timeout; invalid image bytes rejected.

**Definition of done:** Real client matches official docs; failures visible; no redistributed tiles unless license allows.

**Possible edge cases:** Max image size; geographic vs Web Mercator; API credits exhaustion; WSL file paths.

**Rollback/checkpoint:** Disable imagery fetch; map-only mode.

---

## Phase 6 — Rooftop segmentation dataset

**Objective:** Define dataset layout, license, split, and loading code. Obtain or reject datasets **only** after license review. No claim of a trained production model.

**Prerequisites:** Phase 0 ML stack. Dataset decision recorded.

**Files expected:** `ml/data/` (gitignored binaries), dataset README with **actual** source URLs from official pages, `Dataset` class, split script.

**Functionality:** Load images/masks; visualize a sample (script).

**Tests required:** Loader tests with **tiny synthetic fixtures** in-repo (not the full dataset).

**Definition of done:** License documented; loader works on fixtures; full data optional on disk.

**Possible edge cases:** Mask format (0/1 vs 0/255); CRS mismatch; insufficient labeled roofs.

**Rollback/checkpoint:** Keep fixtures; delete large downloads.

---

## Phase 7 — U-Net training pipeline

**Objective:** Train a U-Net with logged metrics; save checkpoints; GPU/CPU device selection per `AGENT_RULES.md`.

**Prerequisites:** Phase 6; PyTorch CUDA test already recorded.

**Files expected:** Model definition, train/eval scripts, config (YAML/JSON), checkpoint directory gitignored.

**Functionality:** One training run on fixtures (smoke) and, if data exists, a real run. Evaluate IoU/Dice or documented metrics.

**Tests required:** Forward pass shape tests; smoke train 1–2 steps on CPU; device helper tests with mocked cuda.

**Definition of done:** Training script exits 0 on smoke; metrics logged; no silent CUDA fallback without log.

**Possible edge cases:** OOM; mixed precision; empty batch; non-reproducible seeds.

**Rollback/checkpoint:** Keep model code; discard bad checkpoints.

---

## Phase 8 — Rooftop area estimation

**Objective:** Convert mask + geospatial scale to roof m² and usable m² with documented factors.

**Prerequisites:** Segmentation inference callable (even if weights are weak). Imagery metadata with scale **or** explicit failure if scale unknown.

**Files expected:** Area service, assumption constants documented, FastAPI exposure if in-product.

**Functionality:** Mask → areas; overlay optional on map.

**Tests required:** Synthetic mask + known m/pixel → exact area; missing scale errors; usable area ≤ roof area.

**Definition of done:** No area without scale/assumptions shown; tests green.

**Possible edge cases:** Non-square pixels; pitch vs planimetric area; multi-building scenes.

**Rollback/checkpoint:** Return mask only; hide area cards.

---

## Phase 9 — NASA POWER integration

**Objective:** Client for NASA POWER point data; validated irradiance series.

**Prerequisites:** Official POWER docs verified and memo’d (paths, units, citation).

**Files expected:** Solar data service, Pydantic models matching **real** schema, cache optional.

**Functionality:** lat/lon → irradiance (and documented extra parameters only if in official API).

**Tests required:** Mocked JSON fixtures copied from documented examples **after** verification (or recorded live sample stored as fixture with date). Timeout/5xx.

**Definition of done:** Units documented; citation in UI/PDF later; no invented endpoints.

**Possible edge cases:** Ocean/invalid points; missing parameters; timezone vs climatology vs time series.

**Rollback/checkpoint:** Disable solar fetch; pipeline stops before generation.

---

## Phase 10 — Solar generation engine

**Objective:** Deterministic kWh from usable area + irradiance + explicit system parameters.

**Prerequisites:** Phase 8–9 (or fixtures for both). Formula documented in `docs/`.

**Files expected:** Pure Python engine, parameter schema, tests with golden values.

**Functionality:** Monthly and/or annual generation. No LLM.

**Tests required:** Hand-calculated fixtures; zero area → zero kWh; unit conversions.

**Definition of done:** Formula and assumptions visible to API consumers; tests match.

**Possible edge cases:** Extreme latitudes; PR > 1 rejected; packing density > 1 rejected.

**Rollback/checkpoint:** Keep NASA data display; omit kWh.

---

## Phase 11 — Financial analysis engine

**Objective:** Deterministic cost, savings, payback, ROI-style metrics from generation + user/config rates.

**Prerequisites:** Phase 10. Financial model documented (simple payback vs NPV—**choose and write down**).

**Files expected:** Finance module, parameter schema, tests.

**Functionality:** Table of metrics; sensitivity only if specified (keep simple first).

**Tests required:** Golden cash-flow cases; zero tariff; negative/NaN rejected.

**Definition of done:** LLM still unused; all rates sourced from input/config.

**Possible edge cases:** Incentive > capex; inflation; currency; missing useful life.

**Rollback/checkpoint:** Show kWh only; hide money.

---

## Phase 12 — PostgreSQL persistence

**Objective:** Store analyses, artifacts paths, statuses. SQLAlchemy models and migrations (tool chosen in this phase: Alembic recommended).

**Prerequisites:** PostgreSQL from Phase 0; Phases 1+.

**Files expected:** Models, migration, repository layer, connection settings.

**Functionality:** Create/read analysis job; persist JSON blobs of validated results.

**Tests required:** Test DB or transactional tests; connection failure handling.

**Definition of done:** App starts against configured DB; migrate command documented and tested.

**Possible edge cases:** WSL localhost vs Windows PostgreSQL; timezone; large images in DB (do not store blobs in Postgres without decision).

**Rollback/checkpoint:** Filesystem-only persistence; disable DB settings.

---

## Phase 13 — Ollama / Llama proposal generation

**Objective:** Narrative from validated metrics snapshot; Pydantic-validated output.

**Prerequisites:** Ollama installed and model pulled (Phase 0 or this phase). Metrics engines exist.

**Files expected:** LLM service, prompt templates, schemas, mocked Ollama tests.

**Functionality:** Proposal text on dashboard; failure state if Ollama down.

**Tests required:** Mock HTTP; invalid JSON; schema extra-numbers policy if implemented.

**Definition of done:** Model name documented; no math from LLM; timeouts in place.

**Possible edge cases:** Slow generation; context overflow; model hallucinating kWh.

**Rollback/checkpoint:** Skip proposal; PDF without narrative.

---

## Phase 14 — PDF report generation

**Objective:** PDF from stored analysis; numbers match dashboard.

**Prerequisites:** Phase 11–13 as needed; PDF library chosen and native deps verified.

**Files expected:** Report builder, template, download endpoint, tests with fixture analysis.

**Functionality:** Generate and download PDF; include disclaimer and sources.

**Tests required:** PDF header/signature; required sections present (text extract or structural asserts).

**Definition of done:** Imagery included only if license allows; generation does not recompute finance.

**Possible edge cases:** Missing mask image; Unicode address; WeasyPrint system libs.

**Rollback/checkpoint:** Dashboard-only export (JSON).

---

## Phase 15 — Full end-to-end integration

**Objective:** One orchestrated job: address → … → PDF, with job status.

**Prerequisites:** Phases 3–14 modules exist or are explicitly stubbed with **error states**, not fake success.

**Files expected:** Orchestrator, frontend wizard, status polling or wait UX.

**Functionality:** Complete demo path on a real address **if** keys and services available; otherwise documented dry-run with mocks.

**Tests required:** Orchestrator with all services faked; one optional live e2e marked skippable.

**Definition of done:** Dashboard and PDF share the same record id; partial failure is visible.

**Possible edge cases:** Mid-pipeline crash; duplicate submissions; stale jobs.

**Rollback/checkpoint:** Run steps manually via individual endpoints.

---

## Phase 16 — Testing and edge-case hardening

**Objective:** Broaden tests, timeouts, validation, and UX empty/error states. No new product features unless required to fix gaps.

**Prerequisites:** Phase 15.

**Files expected:** Additional tests, maybe contract tests frontend↔OpenAPI.

**Functionality:** Hardening only.

**Tests required:** Edge cases listed in prior phases; rate-limit mock; GPU/CPU; LLM invalid output.

**Definition of done:** CI-equivalent commands documented and passing locally; lint/typecheck clean.

**Possible edge cases:** Flaky live tests (must remain skippable).

**Rollback/checkpoint:** Revert hardening that breaks the demo; keep tests.

---

## Phase 17 — Dockerization

**Objective:** `docker compose` for backend, frontend, PostgreSQL; optional Ollama/GPU notes.

**Prerequisites:** App runs on host. Docker available on Windows/WSL—verify, do not assume.

**Files expected:** `Dockerfile`s, `compose.yml`, `.dockerignore`, planned commands in README **after** a successful compose test.

**Functionality:** `build` / `up` / `down` work on the documented host.

**Tests required:** Containers become healthy; health endpoint from published port.

**Definition of done:** Commands run successfully and are unmarked as merely planned.

**Possible edge cases:** GPU passthrough; file mounts; Ollama on host vs container; Windows line endings.

**Rollback/checkpoint:** Keep host venv workflow as primary.

---

## Phase 18 — Deployment / documentation

**Objective:** Operator docs: env vars, ports, model download, GPU, backups, limitations, citations.

**Prerequisites:** Phase 17 or a conscious “host-only deploy” decision.

**Files expected:** Updated README, `docs/` runbooks, security notes (secrets, ToS).

**Functionality:** Another person can follow docs without chat history. Still **Under Development** unless a release is explicitly cut.

**Tests required:** Doc commands match reality (re-run critical path).

**Definition of done:** Setup, run, test, ML, Ollama, Docker sections are accurate; known gaps listed.

**Possible edge cases:** Docs drift; unverified cloud deploy (do not invent AWS/Azure steps).

**Rollback/checkpoint:** README honesty first; remove untested deploy targets.

---

## Phase dependency graph (summary)

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
                ↘               ↙
                  9 → 10 → 11
                         ↘
            12 (can start after 1; needed before 15 persistence)
            13 after 11 (+ Ollama)
            14 after 11 (narrative optional)
            15 → 16 → 17 → 18
```

PostgreSQL (12) may be pulled earlier if needed for job tracking, but **tables for analyses should wait until there is something real to persist**.

---

## Global rule

If blocked on an external API or GPU fact, **stop the phase** and record the blocker. Do not skip ahead to a later phase that depends on the missing fact.

---

*End of development plan.*
