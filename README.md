# HelioScan

**Status: Under Development**

HelioScan is an AI-powered rooftop solar feasibility and energy-yield intelligence platform. This repository currently contains **architecture and specification only**. Features listed below are **planned**, not implemented. Do not assume APIs, models, or Docker workflows work until their development phase is complete and tested.

---

## What it will do

A user searches for an address. The system geocodes it, shows an interactive map, retrieves aerial/satellite imagery, segments the rooftop with a PyTorch U-Net, estimates roof and usable area, pulls solar resource data from NASA POWER, computes **deterministic** energy, financial, and CO₂ figures in Python, asks a **local** Llama model (Ollama) to write a professional explanation of those validated numbers, and presents results in a Next.js dashboard with a PDF feasibility report.

The language model is **not** allowed to invent kWh, money, or CO₂ results.

---

## Planned features

- Address search and geocoding
- Interactive map
- Esri/ArcGIS (or verified equivalent) imagery
- Rooftop segmentation (U-Net)
- Roof / usable area estimation
- NASA POWER solar data
- PV generation engine
- Financial analysis engine
- CO₂ reduction estimate
- Ollama/Llama proposal text
- Next.js dashboard
- PDF feasibility report
- PostgreSQL persistence
- Automated tests
- Docker Compose packaging
- GPU-accelerated training/inference when NVIDIA CUDA is **verified** available; CPU fallback otherwise

---

## Architecture overview

Modular FastAPI backend (service modules: geocoding, imagery, segmentation, area, solar data, solar calc, finance, LLM, PDF) plus a Next.js frontend. ML training lives under `ml/`. Data artifacts under `data/`. See `PROJECT_SPEC.md` for diagrams and data flow.

```
Address → coordinates → map → imagery → segmentation → mask
  → area → NASA POWER → PV kWh → finance → CO₂ → Llama text → PDF
```

---

## Technology stack (planned)

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Leaflet (or equivalent), Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, httpx, Uvicorn |
| ML | PyTorch, U-Net, torchvision, OpenCV/Pillow, augmentation library (candidate: Albumentations) |
| External | Geocoding provider (TBD), Esri/ArcGIS imagery, NASA POWER, Ollama |
| Reports | Python PDF library (TBD in Phase 14) |

Package **versions are not pinned yet**. See `REQUIREMENTS_PLAN.md`.

---

## Development status

| Area | Status |
| --- | --- |
| Specification and agent rules | Present |
| FastAPI / Next.js application | Not started |
| ML training / inference | Not started |
| External API clients | Not started |
| Database | Not started |
| Docker | Not started |
| `requirements.txt` | Intentionally absent until Phase 0 verifies the machine |

Current phase: **pre–Phase 0**. Do not start Phase 0 unless explicitly requested.

---

## Planned setup instructions

Full intended environment: Windows host, WSL2 Ubuntu, Python venv, Node.js, PostgreSQL, Git, NVIDIA drivers, CUDA/PyTorch compatibility check, Ollama. Details: `ENVIRONMENT_SETUP.md`.

**Do not install from this README yet.** When Phase 0 runs, verified steps will replace these placeholders.

---

## How the project will eventually be run

All commands below are **planned** until implemented and tested.

### Backend (planned)

1. Create and activate a virtual environment (see `ENVIRONMENT_SETUP.md`).
2. Install from `backend/requirements.txt` (file created after version verification).
3. Copy `.env.example` to `.env` and configure verified secrets.
4. Start API, in the style of:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

   The exact module path will match the Phase 1 layout.

5. Run tests, in the style of:

   ```bash
   python -m pytest
   ```

### Frontend (planned)

```bash
cd frontend
npm install
npm run dev
npm run build
```

### ML (planned)

1. Verify GPU/CPU with the PyTorch checks in `ENVIRONMENT_SETUP.md`.
2. Train, evaluate, and infer via scripts added in Phases 7–8 (they do not exist yet).

### Ollama (planned)

1. Install per official Ollama documentation for the chosen OS.
2. Pull the **selected** model (name decided in Phase 13).
3. Verify `ollama list` and HTTP access from the backend environment.
4. Run the LLM **through HelioScan’s service**, not as a source of numeric truth.

### Docker (planned, Phase 17)

```bash
docker compose build
docker compose up
docker compose down
```

---

## Testing strategy (planned)

- Unit tests per service, including failure paths
- Mocked tests for every external HTTP API
- Optional skippable live integration tests
- Lint and type checks before a phase is called complete
- Process start verification (Uvicorn, Next.js, later Compose)

Rules: `AGENT_RULES.md`.

---

## Project structure

```
HelioScan/
├── AGENT_RULES.md
├── DEVELOPMENT_PLAN.md
├── ENVIRONMENT_SETUP.md
├── PROJECT_SPEC.md
├── REQUIREMENTS_PLAN.md
├── README.md
├── backend/          # FastAPI (not implemented)
├── frontend/         # Next.js (not implemented)
├── ml/               # PyTorch pipeline (not implemented)
├── data/             # datasets and artifacts (empty; gitignore large files later)
├── tests/            # cross-cutting tests (not implemented)
├── docs/             # verification memos, formulas, environment actuals
└── scripts/          # operator/dev scripts (not implemented)
```

---

## Documents

- `PROJECT_SPEC.md` — product and architecture
- `AGENT_RULES.md` — reliability, API, LLM, GPU, quality rules
- `DEVELOPMENT_PLAN.md` — Phases 0–18
- `REQUIREMENTS_PLAN.md` — dependency groups without guessed pins
- `ENVIRONMENT_SETUP.md` — intended machine and verification commands

---

## License

Not selected. Do not assume MIT or any other license until a decision is recorded.

---

*HelioScan is under development. Nothing in this README claims a working application.*
