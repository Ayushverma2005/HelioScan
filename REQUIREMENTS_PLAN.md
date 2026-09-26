# HelioScan — Requirements plan

**Status:** Planning only. **Do not install packages. Do not pin versions in this document as if they were verified.**

A real `backend/requirements.txt` and, if needed, `ml/requirements.txt` will be generated **after** Phase 0 inspects Python, pip, NVIDIA driver, GPU, and official PyTorch compatibility. Until then, there is **no** authoritative lockfile.

Do not duplicate incompatible dependency versions across backend and ML files. If both files exist later, shared libraries (NumPy, Pydantic, httpx) must be aligned or clearly layered (e.g. ML extra on top of backend).

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
| PyTorch (`torch`) | U-Net train/infer; CUDA build **only after GPU verification** |
| torchvision | Transforms, datasets helpers |
| OpenCV (`opencv-python` or headless variant) | Image I/O, morphology on masks |
| Pillow | Image I/O |
| NumPy | Arrays |
| pandas | Metrics tables, NASA series alignment |
| scikit-learn | Train/val split helpers, simple metrics if used |
| Image augmentation | Planned candidate: **Albumentations**; confirm license, OpenCV dependency, and API in Phase 6–7 |

Optional later (do not add until needed): `segmentation-models-pytorch`, `timm`, `rasterio` / `affine` for geospatial pixel scale. Each requires a written justification and license check.

**CUDA:** The `torch` index URL (CPU vs `cuXXX`) is an **environment outcome**, not a guess in this file.

---

## 4. Frontend (Node)

Planned (exact versions via `package.json` when Phase 2 starts):

| Package | Planned role |
| --- | --- |
| Next.js | App |
| React | UI |
| TypeScript | Typing |
| Tailwind CSS | Styling |
| Leaflet (or MapLibre GL, if Leaflet is a poor Next.js fit) | Map |
| React bindings for the map library | Confirm official package for chosen map lib |
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

Frontend: ESLint, TypeScript `tsc`, and the Next.js test runner or Playwright/Cypress **when** UI tests are in scope (Phase 2 / 16). Not installed now.

---

## 8. Proposed file layout (later)

When versions are verified:

```
backend/requirements.txt          # API + DB + httpx + shared calc deps
backend/requirements-dev.txt      # pytest, lint, types (optional split)
ml/requirements.txt               # torch, torchvision, cv, augment — may `-r ../backend/requirements.txt` or list extras only
frontend/package.json             # npm lockfile committed when created
```

**Rule:** Do not put a CUDA-specific `torch` pin in `backend/requirements.txt` if developers without GPUs must install the API. Options to decide in Phase 0:

- A. CPU `torch` in backend for inference-light API; GPU extra file for training machines
- B. Document two install paths (CPU vs CUDA) in README with official PyTorch commands
- C. ML inference as a separate process with its own venv

Default recommendation: **B + optional `ml/requirements.txt`**, so FastAPI can run without a multi-GB CUDA wheel if inference is optional in early phases.

---

## 9. Explicitly out of scope for pinning today

- Exact FastAPI / Pydantic / SQLAlchemy versions
- Exact PyTorch / CUDA versions
- Exact Next.js major version
- PostgreSQL major version (document installed version in Phase 0)

---

## 10. Stop condition

This file is complete when groups and constraints are documented.  
**Do not** create a guessed `requirements.txt` from this list.

---

*End of requirements plan.*
