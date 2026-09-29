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

**Files expected:** Map component, tile attribution, and lat/lon types. A bbox/viewport type is deferred until a consumer or suitable backend API exists.

**Functionality:** Marker and pan/zoom for user confirmation. No suitable persistence API currently exists, so selected point/bbox persistence is deferred; do not invent an endpoint.

**Tests required:** Component test or e2e smoke if available; do not fail CI on missing map tiles if mocked.

**Definition of done:** Map renders for a successful geocode; missing coordinates show empty state.

**Possible edge cases:** SSR/window; tile ToS; invalid lat/lon; dark CSS vs map controls.

**Rollback/checkpoint:** Hide map route; keep geocoding JSON API.

**Viewport note:** Phase 4 supports user pan/zoom and visual location confirmation. A typed bbox/viewport contract and persistence are deferred until a consumer or suitable backend API exists; do not invent an endpoint for this phase.

---

## Phase 5 — NAIP imagery acquisition and integration

**Decision:** HelioScan's current imagery scope is US-focused. Esri/ArcGIS was originally proposed, then rejected after coverage and usage/redistribution concerns; the project's former India/global imagery ambition is not current scope. The selected source is the USGS NAIP Plus ImageServer, which combines NAIP and high-resolution orthoimagery and varies by location. It is not a global source; do not assume coverage outside verified US extents or fall back to another provider.

**Objective:** Retrieve NAIP imagery for a selected geographic extent, validate it, persist it with metadata, and make it available to rooftop segmentation.

**Prerequisites:** Phase 4. The official USGS NAIP Plus ImageServer endpoint and ArcGIS exportImage request contract have been verified and implemented; current coverage for each AOI remains data-dependent. Record and review current USGS/The National Map and USDA/FSA usage, licensing/redistribution terms, and required acknowledgements before production redistribution. Do not infer legal rights from service metadata alone.

**Files expected:** `backend/app/imagery/` client, validated raster/metadata contract, local storage, source/attribution metadata, mocked tests, optional live checker, and Phase 5 source verification memo.

**Functionality:**

- Acquire imagery for a selected bbox/extent through the verified source and method.
- Validate the returned file: readable raster, supported format, dimensions, bands, CRS, extent/georeferencing, and any needed resolution/GSD metadata.
- Preserve source, acquisition time, CRS, dimensions, band information, extent, attribution/acknowledgement, and applicable license metadata.
- Define storage location and safe WSL path behavior; make validated imagery available to Phase 6.
- Enforce verified source limits or conservative request/image-size bounds, finite timeouts, visible failure states, and rejection of invalid/truncated image data. Do not invent source limits.
- Test mocked success and failure paths, including timeout, unavailable source, invalid image, unsupported CRS/bands, and over-limit payloads.

**Fixture boundary:** `data/test/naip/cedar_park_residential.tif` is an existing real local test image used for inference validation. It is a fixture only, not evidence that HelioScan's imagery acquisition integration exists or works. Verify its source, use, attribution, and redistribution rights before relying on or distributing it.

**Definition of done:** The actual HelioScan acquisition path retrieves imagery for a supported selected extent, validates it, persists it with metadata, and supplies it to Phase 6. A local TIFF fixture alone does not satisfy this phase. Coverage gaps and unsupported extents fail clearly; source terms and attribution are documented; mocked success/failure tests pass.

**Possible edge cases:** Coverage gaps; bbox ordering/axis conventions; CRS conversion; missing georeferencing; unusual dimensions/band counts; oversized or truncated files; timeouts; source changes; Windows/WSL path translation; attribution and redistribution limits.

**Rollback/checkpoint:** Disable remote imagery acquisition; retain local test fixtures; allow map-only/manual imagery mode.

**Implementation status:** The reusable NAIP client, Rasterio validation, local TIFF/JSON persistence, mocked tests, and optional live checker are implemented. Phase 5 is not declared complete until the documented usage/redistribution review and required phase verification gates are resolved.

---

## Phase 6 — Rooftop dataset and Model M integration

**Objective:** Establish the dataset/fixture boundary and integrate the current frozen Model M baseline for inference. Build the image-to-mask contract, including tiling, reconstruction, and post-processing, without requiring HelioScan to train a model first.

**Prerequisites:** Phase 0 ML stack; Phase 5 validated imagery contract; verify Model M source/checkpoint license and use terms before redistribution or deployment.

**Files expected:** Dataset/source/license notes; `ml/data/` layout with large data gitignored; fixture loader and visualization; Model M inference adapter/configuration; input/output contract; tiling and mask-reconstruction utilities; focused tests.

**Functionality:** Load validated imagery and permitted fixtures; run Model M inference; reconstruct tiled predictions into image coordinates; define mask/post-processing outputs and failure behavior. Keep `data/test/naip/cedar_park_residential.tif` identified as a local test fixture, not imagery integration. Record dataset provenance and avoid geographic/source leakage in any future evaluation split.

**Tests required:** Fixture/raster loading and validation; preprocessing and output-shape checks; tile boundaries/reconstruction; inference smoke test when the licensed checkpoint is available. No formal accuracy result without ground-truth labels.

**Definition of done:** The frozen baseline consumes Phase 5 imagery under a documented input contract and produces a correctly shaped reconstructed mask; failures are explicit; fixture provenance/license status and model/checkpoint terms are recorded. This phase does not require training.

**Possible edge cases:** INRIA-to-target domain shift; imagery scale/GSD and CRS; dimensions not divisible by tile size; overlap/seams; memory limits; unavailable or incompatible checkpoint; mask class interpretation.

**Rollback/checkpoint:** Keep the Model M baseline/configuration record; disable inference integration and retain validated imagery/fixtures if the checkpoint or license blocks use.

---

## Phase 7 — Segmentation evaluation and optional training/fine-tuning

**Objective:** Quantitatively evaluate segmentation where labeled ground truth exists, analyze errors, and provide optional training/fine-tuning paths. Model M remains the initial frozen baseline; U-Net is an alternative research/training path, not a prerequisite for the first working inference pipeline.

**Prerequisites:** Phase 6 inference contract; licensed labeled data for any formal metric; PyTorch/CUDA facts and device checks recorded per `AGENT_RULES.md`.

**Files expected:** Evaluation scripts and reports; geographic/source-aware split definitions; reproducible optional U-Net and/or Model M fine-tuning configuration; checkpoint/version metadata; GPU/CPU device selection.

**Functionality:** Compute IoU, Dice, precision, recall, or other documented metrics only where valid ground-truth labels exist; perform error analysis; optionally train/fine-tune or compare models. Preserve Model M's frozen baseline for comparison. Do not label visual plausibility or inference success as formal accuracy.

**Tests required:** Metric tests against synthetic masks; deterministic evaluation smoke tests; training smoke tests only for paths actually implemented; device helper tests with mocked CUDA where applicable.

**Definition of done:** Evaluation data and methodology are documented; metrics can be reproduced and are reported with dataset/split context; optional training is reproducible and does not silently fall back from the configured device. If no suitable ground truth exists, record the gap rather than inventing scores.

**Possible edge cases:** Label disagreement; leakage across neighboring tiles; class imbalance; geographic/domain shift; checkpoint provenance; nondeterminism; OOM; mixed precision; incomplete masks.

**Rollback/checkpoint:** Retain Model M as the frozen baseline; discard experimental checkpoints that do not improve validated outcomes; do not block Phase 8 on optional training if Phase 6 inference is usable.

---

## Phase 8 — Rooftop area estimation

**Objective:** Convert mask + geospatial scale to roof m² and usable m² with documented factors.

**Prerequisites:** Phase 6 segmentation inference callable. Phase 5 imagery metadata with scale **or** explicit failure if scale is unknown. Phase 7 training/evaluation is not a prerequisite.

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
0 → 1 → 2 → 3 → 4 → 5 → 6 → 8 → 9 → 10 → 11
                         └→ 7 (optional evaluation / training; does not gate 8)

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
