# AutoSRE: Upgrade Plan

Goal: make this project read as **engineering + ML**, so it works for SDE roles (Apollo-style: tested, CI/CD, containerised, clean code) and ML/AI roles (evaluation, honest metrics, reliability).

Repo reviewed (code read, not run): `github.com/dhruvbadhe/AutoSRE` (last commit 23 Sep 2026)

---

## How to use this file

1. Do **Part 0** first. These are bugs that make current resume claims untrue.
2. Then Part 1 in the order given. Each task has a done-check.
3. Work through **pull requests**, not direct pushes to `main`. Turn on branch protection once CI exists.
4. Only put a bullet on the resume once its done-check passes and it's pushed.
5. Before any interview, go through the interview section in Part 1 and be able to explain every file you changed.

---

## Part 0: Fix before anything else

| # | Problem | Where | Why it matters |
|---|---|---|---|
| 0.1 | **Safety gate isn't in the pipeline.** The dangerous-command check exists only in `eval/run_eval.py` (scores after the run). The runtime `verification_node` only checks confidence ≥ 0.60 and never inspects the command. | `app/graph/nodes/verification.py` | "Pre-flight safety gates" is false today |
| 0.2 | **`verification_node` returns `None` on the success path.** The `return` is indented inside `else:`, so when confidence ≥ 0.60 nothing is returned and `verification_result` is never set. | `app/graph/nodes/verification.py` | Bug in the normal path |
| 0.3 | **"100% Recall@3" is from 4 scenarios.** | `eval/eval_results.json` | Expand the eval or state the size |

Each of these is also an interview story: **wrote a test → it failed → found the bug → fixed it → the test stays in the suite.** Keep the failing test commit and the fix commit separate so the history shows it.

---

## Part 1: Tasks

### Current state
- **Good:** clear package layout (`graph/nodes`, `services`, `schemas`, `routers`, `core`), LangGraph workflow, FastAPI backend, Typer CLI published to PyPI via `pyproject.toml`, Dockerfile + docker-compose with healthchecks, an eval script with per-scenario results, 7 existing tests.
- **Missing:** a real runtime safety gate, CI, tests on the risky parts, eval size, automated releases.

### Tasks (in order)

| # | Task | Done when | Time |
|---|---|---|---|
| A0.5 ✅ | Fix `/api/incidents/metrics` 500 (found during setup): `get_metrics` returns `resolved_incidents`/`escalated_incidents`/`mean_time_to_resolution_seconds`, but `MetricsResponse` expects `resolved_count`/`escalated_count`/`open_count`/`mttr_seconds`. Failing test first, then minimal fix in the handler. No xfail. | `test_metrics_endpoint` passes | 15 min |
| A1 ✅ | Write a failing test for 0.2 (high confidence → node returns `verification_result="resolved"`) | Test fails on current code | 15 min |
| A2 ✅ | Fix 0.2: return in both branches | A1 passes | 10 min |
| A3 ✅ | Fix 0.1: move the denylist into a `safety.py` module used by `verification_node`. Unsafe command → `escalate=True` regardless of confidence. Eval script imports the same module (one source of truth). Add `drop table`, `kubectl delete ns`, `scale --replicas=0`, `truncate`. Normalise case and whitespace before matching. | Unsafe fix is escalated at runtime | 45 min |
| A4 ✅ | **Parametrized tests** for the safety gate: each dangerous pattern blocked, safe commands allowed, mixed-case and extra-whitespace variants blocked | All pass | 30 min |
| A5 ✅ | **Mock the LLM and embedder** in tests (fixture or dependency override) so tests run without `GEMINI_API_KEY` or model downloads | `pytest` passes offline | 1 h |
| A6 ✅ | **GitHub Actions CI:** ruff → pytest → Docker build | Green badge | 45 min |
| A7 ✅ | **Release workflow:** publish to PyPI on a `v*` tag via trusted publishing; bump version | Tag → new PyPI version | 45 min |
| A8 | **Expand eval** from 4 to ~20 scenarios: known incidents, similar-wording traps, unknown incidents that should escalate, prompts that tempt an unsafe command | `eval_results.json` has ~20 scenarios; README states the size | 1.5 h |
| A9 | Add an eval check: **unsafe command reached output = failure** (now checked at runtime, measured by the eval) | Metric in results | 20 min |
| A10 ✅ | README: architecture diagram of the 7 nodes, the safety gate's limits (a denylist can be bypassed; next step is an allowlist or a dry-run), eval table with size, CI badges | README updated | 1 h |

**Optional**
- **Tracing:** log each node's input, output, latency and tokens to JSON; `autosre trace <run_id>` CLI command. Strong for AI-engineering roles.
- **Allowlist mode:** only allow commands matching known safe verbs (`get`, `describe`, `logs`, `rollout restart`). Safer than a denylist, and a good design discussion.
- **Retry/timeout** around the LLM call with a clear escalation on failure.

### What to know cold for interviews (AutoSRE)
- **The bug story:** eval said 100% safe, but the check only ran in the eval, not at runtime. How you found it, the test, the fix.
- **Denylist limits:** obfuscation (`r''m -rf`, base64, `$(...)`), why allowlists are safer.
- **Hybrid retrieval:** dense vs BM25, what Reciprocal Rank Fusion does, why it helps with exact error strings.
- **CRAG loop:** grader → rewriter → retry; what stops it looping forever.
- **Packaging:** `pyproject.toml`, `[project.scripts]` entry point, how `kubectl logs | autosre` reads stdin.
- **Mocking in tests:** why CI must not call a paid LLM.

---

## Part 2: Resume bullets (SDE + ML)

Use these once the matching tasks are done. Replace `N` and `X` with real numbers.

**AutoSRE – Incident Response Agent** (Python, LangGraph, FastAPI, ChromaDB, PyPI) — GitHub | PyPI
- Built and published `autosre-agent` to PyPI: a CLI (`kubectl logs | autosre`) and FastAPI service that diagnose infrastructure alerts, retrieve runbooks with hybrid dense + BM25 search (Reciprocal Rank Fusion), and draft remediation plans.
- Engineered a runtime safety gate that escalates any generated command matching destructive patterns, after the eval harness showed the check ran only offline; covered by parametrized tests.
- Built an eval harness over N scenarios measuring retrieval hit rate, routing accuracy and unsafe-command rate, with CI (mocked LLM) and tag-based PyPI releases.

### Which bullet to lead with
| Target | Lead with |
|---|---|
| SDE (Apollo, SAP) | Bullet 1 (CLI/packaging) then 3 (CI/releases) |
| ML / AI engineer | Bullet 2 (safety gate) then 3 (evals) |

### Claims to remove or reword everywhere
- "0.0% safety-violation rate" → describe the gate and its tests instead.
- "100% Recall@3" → only with the eval size.
- "~73% MTTR reduction" → drop it, or state the baseline it's measured against.
- "kubectl commands … rm -rf, DROP TABLE" → "generated shell and database commands".

---

## Part 3: Order of work and time (with Claude Code)

| Block | Tasks | Time |
|---|---|---|
| 1 | A1–A4 (bug + runtime safety gate + tests) | 1.75 h |
| 2 | A5–A6 (mocks + CI) | 1.75 h |
| 3 | A10 (README) | 1 h |
| **Total** | | **~4.5 h** |
| Later | A7–A9 (PyPI releases, bigger eval), optional items | +3 h |

If time is short, blocks 1–2 alone make every AutoSRE resume claim true.

### Prompting Claude Code
- One task per session. Paste the task row and its done-check.
- Ask it to write the **failing test first**, run it, then fix.
- Ask for a short explanation of every changed file, and read the diff before committing.
- Never let it change the LangGraph flow, prompts or retrieval logic during these tasks; only the files the task names.

### Before submitting
- [ ] CI green
- [ ] `pip install autosre-agent` works and `autosre --help` runs
- [ ] Every resume number matches the repo
- [ ] You can explain every file you changed
