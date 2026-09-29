# HelioScan

**Status: Under Development**

HelioScan is a US-focused rooftop solar feasibility and energy-yield intelligence platform. This repository contains phased specifications and working early application slices, including backend health/geocoding and NAIP acquisition, frontend search, and an interactive map. Segmentation integration and downstream analysis are not complete. Treat each phase as planned until its definition of done is verified.

---

## What it will do

A user searches for a US address. The system geocodes it, shows an interactive map, and can acquire imagery from the USGS NAIP Plus ImageServer for a bounded WGS84 extent. The service combines NAIP and high-resolution orthoimagery; coverage and resolution vary by location, and the source is not global. Model M (STT + ResNet-50 + INRIA checkpoint) is the frozen segmentation baseline, but its application integration remains planned; engineering inference was validated separately, without a formal HelioScan accuracy benchmark. Later phases estimate roof and usable area, retrieve solar resource data from NASA POWER, calculate **deterministic** energy, financial, and CO₂ figures in Python, generate narrative with local Llama via Ollama, and produce a PDF feasibility report.

The language model is **not** allowed to invent kWh, money, or CO₂ results.

---

## Planned features

- Address search and geocoding
- Interactive map
- USGS NAIP Plus imagery acquisition for bounded US extents (Phase 5; terms/redistribution review remains open)
- Model M rooftop/building segmentation integration (Phase 6)
- Optional quantitative segmentation evaluation and training/fine-tuning (Phase 7)
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

Modular FastAPI backend (service modules planned for imagery, segmentation, area, solar data, solar calculation, finance, LLM, and PDF) plus a Next.js frontend. The early geocoding and map slices exist. Model M's inference integration and remote imagery acquisition are still planned. See `PROJECT_SPEC.md` for diagrams and data flow.

```
Address → coordinates → map → imagery → segmentation → mask
  → area → NASA POWER → PV kWh → finance → CO₂ → Llama text → PDF
```

---

## Technology stack (planned)

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Leaflet + React Leaflet, Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, httpx, Uvicorn |
| ML | PyTorch; Model M (STT + ResNet-50 + INRIA checkpoint) as the frozen baseline; optional U-Net/fine-tuning research |
| External | Nominatim geocoding; USGS NAIP Plus imagery; NASA POWER; Ollama |
| Reports | Python PDF library (TBD in Phase 14) |

Python dependency planning is described in `REQUIREMENTS_PLAN.md`; installed frontend versions are recorded in `frontend/package.json` and its lockfile.

---

## Development status

| Area | Status |
| --- | --- |
| Specification and agent rules | Present |
| FastAPI health and geocoding | Implemented; see backend tests and provider verification memo |
| Next.js search and interactive map | Implemented; production build uses Webpack |
| USGS NAIP Plus acquisition | Implemented client, raster validation, local persistence, and mocked tests; terms review remains open |
| Model M inference integration | Engineering validation complete; application integration planned in Phase 6 |
| Quantitative segmentation evaluation/training | Optional future work; Phase 7 |
| Database / Docker | Not implemented |
| Environment and ML compatibility notes | Recorded in `docs/`; see phase reports |

The project remains phase-driven. See `DEVELOPMENT_PLAN.md` for prerequisites, checkpoints, and rollback boundaries.

---

## Planned setup instructions

The intended environment is Windows with WSL2 Ubuntu, Python virtual environments, Node.js, Git, NVIDIA/CUDA where available, and Ollama. PostgreSQL remains deferred. Verified environment and PyTorch compatibility findings are recorded in `docs/PHASE_00_ENV_AUDIT.md` and `docs/PHASE_00_PYTORCH_COMPATIBILITY.md`; imagery-source and model/checkpoint terms still require phase-specific review where noted.

---

## How the project will eventually be run

Commands below are workflow examples; verify phase-specific setup and environment values before use.

### Backend (planned)

1. Create and activate a virtual environment (see `ENVIRONMENT_SETUP.md`).
2. Install from `backend/requirements.txt` in the backend environment.
3. Copy `.env.example` to `.env` and configure verified secrets.
4. Start API, in the style of:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

   Run from the backend directory.

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
2. Phase 6 will integrate Model M inference; Phase 7 covers optional evaluation and training/fine-tuning.

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
├── backend/          # FastAPI health, geocoding, and NAIP acquisition slices
├── frontend/         # Next.js search and interactive map slices
├── ml/               # Model M inference integration planned
├── data/             # Local NAIP test imagery and generated imagery artifacts
├── tests/            # Cross-cutting test notes
├── docs/             # Verification memos, model decision, and environment findings
└── scripts/          # operator/dev scripts (not implemented)
```

---

## Documents

- `PROJECT_SPEC.md` — product and architecture
- `AGENT_RULES.md` — reliability, API, LLM, GPU, quality rules
- `DEVELOPMENT_PLAN.md` — Phases 0–18
- `REQUIREMENTS_PLAN.md` — dependency groups without guessed pins
- `ENVIRONMENT_SETUP.md` — intended machine and verification commands
- `docs/MODEL_SELECTION_JOURNEY.md` — Model M selection and engineering validation
- `docs/PHASE_05_NAIP_VERIFICATION.md` — USGS NAIP Plus service and acquisition contract

---

## License

Not selected. Do not assume MIT or any other license until a decision is recorded.

---

*HelioScan is under development. Reported implementation status is limited to the slices and validations identified above.*
