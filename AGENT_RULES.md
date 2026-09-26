# HelioScan — Agent and developer rules

These rules bind every human and AI contributor. They are not optional. If a request conflicts with this file, **stop and ask**; do not “be helpful” by inventing data or claiming untested work.

---

## 1. Scope discipline

- Implement **only** the currently authorized development phase (`DEVELOPMENT_PLAN.md`).
- Do not implement future phases “while we are here.”
- Do not add features, APIs, datasets, or UI screens that the current phase does not require.
- Do not rewrite working code without a stated reason (bug, security, or an explicit refactor task).
- Prefer small, incremental diffs.

This repository’s first delivered work is **specification only**. Application implementation starts only when Phase 0 is explicitly authorized.

---

## 2. Reliability

**Never:**

- Invent APIs, endpoints, query parameters, or HTTP methods.
- Invent API response bodies, field names, status codes, or error shapes.
- Invent dataset URLs, mirror links, or “standard” training-set locations.
- Invent free-tier limits, quotas, pricing, or rate limits.
- Invent authentication schemes, OAuth flows, or “typical” API key headers.
- Hard-code API keys, tokens, passwords, or connection strings.
- Silently swallow exceptions (`except: pass`, empty `except Exception`, logging that hides the error then continues as success).
- Ship fake production implementations (random numbers, placeholder kWh, canned NASA JSON presented as live).
- Claim that something works without running the relevant tests, linters, type checks, and a real process start where applicable.

**If documentation is missing or ambiguous:** record the gap, cite what was checked, and wait for a decision. Do not guess a production client.

**If a test cannot be run:** say so. Do not mark a phase complete.

---

## 3. External APIs

### 3.1 Before writing any client

Verify from **official** sources (provider docs, OpenAPI published by the vendor, or equivalent):

1. Base URL and current path versions
2. Authentication (whether required, header vs query, key restrictions)
3. Current usage limits and ToS
4. Response format and units
5. Licensing, attribution, caching, and redistribution (especially imagery in PDFs)

Write the verification result into `docs/` (or the phase notes) **before** implementation: date checked, URL of docs, constraints, open questions.

### 3.2 Every outbound call must include

- Timeouts (connect and read)
- Error handling for network, HTTP 4xx/5xx, and malformed bodies
- Response validation (Pydantic or equivalent)
- Rate-limit handling where the provider documents it (honor `Retry-After` if specified; backoff only per documented or conservative policy—do not invent quota numbers)
- Structured logging (no secrets in logs)
- Graceful failure: persist error state; **do not** fill downstream metrics with invented values

### 3.3 Secrets

- Store secrets in environment variables / `.env` (gitignored).
- Ship `.env.example` with blank or dummy names only.
- Never commit credentials, Esri tokens, database passwords, or Ollama-unrelated cloud keys.

---

## 4. LLM rules

The local Llama model via Ollama is **narrative only**.

The LLM must **never** be the source of truth for:

- Solar calculations
- Energy generation (kWh)
- Financial calculations
- ROI
- Payback period
- CO₂ calculations
- Roof area or usable area

Those values are produced by **deterministic Python** (and ML mask geometry for area). The LLM receives a validated snapshot and explains it.

Additional LLM rules:

- All structured LLM output is parsed and validated with **Pydantic**. Invalid JSON/schema → error, not a partial dashboard.
- Prompts must instruct the model not to invent numeric results. Phase 13 should add automated checks that numbers in the prose appear in the snapshot (best-effort; still do not trust the model for math).
- Do not send API keys or raw provider credentials to the model.
- If Ollama is down, the analysis may still complete with metrics and a “proposal unavailable” state—never a fabricated essay presented as generated.

---

## 5. GPU and PyTorch

The ML pipeline must be **GPU-aware** and **never assume CUDA**.

Before selecting PyTorch/CUDA wheels:

1. Inspect the NVIDIA driver on the actual machine (WSL2 + Windows as documented).
2. Inspect the GPU model and VRAM.
3. Verify PyTorch/CUDA compatibility against **current official PyTorch install guidance** for that driver.
4. Perform an **actual CUDA tensor test** (`tensor.to("cuda")` + a trivial op) before declaring GPU support.

Rules:

- Use GPU when the test passes.
- Provide **CPU fallback** for inference and development.
- Never blindly install a CUDA toolkit or PyTorch build.
- Never pin `cu118` / `cu124` / etc. from memory or from another machine.
- Training jobs must fail clearly if the configured device is unavailable (unless CPU training is explicitly requested).

Document the chosen wheel and the verification commands/output (sanitized) in environment notes when Phase 0 / Phase 7 runs.

---

## 6. Code quality

- Every **major service** has tests (happy path + failure path).
- Every **external integration** has **mocked** tests (no live network in default CI).
- Optional live/integration tests must be clearly marked and skippable without credentials.
- Do not make unrelated changes in the same diff (no drive-by refactors, no formatting the whole repo).
- Prefer small incremental changes.
- Do not rewrite working code without justification.

**Before declaring a phase complete:**

1. Run the test suite in scope
2. Run lint
3. Run type checks
4. Verify the application **actually starts** (backend and/or frontend as relevant)

If a tool is not yet installed (pre–Phase 0), do not pretend the checks passed.

---

## 7. Data, models, and “demo realism”

- Do not download datasets until the dataset phase is authorized and licenses are recorded.
- Do not commit large binary weights unless an explicit exception is made; use git-lfs or documented download scripts later.
- Do not use copyrighted imagery in repo fixtures unless the license allows it; prefer synthetic or clearly licensed samples.
- Deterministic engines may use **documented default assumptions** (performance ratio, packing factor, emission factor). Defaults must be visible in API/UI/PDF, not hidden.

---

## 8. Documentation honesty

- README and phase docs must say **Under Development** until a phase is done and verified.
- Planned commands are labeled **planned** until executed successfully on the target environment.
- Do not copy vendor docs verbatim in violation of copyright; summarize and link.

---

## 9. Git and secrets hygiene

- Do not `git commit` unless the user asks.
- Do not force-push or rewrite shared history unless the user explicitly requests it.
- Do not disable hooks to hide failures.

---

## 10. Conflict resolution

If product spec, phase plan, and these rules disagree: **these reliability/API/LLM/GPU rules win**, then stop for a human decision.

---

*End of agent rules.*
