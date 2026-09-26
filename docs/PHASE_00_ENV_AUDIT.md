# Phase 0 — Environment audit (step 1)

**Date:** 2026-09-22  
**Scope (Step 1):** Read-only inspection. **Scope (Step 2):** create two empty `venv`s only. No project packages, no `requirements.txt`, no PostgreSQL/PyTorch/Node/Ollama work.  
**Primary WSL distro audited:** `Ubuntu` (default, WSL2) — Ubuntu 24.04.3 LTS  
**Windows host:** PowerShell on `win32`  
**Project path (Windows):** `C:\Users\vipin\Desktop\HelioScan`

This document records **exact command outputs** and a concise analysis. PyTorch/CUDA wheel selection is **not** made here.

---

## A. WSL distros present

Command (Windows): `wsl -l -v`

```
  NAME              STATE           VERSION
* Ubuntu            Stopped         2          (started for this audit)
  docker-desktop    Stopped         2
  Ubuntu-22.04      Stopped         2
```

(Original `wsl -l -v` output was UTF-16 spaced characters; table above is the decoded listing.)

- Default (`*`) distro: **Ubuntu**
- Secondary: **Ubuntu-22.04** (spot-checked only; not used as the HelioScan target)

Spot-check `wsl -d Ubuntu-22.04 -- bash -c "cat /etc/os-release | head -5; python3 --version"`:

```
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
Python 3.10.12
```

**HelioScan audit target is default `Ubuntu` 24.04**, not Ubuntu-22.04.

---

## B. Requested commands (WSL `Ubuntu` unless noted)

### 1. `uname -a`

```
Linux LAPTOP-P9E7SV9T 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux
```

### 2. `cat /etc/os-release`

```
PRETTY_NAME="Ubuntu 24.04.3 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.3 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
```

### 3. `python3 --version`

```
Python 3.12.3
```

Additional (not requested, recorded for location):

```
3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
/usr/bin/python3
```

### 4. `python3 -m pip --version`

```
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
```

`which python3` / `which pip3`:

```
/usr/bin/python3
/usr/bin/pip3
```

### 5. `node --version` (WSL)

```
v20.20.0
```

`which node`: `/usr/bin/node`

### 6. `npm --version` (WSL)

```
10.8.2
```

`which npm`: `/usr/bin/npm`

### 7. `git --version` (WSL)

```
git version 2.43.0
```

`which git`: `/usr/bin/git`

### 8. `nvidia-smi` (WSL)

```
Tue Sep 22 16:43:53 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 615.71.08              KMD Version: 616.92        CUDA UMD Version: 13.4     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5070 ...    On  |   00000000:02:00.0 Off |                  N/A |
| N/A   42C    P5             11W /   95W |     118MiB /  12227MiB |     60%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

`which nvidia-smi` (WSL): `/usr/lib/wsl/lib/nvidia-smi`

Query: `nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv`

```
name, driver_version, memory.total [MiB], compute_cap
NVIDIA GeForce RTX 5070 Ti Laptop GPU, 616.92, 12227 MiB, 12.0
```

### 9. `which nvcc` (WSL default PATH)

Not on `PATH`. `nvcc --version` as a bare command:

```
bash: line 1: nvcc: command not found
```

**Found off-PATH** (additional inspection, not an install):

```
/usr/local/cuda/bin/nvcc
```

`readlink -f /usr/local/cuda` → `/usr/local/cuda-13.1`  
`/usr/local/cuda` → `/etc/alternatives/cuda`

### 10. `nvcc --version` (full path `/usr/local/cuda/bin/nvcc`)

```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2025 NVIDIA Corporation
Built on Tue_Dec_16_07:23:41_PM_PST_2025
Cuda compilation tools, release 13.1, V13.1.115
Build cuda_13.1.r13.1/compiler.37061995_0
```

`/usr/local/cuda/version.json` reports CUDA SDK **13.1.1** (truncated here to the `cuda` object; full file is on disk):

```json
{
   "cuda" : {
      "name" : "CUDA SDK",
      "version" : "13.1.1"
   }
}
```

`dpkg` (excerpt):

```
ii  cuda-toolkit                    13.1.1-1                                amd64        CUDA Toolkit meta-package
ii  cuda-toolkit-13-1               13.1.1-1                                amd64        CUDA Toolkit 13.1 meta-package
ii  cuda-toolkit-13-1-config-common 13.1.80-1                               all          Common config package for CUDA Toolkit 13.1.
ii  cuda-toolkit-13-config-common   13.1.80-1                               all          Common config package for CUDA Toolkit 13.
ii  cuda-toolkit-config-common      13.1.80-1                               all          Common config package for CUDA Toolkit.
```

WSL user-mode CUDA libraries present:

```
/usr/lib/wsl/lib/libcuda.so
/usr/lib/wsl/lib/libcuda.so.1
/usr/lib/wsl/lib/libcuda.so.1.1
/usr/lib/wsl/lib/libcudadebugger.so.1
```

`CUDA_PATH` was unset in the non-login command environment used for that check.

**Note:** `version.json` also lists `"nvidia_driver": "590.48.01"`. That is the **toolkit metadata**, not the live GPU driver. Live WSL/Windows driver is **616.92** (see `nvidia-smi`).

### 11. `which ollama` (WSL)

```
/usr/local/bin/ollama
```

### 12. `ollama --version` (WSL)

```
ollama version is 0.17.4
```

Read-only `ollama list` (no pull, no config change):

```
NAME             ID              SIZE      MODIFIED     
llama3:latest    365c0bd3c000    4.7 GB    6 months ago    
```

### 13. `which psql` (WSL)

Not found (`psql` command failed).

### 14. `psql --version` (WSL)

```
bash: line 1: psql: command not found
```

`dpkg -l | grep -i postgres` → `no postgresql packages`  
`ls /usr/lib/postgresql` → `no /usr/lib/postgresql`  
`systemctl is-active postgresql` → `inactive` (and no package present)

---

## C. Windows host (same machine; not a substitute for WSL Python/ML)

### GPU / driver — `nvidia-smi`

```
Tue Sep 22 22:11:04 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 616.92                 KMD Version: 616.92        CUDA UMD Version: 13.4     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5070 ...  WDDM  |   00000000:02:00.0 Off |                  N/A |
| N/A   40C    P4              8W /   95W |     118MiB /  12227MiB |     13%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A           19504    C+G   ...al\Programs\Cursor.exe      N/A      |
+-----------------------------------------------------------------------------------------+
```

`nvidia-smi -q` excerpts:

```
Driver Version                                         : 616.92 [Deprecated; will be removed in CUDA 14.0. Use KMD Version instead]
CUDA Version                                           : 13.4 [Deprecated; will be removed in CUDA 14.0. Use CUDA UMD Version instead]
    Product Name                                       : NVIDIA GeForce RTX 5070 Ti Laptop GPU
    Product Brand                                      : GeForce
```

### Other Windows tools

| Tool | Result |
| --- | --- |
| Git | `git version 2.52.0.windows.1` — `C:\Program Files\Git\cmd\git.exe` |
| Node.js | `v24.13.0` — `C:\Program Files\nodejs\node.exe` |
| npm | `11.6.2` |
| Python | `3.14.2` — `C:\Python314\python.exe` |
| `nvcc` | not on PATH (`where.exe nvcc` found nothing) |
| `psql` | not on PATH |
| `ollama` | not on Windows PATH (`where.exe ollama` found nothing). Ollama **is** present **inside WSL**. |
| Docker CLI | visible from WSL as `/mnt/c/Program Files/Docker/Docker/resources/bin/docker` (Docker Desktop distro exists; not started for this audit) |

Windows `python -c "import torch; ..."`:

```
ModuleNotFoundError: No module named 'torch'
```

---

## D. PyTorch (read-only)

WSL:

```
ModuleNotFoundError: No module named 'torch'
```

WSL `import torchvision` → `ModuleNotFoundError: No module named 'torchvision'`  
WSL `import fastapi` → `ModuleNotFoundError: No module named 'fastapi'`  
WSL `import numpy` → `ModuleNotFoundError: No module named 'numpy'`

**PyTorch is not installed** on WSL system Python or Windows Python 3.14. No CUDA tensor test was run (would require installing/using torch).

---

## E. Environment managers (read-only)

In default WSL Ubuntu:

```
conda: not found
mamba: not found
micromamba: not found
uv: not found
poetry: not found
```

No HelioScan backend/ML virtual environments exist (none were created).

---

## F. Analysis

### 1. What is already installed

- WSL2 kernel `6.6.87.2-microsoft-standard-WSL2`
- Default distro **Ubuntu 24.04.3 LTS**
- Python **3.12.3** + pip **24.0** (Debian/Ubuntu system packages)
- Node **v20.20.0** + npm **10.8.2** (WSL)
- Git **2.43.0** (WSL) and **2.52.0** (Windows)
- NVIDIA GPU visible in WSL (`nvidia-smi`, `libcuda.so`)
- CUDA **toolkit 13.1.1** under `/usr/local/cuda-13.1` including `nvcc` (not on default PATH)
- Ollama **0.17.4** in WSL with model `llama3:latest` (4.7 GB) already pulled
- Windows NVIDIA driver stack (SMI **616.92**, CUDA UMD **13.4**)
- Windows Node **v24.13.0** / npm **11.6.2** (different from WSL)
- Windows Python **3.14.2** (different from WSL)
- Docker Desktop bits present (distro stopped; not audited as running)

### 2. What is missing

- PostgreSQL server and `psql` client (WSL packages absent; Windows `psql` not on PATH)
- PyTorch / torchvision / CUDA-enabled ML Python stack
- FastAPI / Uvicorn / backend Python stack
- NumPy and other ML/backend libraries on system Python
- `nvcc` on default `PATH` (binary exists but is not discoverable via `which nvcc`)
- Conda / Mamba / uv / Poetry
- Dedicated backend and ML virtual environments (intentionally not created)
- `backend/requirements.txt` / `ml/requirements.txt` (intentionally not created)
- Windows-native Ollama on PATH (WSL Ollama exists instead)
- Project application code (still specification-only)

### 3. GPU status

- **WSL can see the NVIDIA GPU: yes**
- Model: **NVIDIA GeForce RTX 5070 Ti Laptop GPU**
- VRAM: **12227 MiB** (~12 GB)
- Compute capability reported by `nvidia-smi`: **12.0** (Blackwell-class)
- WDDM on Windows; persistence “On” in WSL listing
- Laptop TGP cap shown as **95 W**

### 4. NVIDIA driver status

- Windows KMD / SMI: **616.92**
- WSL `NVIDIA-SMI` user-mode: **615.71.08**, KMD **616.92**
- This is a **new** driver line reporting CUDA UMD **13.4**
- Do not confuse toolkit JSON `nvidia_driver 590.48.01` with the live driver

### 5. CUDA status

Three **different** CUDA version numbers are present and must not be collapsed:

| Source | Version | Meaning |
| --- | --- | --- |
| Windows/WSL `nvidia-smi` CUDA UMD | **13.4** | Max CUDA runtime the **driver** will accept |
| WSL CUDA toolkit (`nvcc`, packages) | **13.1.1** | Local **compiler/toolkit** install |
| PyTorch-reported CUDA | **N/A** | PyTorch not installed |

- `nvcc` **is installed** at `/usr/local/cuda/bin/nvcc`, **not** on default PATH
- WSL CUDA driver libraries exist under `/usr/lib/wsl/lib/`
- **The toolkit version must not be used as the PyTorch wheel selector.** Official PyTorch CUDA builds (e.g. cu124 / cu128 / cu130) are chosen against GPU arch + PyTorch’s published wheels, after a later verification step.
- RTX 5070 Ti / **sm_120** requires a PyTorch build that actually includes that arch. Older cu118/cu121 wheels are a high risk of “CUDA available but kernel not compiled for this GPU” even if the driver is new.

### 6. PyTorch status

- **Not installed** (WSL Python 3.12.3 and Windows Python 3.14.2)
- `torch.cuda.is_available()` **not measured**
- No GPU tensor test performed

### 7. PostgreSQL status

- **Not installed** in the audited WSL Ubuntu (no packages, no `psql`)
- Not on Windows PATH
- Not configured

### 8. Ollama status

- **Installed in WSL:** `/usr/local/bin/ollama`, version **0.17.4**
- Model already present: **`llama3:latest`**
- Not on Windows PATH
- Service was not started/configured as part of this audit (version/list only)
- FastAPI-in-WSL → Ollama-in-WSL is the natural path; Windows↔WSL localhost mapping was **not** tested

### 9. Node.js status

- **Installed in WSL:** Node **v20.20.0**, npm **10.8.2** (good LTS-class for Next.js)
- **Also installed on Windows:** Node **v24.13.0**, npm **11.6.2**
- Two Node majors on one machine: later frontend work must pick **one** runtime and stick to it

### 10. Git status

- **Installed** on Windows (2.52.0) and WSL (2.43.0)
- Line endings / which Git operates on `C:\Users\vipin\Desktop\HelioScan` should be decided when development starts (WSL `/mnt/c/...` vs Windows)

### 11. Backend environment status

- **Does not exist yet**
- System Python 3.12.3 has **no** FastAPI
- Windows Python 3.14.2 is **unsuitable as a default backend** without a separate decision: 3.14 is very new; many wheels lag
- Backend must **not** receive the CUDA/PyTorch stack (confirmed as a plan; nothing installed)

### 12. ML environment status

- **Does not exist yet**
- No Conda/venv/uv isolation present
- GPU **is** visible to WSL, which is the intended place for a CUDA-capable ML env
- Toolkit 13.1 and driver UMD 13.4 are present; **PyTorch still unchosen**
- System Python must not be used as the ML env (Ubuntu `python3` is distro-managed)

### 13. Potential compatibility issues

1. **Blackwell / compute 12.0:** RTX 5070 Ti Laptop needs a PyTorch build with **sm_120** support. Driver CUDA 13.4 does **not** automatically imply any particular `pip install torch` index URL.
2. **Multiple CUDA numbers (13.4 vs 13.1 vs future torch.version.cuda):** mixing them up is the main install foot-gun.
3. **`nvcc` not on PATH:** compiling custom CUDA extensions would fail until PATH/`CUDA_HOME` are set; many PyTorch wheels do **not** need local `nvcc`.
4. **Two Ubuntu distros:** installing into Ubuntu-22.04 by mistake would fork the environment.
5. **Two Node.js versions (20 vs 24) and two Pythons (3.12 vs 3.14):** path confusion.
6. **Windows Python 3.14** vs **WSL 3.12:** HelioScan backend/ML should almost certainly live on **WSL 3.12** unless Phase 0 later proves otherwise.
7. **Laptop 12 GB / 95 W:** training batch sizes and 4.7 GB Llama + training concurrently may OOM or throttle; not tested.
8. **Ollama only in WSL:** Windows-hosted tools will not see `ollama` unless WSL is used or Windows Ollama is installed later.
9. **PostgreSQL missing:** Phase 12 (and any early DB) needs a later install step.
10. **Project on `/mnt/c`:** if venvs are created on the Windows filesystem from WSL, bind-mount performance/permissions can hurt; location still TBD after this audit.

### 14. Recommended NEXT STEP only

**Do not install PyTorch, CUDA packages, PostgreSQL, Node upgrades, or virtual environments yet.**

**Next step (Phase 0, step 2 — pending your approval):** decide the **physical layout** of the two logical environments (Backend vs ML) and the **mechanism** (`venv` vs Conda/etc.), using this audit:

- Target OS: default WSL **Ubuntu 24.04**
- Target Python for both envs: **3.12.3** (`/usr/bin/python3`), not Windows 3.14
- ML env: WSL, GPU-visible, **no wheel chosen until** official PyTorch compatibility for **RTX 5070 Ti / sm_120** is checked in a following step
- Backend env: WSL, CPU-only Python deps, **no** torch/CUDA
- Defer PostgreSQL install and `requirements.txt` until those decisions are written down

STOP. Waiting for approval before any further Phase 0 work.

---

## Phase 0 Step 2 — Python Environment Setup

**Status:** Complete (2026-09-22). Mechanism: Python stdlib **`venv`**. Conda/uv/Poetry were not installed.

**Host used:** WSL distro `Ubuntu` (24.04.3), system interpreter `python3` → **Python 3.12.3** (`/usr/bin/python3`).

Commands run (no packages installed after creation):

```bash
python3 -m venv /mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv
python3 -m venv /mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv
```

### Environment paths

| Role | WSL path | Windows path |
| --- | --- | --- |
| Backend venv | `/mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv` | `C:\Users\vipin\Desktop\HelioScan\backend\.venv` |
| Backend Python | `/mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv/bin/python` | (use via WSL) |
| ML venv | `/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv` | `C:\Users\vipin\Desktop\HelioScan\ml\.venv` |
| ML Python | `/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv/bin/python` | (use via WSL) |

Both `sys.base_prefix` values are `/usr` (shared **system** CPython 3.12). `sys.prefix` values differ (see independence).

### Python versions

```
$ backend/.venv/bin/python --version
Python 3.12.3

$ ml/.venv/bin/python --version
Python 3.12.3
```

`sys.executable` / `sys.prefix` / `sys.base_prefix`:

Backend:

```
/mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv/bin/python
/mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv
/usr
```

ML:

```
/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv/bin/python
/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv
/usr
```

### pip versions

```
$ backend/.venv/bin/pip --version
pip 24.0 from /mnt/c/Users/vipin/Desktop/HelioScan/backend/.venv/lib/python3.12/site-packages/pip (python 3.12)

$ ml/.venv/bin/pip --version
pip 24.0 from /mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv/lib/python3.12/site-packages/pip (python 3.12)
```

pip was **not** upgraded.

### Independence

- Distinct `sys.prefix` and `sys.executable` (backend vs `ml`).
- Distinct `site-packages` trees (`backend/.venv/lib/python3.12/site-packages` vs `ml/.venv/lib/python3.12/site-packages`).
- pip reports its own copy under each venv.

### No project dependencies installed

`pip list` after creation — backend:

```
Package Version
------- -------
pip     24.0
```

`pip list` after creation — ML:

```
Package Version
------- -------
pip     24.0
```

Not installed (confirmed by absence from `pip list`): FastAPI, Uvicorn, Pydantic, SQLAlchemy, PostgreSQL drivers, httpx, pytest, torch, torchvision, OpenCV, Pillow, NumPy, pandas, scikit-learn, Albumentations.

CUDA toolkit, NVIDIA drivers, and system Python were not modified. `requirements.txt` was not created.

### Step 2 stop

PostgreSQL, PyTorch/CUDA wheels, Node/npm project setup, and Ollama configuration were **not** started.

**Next (Phase 0 Step 3) requires explicit approval.**

---

*End of environment audit (through Phase 0 Step 2).*
