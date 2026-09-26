# HelioScan — Environment setup (planned)

**Status:** Documentation only. **Do not execute installation commands as part of the specification task.**  
When Phase 0 is authorized, run the **verification** commands on the actual machine and record results in `docs/environment-actual.md` (to be created then).

Intended development setup:

| Layer | Intent |
| --- | --- |
| Host OS | Windows 10/11 |
| Linux | WSL2, Ubuntu |
| Python | CPython in a **virtual environment** (inside WSL recommended for ML) |
| Node.js | LTS, via nvm or official installer (document which in Phase 0) |
| npm | Comes with Node |
| PostgreSQL | Local server (WSL package or Windows install—pick one and document host/port) |
| Git | Windows and/or WSL; do not mix line-ending surprises without `.gitattributes` later |
| NVIDIA | Windows NVIDIA driver; WSL GPU access **if** NVIDIA’s WSL CUDA guide applies to this PC |
| CUDA / PyTorch | Selected **after** driver + GPU inspection + official PyTorch wheel matrix |
| Ollama | Local LLM runtime; Windows app vs WSL Linux binary must be decided and tested for API reachability from FastAPI |

---

## 1. Architecture of the workstation

```
Windows host
  ├── NVIDIA driver (if GPU present)
  ├── Optional: Ollama for Windows, Docker Desktop
  └── WSL2 Ubuntu
        ├── Python venv (backend + ml)
        ├── Node/npm (frontend) — or run frontend on Windows against WSL API
        ├── PostgreSQL client and/or server
        └── Optional: Ollama Linux build
```

**Do not assume** CUDA is visible inside WSL until `nvidia-smi` (or the current NVIDIA-recommended check) succeeds **inside the same environment where PyTorch will run**.

---

## 2. Verification commands (run in Phase 0, not now)

Run in the environment you will actually use for that tool (note Windows **PowerShell** vs **WSL bash**). Commands below are **planned checks**, not a promise they exist on this PC yet.

### 2.1 Python and pip

WSL (planned):

```bash
python3 --version
python3 -m pip --version
which python3
```

Windows PowerShell (if used):

```powershell
python --version
python -m pip --version
Get-Command python
```

### 2.2 Node and npm

```bash
node --version
npm --version
```

```powershell
node --version
npm --version
```

### 2.3 Git

```bash
git --version
```

```powershell
git --version
```

### 2.4 PostgreSQL

```bash
psql --version
pg_isready -h 127.0.0.1 -p 5432
```

If the server is not installed, record “not installed” and defer Phase 12. **Do not invent a Docker Postgres as running.**

### 2.5 NVIDIA GPU (Windows host)

PowerShell (planned; exact module names depend on driver):

```powershell
nvidia-smi
```

If `nvidia-smi` is missing, record no driver/GPU tools in PATH.

### 2.6 NVIDIA / CUDA inside WSL

```bash
nvidia-smi
```

Follow **current** NVIDIA WSL CUDA documentation if this fails. Do not install random CUDA toolkit versions.

### 2.7 PyTorch (only after a verified install in Phase 0)

CPU sanity:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

CUDA tensor test (**required** before claiming GPU support):

```bash
python -c "import torch; t=torch.tensor([1.0]).cuda(); print(t, t.sum().item())"
```

If `.cuda()` fails, document CPU-only. Do not retry by blindly pip-installing another `cuXXX` wheel without reading official install instructions for the observed driver.

### 2.8 Ollama

```bash
ollama --version
ollama list
```

HTTP check (path/port per **official** Ollama docs at the time of Phase 0—do not hard-code if docs differ):

```bash
# Planned: GET the documented local API root or version endpoint
```

Record whether FastAPI in WSL can reach Ollama on Windows `localhost` (this often needs a special hostname; **verify**, do not guess).

---

## 3. Planned install sequence (Phase 0+, not now)

High-level order **after** authorization:

1. Confirm WSL2 Ubuntu.
2. System packages as needed (`build-essential`, Python venv, etc.) per Ubuntu version.
3. Create project virtualenv; upgrade pip **inside** venv.
4. Inspect GPU; choose PyTorch install **from pytorch.org instructions**.
5. Install backend requirements (API first if splitting files).
6. Install Node LTS; later `npm install` in `frontend/`.
7. Install PostgreSQL; create empty database; no app tables until Phase 12.
8. Install Ollama; pull a **named** model only after a size/RAM decision.
9. Write `docs/environment-actual.md` and then generate `requirements.txt` files.

Exact `apt`/`winget` lines are **omitted here** so they are not copy-pasted as if already validated on this machine.

---

## 4. Python virtual environment (planned)

WSL:

```bash
cd /path/to/HelioScan
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# pip install -r backend/requirements.txt   # after that file exists and is verified
```

Windows PowerShell (if backend is not in WSL):

```powershell
cd C:\Users\vipin\Desktop\HelioScan
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

---

## 5. Planned runtime commands (untested)

Label remains **planned** until a phase runs them successfully.

### Backend

```bash
# create / activate venv (see above)
# pip install -r backend/requirements.txt
# copy .env.example to .env and fill verified secrets
python -m uvicorn app.main:app --reload --app-dir backend
# exact module path will match the Phase 1 package layout
```

Tests (planned):

```bash
cd backend && python -m pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```

### ML

```bash
# verify GPU as in §2.7
# train / eval / infer script names will be created in Phases 7–8
python -m ml.train --help    # does not exist yet
```

### Ollama

```bash
# install per official docs for Windows or Linux
# ollama pull <model>   # model name chosen in Phase 13, not guessed as a “default Llama”
ollama list
```

### Docker (Phase 17)

```bash
docker compose build
docker compose up
docker compose down
```

These compose commands **must not** be treated as working until Phase 17 tests them.

---

## 6. Environment variables (planned)

Typical keys (names may change; **no values** here):

- `DATABASE_URL`
- Geocoding API key (if the chosen provider requires one)
- Esri/ArcGIS credentials (if required)
- `OLLAMA_HOST` / model name
- `NASA_POWER` usually public HTTP—still confirm whether a key is required **from current docs**
- `HELIO_DEVICE=cuda|cpu|auto`

Never commit `.env`.

---

## 7. What Phase 0 must resolve

See README / closing report: Python location (WSL vs Windows), GPU in WSL, Ollama network path, PostgreSQL location, Node location, PyTorch wheel.

---

*End of environment setup document. No installs were performed for this specification task.*
