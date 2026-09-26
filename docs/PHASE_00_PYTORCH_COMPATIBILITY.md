# Phase 0 Step 3 — PyTorch / RTX 5070 Ti compatibility (pre-install)

**Date checked:** 2026-09-22  
**Status:** Research only. **PyTorch was not installed.** CUDA toolkit, NVIDIA drivers, `backend/.venv`, and other ML packages were not modified.

This report selects an **official PyTorch wheel** whose **bundled CUDA runtime** supports **Blackwell compute 12.0**. It does **not** treat the local CUDA toolkit or `nvidia-smi` CUDA UMD version as the wheel selector.

---

## Machine facts (from Phase 0 Steps 1–2)

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti Laptop GPU |
| Compute capability | **12.0** (Blackwell / `sm_120`) |
| Windows NVIDIA driver | **616.92** (KMD 616.92) |
| WSL | WSL2, kernel `6.6.87.2-microsoft-standard-WSL2` |
| WSL distro | Ubuntu **24.04.3 LTS** |
| Python | **3.12.3** (`ml/.venv`, created from `/usr/bin/python3`) |
| System CUDA toolkit | **13.1.1** at `/usr/local/cuda-13.1` (`nvcc` 13.1.115, **not** on default PATH) |
| Driver-reported CUDA (UMD) | **13.4** |
| ML venv | `/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv` |
| PyTorch today | **Not installed** (`ModuleNotFoundError: torch`) |

---

## Recommendation (pending approval to install)

| Decision | Choice |
| --- | --- |
| Recommended PyTorch version | **2.14.0** (`+cu130`) |
| Recommended CUDA wheel / index | **`cu130`** — official index `https://download.pytorch.org/whl/cu130` |
| Recommended torchvision | **Companion wheel from the same `cu130` index** (do not take torchvision from default PyPI). Exact `torchvision` version is published next to torch on that index and should be **recorded after install**, not guessed. |
| Python 3.12 supported? | **Yes.** Official index publishes `torch-2.14.0+cu130-cp312-cp312-manylinux_2_28_x86_64.whl`. `RELEASE.md` lists PyTorch 2.14 Python **≥ 3.10** (upper bound includes 3.15 experimental). |
| Compute 12.0 supported? | **Yes, for this CUDA build.** Official `RELEASE.md` (main, CUDA support matrix **for release 2.14**) lists CUDA **13.0.3** Linux x86/Windows architectures: Turing 7.5, Ampere 8.0/8.6, Hopper 9.0, **Blackwell 10.0, 12.0+PTX**. |
| Local toolkit 13.1 / driver 13.4? | **Irrelevant to wheel name.** Do **not** install a “CUDA 13.1” or “CUDA 13.4” PyTorch build. There is no `cu131`/`cu134` wheel requirement. Driver 13.4 can run a **13.0** wheel runtime (newer driver, older bundled CUDA). Toolkit `nvcc` 13.1 is **not** used by a binary wheel install. |

### Exact installation command (not executed)

Use the **ML venv only**. Do not run this until approved.

```bash
/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

Optional pin (same index; torchvision still resolved from `cu130`):

```bash
/mnt/c/Users/vipin/Desktop/HelioScan/ml/.venv/bin/python -m pip install torch==2.14.0 torchvision --index-url https://download.pytorch.org/whl/cu130
```

HelioScan does **not** need `torchaudio`. Official get-started snippets often include it; omit it unless a later phase requires audio.

**Do not** use:

```bash
pip install torch
# default PyPI / unspecified CUDA — often CPU or CUDA 12.6, which is wrong for sm_120
```

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
# CUDA 12.6 wheels: RELEASE.md 2.14 matrix lists Maxwell–Hopper only, NOT Blackwell 12.0
```

---

## Compatibility reasoning

1. **Three CUDA numbers must stay separate**
   - Driver UMD **13.4** = newest CUDA the **driver** will accept.
   - Toolkit **13.1.1** = local **nvcc**/headers. Binary wheels ship their own `nvidia-cuda-runtime` (and related) packages.
   - Wheel **`cu130`** = PyTorch was **built** against CUDA **13.0**. That is the number that must include **sm_120 kernels**.

2. **Blackwell / sm_120 rule (official + maintainer)**
   - GitHub issue [pytorch/pytorch#174284](https://github.com/pytorch/pytorch/issues/174284): maintainers point at `RELEASE.md` CUDA support matrix — **Blackwell → 12.8 or 13.0 builds; 12.6 does not**.
   - PyTorch engineer **ptrblck** (forums): binaries **built with CUDA 12.8+** support Blackwell / **sm_120**; CUDA **≤ 12.6** produces “capability sm_120 is not compatible” / missing kernel image. First stable line was **2.7.0 + cu128** (April 2025 blog).
   - Current **2.14** official matrix **documents Blackwell 12.0** on **CUDA 13.0 and 13.2**, not on **12.6**.

3. **Why `cu130` + 2.14.0 rather than `cu128`**
   - `https://download.pytorch.org/whl/cu130/torch/` currently lists **`torch-2.14.0+cu130-cp312-...manylinux_2_28_x86_64.whl`** (also 2.9–2.13).
   - `https://download.pytorch.org/whl/cu128/torch/` currently lists up through **`torch-2.11.0+cu128-cp312-...`** (no 2.14 on cu128 in that listing).
   - Driver **13.4 ≥ 13.0**, so a 13.0 wheel is valid.
   - 2.14 + CUDA 13.0 is the **documented** Linux x86 Blackwell **12.0** row in current `RELEASE.md`.

4. **Fallback if `cu130` install or GPU test fails (do not apply until that happens)**
   - Official `cu128` index, latest cp312 wheel observed: **2.11.0+cu128**.
   - Command: `.../ml/.venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`
   - Forum consensus and ptrblck: **cu128 includes sm_120**. This remains a valid Blackwell path; it is **not** the newest documented arch matrix (that is 2.14 / CUDA 13.0+).

5. **Python 3.12**
   - Wheels exist for **cp312** on both `cu128` and `cu130`.
   - `pytorch.org/get-started/locally/` Linux text: Python **3.10–3.14** recommended (page last updated 2026-07-27).
   - Forum (ptrblck): binaries support a Python range that **includes 3.12** (historically 3.9–3.13 for 2.7-era; 2.14 matrix is **≥ 3.10**).

6. **Website selector lag**
   - `https://pytorch.org/get-started/locally/` HTML still showed **Stable (2.7.0)** and compute options **CUDA 11.8 / 12.6 / 12.8** in the fetched page (2026-07-27). The **command box is JS-driven**; the default snippet in the dump was `cu118`, which is **wrong** for this GPU.
   - Prefer **wheel index + `RELEASE.md`**, then the get-started **shape** of the command (`pip` + `--index-url https://download.pytorch.org/whl/<cuXXX>`).
   - `https://docs.pytorch.org/get-started/locally/` was **stale** in this fetch (e.g. Stable 1.13.0 / CUDA 12.1–12.4). Do not follow that mirror for wheel choice.

---

## Planned post-install checks (next step only, after approval)

Not run now. After install, in `ml/.venv`:

```python
import torch
print("PyTorch:", torch.__version__)
print("Torch CUDA:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
print("Arch list:", torch.cuda.get_arch_list())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A")
t = torch.tensor([1.0], device="cuda")
print(t, float(t.sum()))
```

Success criteria (not claimed yet):

- `torch.__version__` contains `+cu130` (or `+cu128` if fallback).
- `torch.version.cuda` is **12.8 or 13.0+**, **not** 12.6/12.4/11.8.
- `torch.cuda.is_available()` is **True**.
- `get_arch_list()` includes **`sm_120`** (and/or `12.0`).
- A trivial CUDA tensor op **succeeds** (not only “CUDA available”).
- GPU name is RTX 5070 Ti.

---

## Official sources consulted

| Source | What was used |
| --- | --- |
| [pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/) | Official pip + `--index-url` pattern; Linux Python 3.10–3.14; CUDA 12.8 listed as a compute option. Selector HTML still showed Stable **2.7.0** (treat as possibly stale UI). |
| [docs.pytorch.org/get-started/locally/](https://docs.pytorch.org/get-started/locally/) | Fetched; **out of date** vs pytorch.org and wheel index. |
| [github.com/pytorch/pytorch `RELEASE.md` (main)](https://github.com/pytorch/pytorch/blob/main/RELEASE.md) | Release compatibility matrix (2.14 CUDA 12.6 / 13.0 / 13.2). **CUDA architecture matrix for 2.14:** CUDA 13.0.3 / 13.2.1 include **Blackwell 12.0+PTX**; CUDA 12.6.3 does **not**. |
| [download.pytorch.org/whl/cu130/torch/](https://download.pytorch.org/whl/cu130/torch/) | Confirmed `torch-2.14.0+cu130-cp312-cp312-manylinux_2_28_x86_64.whl`. |
| [download.pytorch.org/whl/cu128/torch/](https://download.pytorch.org/whl/cu128/torch/) | Confirmed latest `+cu128` **2.11.0** for cp312 (fallback). |
| [pytorch.org/blog/pytorch-2-7/](https://pytorch.org/blog/pytorch-2-7/) | First official Blackwell + **CUDA 12.8** wheels; example `pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128`. |
| [github.com/pytorch/pytorch/issues/174284](https://github.com/pytorch/pytorch/issues/174284) | Blackwell: use **12.8 or 13.0** builds; **12.6** has no Blackwell. |
| Forum threads (ptrblck / users) | [sm_120 availability](https://discuss.pytorch.org/t/when-will-sm120-support-be-available/223621), [RTX 5070 Ti sm_120](https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509), [RTX 5050 timeline](https://discuss.pytorch.org/t/rtx-5050-sm-120-support-timeline-when-in-stable-pytorch/224288): **CUDA 12.8+ wheels support sm_120**; older CUDA wheels do not. |

**Not used as authority:** third-party blogs, Stack Overflow answers that contradict the wheel index, or “match nvcc 13.1 / nvidia-smi 13.4”.

---

## Explicit non-actions (this step)

- Did not install PyTorch, torchvision, or CUDA Python packages.
- Did not modify CUDA toolkit or NVIDIA drivers.
- Did not install extra CUDA toolkits.
- Did not install other ML packages (OpenCV, Albumentations, etc.).
- Did not modify `backend/.venv`.
- Did not create `requirements.txt`.
- Did not train or start FastAPI/Next.js.

**STOP.** Installation and GPU tensor verification wait for approval.
