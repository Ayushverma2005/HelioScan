# HelioScan — Requirements plan

**Status:** Dependency-selection guidance. Current Python pins are in `backend/requirements.txt` and `ml/requirements.txt`; frontend pins are in `frontend/package.json` and `frontend/package-lock.json`. This document describes package roles and future selection constraints; it is not a substitute for those manifests.

Phase 0 environment and PyTorch compatibility findings are recorded in `docs/PHASE_00_ENV_AUDIT.md` and `docs/PHASE_00_PYTORCH_COMPATIBILITY.md`. Do not change installed dependencies or pins without the relevant phase authorization and compatibility review.

Do not duplicate incompatible dependency versions across backend and ML files. Shared libraries (NumPy, Pydantic, httpx) must remain aligned or clearly layered (e.g. an ML extra on top of backend dependencies).

---

## 1. Principles

- Choose packages from this plan unless a documented substitute is required (license, WSL incompatibility, abandoned project).
- Record **why** a library was chosen when it is selected.
- Separate runtime backend, ML, frontend, PDF, LLM, and development/test groups.
- Prefer well-maintained libraries with OSI-approved licenses; verify license at selection time.

---

## 2. Backend (API, persistence, HTTP)

Planned runtime (Python):

| Package | Planned role |
| --- | --- |
| FastAPI | HTTP API, OpenAPI |
| Uvicorn | ASGI server (`[standard]` extras TBD at install time) |
| Pydantic | Settings, request/response, LLM output validation (v2 expected; confirm at install) |
| SQLAlchemy | ORM / SQL (2.x expected; confirm) |
| PostgreSQL driver | Planned candidate: `psycopg` (v3) or `psycopg2`; choose after SQLAlchemy + Python version check |
| httpx | Async/sync HTTP client for geocoding, imagery, NASA POWER, Ollama |
| python-dotenv | Local `.env` loading (if not fully replaced by Pydantic settings) |

Configuration: Pydantic `BaseSettings` (or `pydantic-settings`) — confirm package name for the chosen Pydantic major version **from docs at install time**.

**Not in this group yet:** geocoding/imagery SDKs. Prefer `httpx` + official REST until an official SDK is justified.

---

## 3. ML

Planned (Python):

| Package | Planned role |
| --- | --- |
| PyTorch (`torch`) | Model M inference baseline; optional evaluation, U-Net training, or Model M fine-tuning in Phase 7. CUDA build **only after GPU verification** |
| torchvision | Transforms, datasets helpers |
| OpenCV (`opencv-python` or headless variant) | Image I/O, morphology on masks |
| Pillow | Image I/O |
| NumPy | Arrays |
| pandas | Metrics tables, NASA series alignment |
| scikit-learn | Train/val split helpers, simple metrics if used |
| Image augmentation | Planned candidate: **Albumentations**; confirm license, OpenCV dependency, and API in Phase 6–7 |

`rasterio` is pinned in `backend/requirements.txt` for Phase 5 GeoTIFF validation. Do not duplicate it in the ML requirements unless a later ML-specific raster operation requires that environment to install it independently. Other optional packages such as `segmentation-models-pytorch`, `timm`, or `affine` require a written justification and license check before addition.

**CUDA:** The `torch` index URL (CPU vs `cuXXX`) is an **environment outcome**, not a guess in this file.

---

## 4. Frontend (Node)

Selected early frontend stack; exact installed versions are recorded in `frontend/package.json` and `frontend/package-lock.json`:

| Package | Planned role |
| --- | --- |
| Next.js | App |
| React | UI |
| TypeScript | Typing |
| Tailwind CSS | Styling |
| Leaflet | Selected map engine; the Phase 4 Next.js production build was validated with Webpack |
| React Leaflet | Selected React bindings for Leaflet; package and core declare Hippocratic-2.1, so project license acceptance remains a release review item |
| Recharts | Charts |
| Axios **or** native `fetch` | HTTP to FastAPI; prefer one client and stick to it |

Do not add UI component kits unless a phase explicitly requires them.

---

## 5. PDF

Choose **one** Python library in Phase 14 after a rendering test on WSL:

| Candidate | Notes to verify |
| --- | --- |
| ReportLab | Programmatic PDF; no HTML |
| WeasyPrint | HTML/CSS → PDF; native deps on Linux |
| fpdf2 | Lightweight; limited CSS |

Until then: **no PDF package in any requirements file.**

---

## 6. LLM

| Approach | Notes |
| --- | --- |
| Ollama HTTP API via **httpx** | Preferred initially (one HTTP stack, easy to mock) |
| Official `ollama` Python package | Allowed if docs confirm it is maintained and matches the installed Ollama server |

Do not add cloud LLM SDKs (OpenAI, Anthropic, etc.) unless a later phase explicitly changes architecture. Local Llama remains the specified generator.

---

## 7. Development and test (Python)

| Package | Planned role |
| --- | --- |
| pytest | Tests |
| pytest-asyncio | Async FastAPI/httpx tests |
| httpx (test client) / FastAPI `TestClient` | API tests |
| ruff or flake8 + black | Lint/format — **pick one toolchain in Phase 0** |
| mypy or Pyright | Type check — **pick in Phase 0** |
| coverage (optional) | Coverage reports |

Frontend: ESLint and TypeScript `tsc` are in use. No component/e2e test framework is currently recorded; add one only when a phase requires it and the test scope justifies it.

---

## 8. Current dependency files and layout

The repository currently uses:

```
backend/requirements.txt          # API + DB + httpx + shared calc deps
backend/requirements-dev.txt      # pytest, lint, types (optional split)
ml/requirements.txt               # torch, torchvision, cv, augment — may `-r ../backend/requirements.txt` or list extras only
frontend/package.json             # frontend dependency manifest
frontend/package-lock.json        # npm lockfile
```

**Rule:** Keep CUDA-specific `torch` pins in the ML dependency group so developers who only need the API do not have to install the GPU stack. The current GPU environment and tested model configuration are recorded in the Phase 0 and Model Selection Journey reports. Revisit the split only through an authorized dependency phase.

This keeps API-only backend setup independent from GPU-enabled ML installation.

---

## 9. Version governance

Exact package pins live in the current dependency manifests, not this planning document. Do not infer installed versions from the role tables above. Changes require phase authorization and compatibility verification; PostgreSQL remains deferred until its phase.

---

## 10. Stop condition

This file records dependency roles and constraints. It is not an installation command or source of version pins. **Do not** create guessed dependency changes from this plan.

---

*End of requirements plan.*
