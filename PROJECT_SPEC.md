# HelioScan — Project Specification

**Status:** Specification only. Application code is not implemented.  
**Audience:** Product, architecture, and development agents working on HelioScan.

This document is the product and system specification. Implementation must not begin until Phase 0 (environment and project foundation) is explicitly authorized.

---

## 1. Product overview

### 1.1 What HelioScan does

HelioScan is an AI-powered rooftop solar feasibility and energy-yield intelligence platform. A user supplies a street address. The system geocodes that address, displays it on an interactive map, fetches aerial or satellite imagery, segments the rooftop with a trained PyTorch U-Net, estimates usable roof area, retrieves solar irradiance from NASA POWER, computes deterministic energy yield and financial metrics, estimates CO₂ reduction, asks a local Llama model (via Ollama) to write a professional explanation of those validated numbers, and presents the result in a Next.js dashboard with a downloadable PDF feasibility report.

HelioScan is a **decision-support** tool. It produces pre-sales / pre-engineering feasibility estimates, not stamped construction drawings, structural analysis, or utility interconnection applications.

### 1.2 Target users

| Persona | Need |
| --- | --- |
| Homeowners | Understand whether their roof is a reasonable solar candidate and what ballpark generation, payback, and CO₂ impact look like. |
| Solar sales / site-assessment teams | Produce a consistent, address-based feasibility pack without a site visit as the first step. |
| Energy consultants / analysts | Compare yield and financial assumptions across properties using a repeatable pipeline. |
| Developers / operators of HelioScan | Run the stack locally (Windows host + WSL2), train or infer the U-Net, and generate reports. |

Primary demo user is a **homeowner or solar analyst** completing one address-to-PDF journey.

### 1.3 Problem being solved

Rooftop solar interest is high, but early answers are fragmented:

- Addresses are converted to coordinates and maps by hand.
- Roof area is guessed from satellite photos or delayed until a site survey.
- Irradiance, kWh estimates, cash-flow, and CO₂ figures live in disconnected spreadsheets.
- Narrative proposals are written from those spreadsheets, so numbers can drift from the source calculations.

HelioScan binds geolocation, imagery, computer vision, physics-style yield math, finance, and narrative into one audited pipeline, with **numbers owned by Python**, not by the LLM.

### 1.4 Complete user journey

1. User opens the HelioScan dashboard.
2. User searches for a street address (autocomplete when a geocoding provider supports it).
3. Backend geocodes the address to latitude/longitude and a normalized place record.
4. Frontend shows an interactive map centered on the coordinates.
5. User confirms the location (and later, optionally, a roof bounding box / polygon).
6. Backend requests aerial/satellite imagery for the selected extent (planned: Esri/ArcGIS World Imagery or equivalent, **pending license and API verification**).
7. Imagery is stored and passed to the segmentation service.
8. U-Net produces a rooftop mask (and later, optional obstruction / usable-area refinements).
9. Geometry + pixel scale produce estimated roof area (m²) and usable area (m²).
10. Backend queries NASA POWER for solar resource data at the coordinates.
11. Solar calculation engine converts usable area, assumed array parameters, and irradiance into annual (and monthly, if data supports it) energy generation.
12. Financial engine applies user- or config-provided tariffs, capex, incentives, and discount rate to produce cost, savings, payback, and simple ROI-style metrics.
13. CO₂ engine applies a documented emission-factor assumption to estimated generation.
14. Validated numeric payload is sent to Ollama/Llama, which returns **explanation/proposal text only**.
15. Dashboard displays map, overlay, metrics, charts, and narrative.
16. User downloads a PDF feasibility report assembled from the same validated payload.

### 1.5 Final expected demo

A local demo (not claimed as production-ready) in which an operator:

1. Starts PostgreSQL, FastAPI, Next.js, and Ollama (planned).
2. Enters a real, geocodable address.
3. Sees the map and imagery.
4. Sees a rooftop mask and area estimate (quality depends on trained model and imagery).
5. Sees NASA POWER–backed irradiance and deterministic kWh, finance, and CO₂ figures.
6. Reads an LLM-written proposal that quotes those figures.
7. Downloads a PDF that matches the on-screen numbers.

The demo must fail loudly if an external service, GPU, or model is unavailable—never with invented numbers presented as measured results.

---

## 2. System architecture

HelioScan is a **modular monolith** in the first implementation: one FastAPI process exposing HTTP APIs, with **internal service modules** that have clear interfaces and can be unit-tested in isolation. Process-level microservices are **not** required for the initial product. Docker Compose will later package backend, frontend, PostgreSQL, and optionally Ollama.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js frontend                         │
│     TypeScript · Tailwind CSS · Leaflet (or equivalent)          │
│                         Recharts                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / JSON (planned API contract)
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI application                         │
│              Pydantic schemas · SQLAlchemy · httpx               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │geocoding │ │ imagery  │ │segmentation  │ │ rooftop area  │  │
│  └──────────┘ └──────────┘ └──────────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │solar data│ │ solar    │ │  financial   │ │ LLM (Ollama)  │  │
│  │(NASA)    │ │ calc     │ │  calc        │ │               │  │
│  └──────────┘ └──────────┘ └──────────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐                                      │
│  │ CO₂      │ │ PDF      │                                      │
│  └──────────┘ └──────────┘                                      │
└───────┬──────────────┬──────────────────┬───────────────────────┘
        │              │                  │
        ▼              ▼                  ▼
  PostgreSQL     ML artifacts        External HTTP
                 (ml/ + data/)       Geocoding · Esri/ArcGIS
                                     NASA POWER · Ollama
```

### 2.1 Frontend

| Technology | Role |
| --- | --- |
| Next.js | App Router UI, dashboard pages, API client to FastAPI. |
| TypeScript | Typed UI and API DTOs matching backend Pydantic models (contract documented when APIs exist). |
| Tailwind CSS | Layout and visual system. |
| Leaflet or equivalent | Interactive map, markers, later roof overlay. Library choice is confirmed in Phase 4 after license and Next.js compatibility check. |
| Recharts | Charts for monthly irradiance/generation and financial series. |

Frontend **does not** compute energy, finance, or CO₂. It displays backend-validated results.

### 2.2 Backend

| Technology | Role |
| --- | --- |
| Python | Runtime for API, calculations, orchestration. |
| FastAPI | HTTP API, OpenAPI generation. |
| Pydantic | Request/response models, LLM output validation, config. |
| SQLAlchemy | Persistence mapping (Phase 12). |
| PostgreSQL | Authoritative store for analyses, imagery metadata, reports. |
| httpx | Outbound HTTP with timeouts. |
| Uvicorn | ASGI server. |

### 2.3 ML

| Technology | Role |
| --- | --- |
| PyTorch | U-Net training and inference. |
| torchvision | Transforms, optional pretrained backbones **only if license and API are verified**. |
| OpenCV / Pillow | Image I/O, resizing, mask post-processing. |
| Augmentation library | Planned candidate: Albumentations (verify license and API in Phase 6–7). |
| NumPy / pandas | Arrays and tabular metrics. |

Device policy: **GPU when verified available; CPU fallback for inference/development.** CUDA versions are not assumed; they are selected after driver/GPU inspection (see `AGENT_RULES.md` and `ENVIRONMENT_SETUP.md`).

### 2.4 External services

All providers below are **planned**. Endpoints, auth, quotas, and licenses **must be verified from official documentation before any client is written**. Do not treat this table as a live API reference.

| Service | Planned use | Verification required before implementation |
| --- | --- | --- |
| Geocoding provider | Address → lat/lon, display name, confidence. Candidates include ArcGIS Geocoding (if Esri stack is already used), OpenStreetMap Nominatim (usage policy constraints), or another commercial geocoder. **Not selected.** | Official docs, ToS, attribution, rate limits, API key rules. |
| Esri / ArcGIS imagery | Aerial/satellite tiles or export for the selected bounding box. | Product name, REST vs SDK, authentication, credits, caching/redistribution rules. |
| NASA POWER | Solar radiation and related meteorology at point location. | Current POWER API paths, parameters, units, citation requirements. |
| Ollama / Llama | Local generation of proposal narrative from a **fixed JSON payload of already-computed metrics**. | Installed model name, context limits, HTTP API schema. |

### 2.5 Reports

PDF generation runs on the backend from the same analysis record used by the dashboard. Planned library candidates (choose one after license and Windows/WSL rendering checks): **ReportLab**, **WeasyPrint**, or **fpdf2**. Do not lock a package until Phase 14.

The PDF must print:

- Address and coordinates
- Map/imagery figure (if legally cacheable)
- Roof area and usable area
- Irradiance and generation
- Financial table
- CO₂ estimate
- LLM narrative (clearly labeled as generated text)
- Assumptions, data sources, and timestamps

### 2.6 Data stores and artifacts

| Store | Contents |
| --- | --- |
| PostgreSQL | Users/sessions (if added), analysis jobs, geocode results, solar/finance JSON, report metadata. |
| Object/file store (local disk first) | Imagery, masks, PDF files. Paths in DB. |
| `data/` | Datasets, sample fixtures (never secrets). |
| `ml/` | Training code, configs, checkpoints (large binaries gitignored). |

---

## 3. Data flow

End-to-end pipeline (each arrow is a module boundary with typed inputs/outputs):

```
Address (user string)
  → Coordinates + normalized address (geocoding)
  → Map view (frontend Leaflet; backend may persist bbox)
  → Imagery raster + georeference metadata (imagery service)
  → Rooftop segmentation logits/mask (ML inference)
  → Roof mask (post-processed binary/instance mask)
  → Roof area m² (pixel scale × mask; rooftop-area service)
  → Usable area m² (setbacks, pitch/obstruction factors — documented assumptions)
  → Solar irradiance (NASA POWER; validated units)
  → PV generation kWh (solar calculation engine)
  → Financial metrics (financial calculation engine)
  → CO₂ reduction (emission factor × generation)
  → Llama proposal text (LLM service; Pydantic-validated)
  → PDF (report service)
```

### 3.1 Stage contracts (logical)

These are **logical schemas**, not implemented APIs. Field names may change when OpenAPI is designed in Phase 1. No client should be written against invented URLs.

| Stage | Input | Output (conceptual) | Source of truth |
| --- | --- | --- | --- |
| Geocoding | `query: str` | `lat, lon, label, provider, raw_ref` | Geocoder |
| Map | `lat, lon` | Viewport / optional bbox | User + frontend |
| Imagery | `bbox` or point+zoom, CRS | Image bytes, width/height, meters-per-pixel or affine, attribution | Imagery provider |
| Segmentation | Image tensor | Mask, confidence/metrics | U-Net |
| Roof area | Mask + scale | `roof_area_m2` | Geometry math |
| Usable area | Roof area + factors | `usable_area_m2` | Documented factors |
| Solar data | `lat, lon, dates` | Irradiance series + metadata | NASA POWER |
| PV generation | Usable area, irradiance, system params | `kwh` monthly/annual | Deterministic Python |
| Finance | Generation + tariff/capex params | Cost, savings, payback, ROI-style metrics | Deterministic Python |
| CO₂ | Generation + factor | `co2_kg` or `co2_t` | Deterministic Python |
| LLM | Metrics JSON + template | `headline, body, caveats` | Llama; **must not introduce new numbers** |
| PDF | Analysis record | PDF bytes/path | Report renderer |

If any upstream stage fails, downstream stages must not fabricate values. The analysis record stores error state.

---

## 4. Service boundaries

Each backend capability is a **module with a narrow interface**, injectable for tests. Prefer `backend/app/services/<name>/` (exact layout decided in Phase 1). Services must not import Next.js, and ML training code in `ml/` must not import FastAPI app objects (inference may share a thin `ml` package).

### 4.1 Geocoding

- **Responsibility:** Resolve address strings; return coordinates and provider metadata.
- **Must not:** Fetch imagery, run ML, or compute kWh.
- **Test independently:** Mock HTTP; reject empty queries; handle zero results and ambiguous results.

### 4.2 Imagery

- **Responsibility:** Fetch and persist georeferenced rooftop imagery; record attribution and license constraints.
- **Must not:** Segment pixels or estimate area.
- **Test independently:** Mock tile/export HTTP; validate image dimensions; handle 401/429/timeout.

### 4.3 Segmentation

- **Responsibility:** Load model, run inference, return mask + quality metrics; select CUDA or CPU.
- **Must not:** Call NASA, finance, or LLM.
- **Test independently:** Fixture image → fixture mask shape; device selection unit tests with mocked `torch.cuda`.

### 4.4 Rooftop area

- **Responsibility:** Convert mask + geospatial scale to area; apply usable-area policy.
- **Must not:** Train models or call external weather APIs.
- **Test independently:** Known mask + known GSD → known m²; invalid scale raises.

### 4.5 Solar data

- **Responsibility:** NASA POWER client; parse and validate units/time coverage.
- **Must not:** Convert irradiance into kWh (that is the solar calculation engine).
- **Test independently:** Mock POWER JSON; schema validation; timeout/5xx.

### 4.6 Solar calculations

- **Responsibility:** PV generation from usable area, irradiance, performance ratio, tilt/azimuth assumptions, module wattage or packing density—**all parameters explicit**.
- **Must not:** Call LLM or mutate finance.
- **Test independently:** Golden spreadsheet-style fixtures; unit conversion tests.

### 4.7 Financial calculations

- **Responsibility:** Capex, incentives, tariff, escalation, simple payback, NPV/ROI **as specified in Phase 11**. Deterministic.
- **Must not:** Invent market prices; all rates come from config or user input.
- **Test independently:** Fixed inputs → expected cash metrics; edge cases (zero tariff, zero capex).

### 4.8 LLM

- **Responsibility:** Turn a **read-only metrics snapshot** into prose; validate with Pydantic.
- **Must not:** Recalculate energy, money, or CO₂. Reject or flag output that contains numbers not present in the snapshot (policy defined in Phase 13).
- **Test independently:** Mock Ollama HTTP; invalid JSON rejected; timeout.

### 4.9 PDF generation

- **Responsibility:** Render analysis record to PDF.
- **Must not:** Recompute science/finance; it only formats stored results.
- **Test independently:** Fixture record → PDF magic bytes / page count; missing optional images.

### 4.10 CO₂ (sub-module of calculations)

May live beside solar/finance engines. Same independence rules: documented emission factor, tested with fixtures.

### 4.11 Orchestration

A thin **analysis orchestrator** (application service) sequences the pipeline, writes job state to PostgreSQL (Phase 12), and exposes one or a few FastAPI routes. Orchestrator tests use fakes for every downstream service.

---

## 5. Assumptions and non-goals (initial)

**Assumptions (to confirm before or during relevant phases):**

- Development host is Windows with WSL2 Ubuntu for Python/ML; Node may run in WSL or Windows—documented in `ENVIRONMENT_SETUP.md`.
- Single-user / local-demo auth is acceptable until a later phase (do not invent OAuth).
- Financial inputs (electricity price, system cost per kW, incentives) are configuration or form fields, not live utility APIs, unless a verified API is added later.
- Roof pitch, azimuth, shading, and structural capacity are **simplified assumptions**, labeled as such in UI and PDF.

**Non-goals for the specified product arc:**

- Utility bill OCR
- Real-time inverter monitoring
- Multi-tenant SaaS billing
- Mobile native apps
- Autonomous purchasing of solar equipment

---

## 6. Quality, security, and compliance notes

- No API keys in git. Use `.env` (gitignored) and `.env.example` with empty placeholders.
- External imagery and geocoding **attribution** must follow provider terms (verify before shipping tiles in PDFs).
- NASA POWER citation/acknowledgement per official guidance (verify in Phase 9).
- LLM output is not engineering advice; UI must include a feasibility disclaimer.

---

## 7. Related documents

| Document | Purpose |
| --- | --- |
| `AGENT_RULES.md` | Binding development rules |
| `DEVELOPMENT_PLAN.md` | Phased delivery |
| `REQUIREMENTS_PLAN.md` | Planned dependency groups (no pinned versions yet) |
| `ENVIRONMENT_SETUP.md` | Intended toolchain; verification commands **not yet executed** |
| `README.md` | Project entry point |

---

*End of specification. Do not treat planned APIs as implemented.*
