# AutoSRE upgrade report (2026-10-15)

Autonomous run of `docs/UPGRADE_PLAN.md`. Every change went through a PR on GitHub and was squash-merged after review checks (and CI from A6 on). Nothing was pushed straight to `main`, nothing was force-pushed, no version was bumped, no tag was pushed, nothing was published to PyPI, and `stash@{0}` (`local-eval-run-2026-10-15`) is untouched.

## 1. Tasks

| Task | Branch | PR | Status |
|---|---|---|---|
| Setup | `chore/agent-docs` | [#1](https://github.com/dhruvbadhe/AutoSRE/pull/1) | ✅ merged |
| A0.5 metrics 500 | `fix/metrics-response-schema` | [#2](https://github.com/dhruvbadhe/AutoSRE/pull/2) | ✅ merged |
| A1+A2 `verification_node` returns None | `fix/A1-verification-return` | [#3](https://github.com/dhruvbadhe/AutoSRE/pull/3) | ✅ merged |
| A3+A4 runtime safety gate + tests | `fix/A3-runtime-safety-gate` | [#4](https://github.com/dhruvbadhe/AutoSRE/pull/4) | ✅ merged |
| A5 offline mocks | `fix/A5-offline-test-mocks` | [#5](https://github.com/dhruvbadhe/AutoSRE/pull/5) | ✅ merged |
| A6 CI | `fix/A6-github-actions-ci` | [#6](https://github.com/dhruvbadhe/AutoSRE/pull/6) | ✅ merged, CI green |
| A10 README | `fix/A10-readme` | [#7](https://github.com/dhruvbadhe/AutoSRE/pull/7) | ✅ merged, CI green |
| A7 release workflow | `fix/A7-pypi-release` | [#8](https://github.com/dhruvbadhe/AutoSRE/pull/8) | ⏳ merged; first real release needs your PyPI setup (section 3) |
| A8+A9 eval | `fix/A8-expanded-eval` | [#9](https://github.com/dhruvbadhe/AutoSRE/pull/9) | A9 ✅ / A8 ⏳ merged; real 3-run eval **not run** (no `GEMINI_API_KEY` in shell) |
| Report | `docs/upgrade-report` | this PR | — |

Each PR body holds the full 4-part report with complete command output. Condensed versions follow.

### A0.5: `/api/incidents/metrics` always returned 500
1. **PASS.** `pytest tests/test_api.py::test_metrics_endpoint`. Before: `ResponseValidationError: 4 validation errors … missing resolved_count/escalated_count/open_count/mttr_seconds`. After: `1 passed`.
2. **Files:**
   - `tests/test_api.py`: asserts the exact `MetricsResponse` field set.
   - `app/routers/incidents.py`: the handler returns the schema's field names (which the dashboard already read) and adds `open_count`.
3. **Q:** Why 500 and not 422? **A:** The *response* failed `response_model` validation, which is a server bug. 422 is for bad request input.
4. **Commits:** test commit `c571568` → fix commit.

### A1+A2: `verification_node` returned `None` on the success path
1. **PASS.** `pytest tests/test_verification.py`. Before: `TypeError: 'NoneType' object is not subscriptable`. After: `2 passed`.
2. **Files:**
   - `tests/test_verification.py`: new node-level tests.
   - `verification.py`: the return block moved out of `else:`.
3. **Q:** Why did nobody notice? **A:** A LangGraph node that returns `None` writes nothing, and `escalate` defaulted to `False`, which happens to be right for confident fixes. The committed eval even shows `eval-004` not escalating.
4. **Commits:** test `ea0595d` → fix.

### A3+A4: runtime safety gate and parametrized tests
1. **PASS.** Before: `assert 'resolved' == 'unresolved'` for a 0.99-confidence `kubectl delete namespace`. After: `3 passed`. Safety tests: `30 passed, 1 xfailed`.
2. **Files:**
   - `app/services/safety.py`: 9 word-boundary regexes on lowercased, whitespace-collapsed text.
   - `verification.py`: checks safety *before* confidence.
   - `eval/run_eval.py`: imports the same module, with no list of its own.
   - `tests/test_safety.py`: every pattern, case and whitespace variants, safe commands, a strict xfail for the quoting bypass.
3. **Q:** Why a strict xfail? **A:** It records the known limit in code. If someone closes the gap, the test passes unexpectedly and forces a real test.
4. **Commits:** test `3fcc267` → fix `49ea7eb` → tests.

### A5: tests run offline
1. **PASS.** From an empty dir with no key and no `.env`: `44 passed, 1 xfailed`. Before: 2 collection errors (`GEMINI_API_KEY Field required`).
2. **Files:**
   - `tests/conftest.py`: dummy key, temp DB and Chroma set before import; fake `llm.model`, embedder and DDGS; socket guard.
   - `tests/test_graph.py`: real graph, fake LLM covering resolve, unsafe → `ESCALATED`, and the CRAG loop.
   - `tests/test_offline.py`: the guard works.
3. **Q:** Why patch `llm.model`, not `generate_text`? **A:** Each node imported `generate_text` by name. Patch where the name is looked up.
4. **Commits:** `beb36a8`.

### A6: GitHub Actions CI
1. **PASS.** Run 38781042739: lint ✅, `44 passed, 1 xfailed`, 58% of app/, Docker build ✅, `pip install .` → `autosre --help` exit 0 ✅ (2m1s).
2. **Files:**
   - `ci.yml`: one `ci` job.
   - `requirements-dev.txt`: `ruff==0.17.1`, `pytest-cov==7.1.0`.
   - `pyproject.toml`: ruff E4/E7/E9/F, plus an E402 ignore for `cli.py`.
   - 7 unused imports removed.
   - `.dockerignore`: keeps `.env` and `venv/` out of images.
   - `.gitignore`: `build/`, `.coverage`.
3. **Q:** Why a separate venv for the CLI smoke test? **A:** So `requirements.txt` can't hide a missing package dependency.
4. **Commits:** `7ff7731` lint, `01b98ad` CI.

### A10: README
1. **PASS.** README updated; CI green.
2. **Changes:**
   - CI badge added; the stale "Tests 7/7" badge removed.
   - Mermaid diagram of the 7 nodes.
   - "Safety gate and its limits" section.
   - Eval table states its size.
   - Unmeasured claims dropped (naive-RAG baseline, ~73% MTTR, <12 s, 100% safety).
   - "10 scenarios", "BM25 rebuilt on cold start" and `edges.py` corrected.
3. **Q:** Why "3/3 on 4 scenarios" and not "100%"? **A:** A percentage on n=4 implies precision that isn't there.
4. **Commits:** one README commit.

### A7: tag-based PyPI release
1. **PARTIAL.** `release.yml` validated: YAML parses; the tag check allows `v1.0.1` and blocks `v1.2.0`; `python -m build` produces the sdist and wheel. The "tag → new PyPI version" step waits on section 3.
2. **Files:** `release.yml`. On `v*` tags it checks that the tag equals the `pyproject.toml` version, builds, then publishes via trusted publishing (OIDC, environment `pypi`, no stored token).
3. **Q:** Why trusted publishing? **A:** There's no long-lived token to leak; the per-run OIDC token expires in minutes.
4. **Commits:** one workflow commit.

### A8+A9: eval with 20 scenarios × 3 runs, unsafe output fails the run
1. **A9 PASS** (offline): the runner, run 2×2 through the real graph with a fake LLM that always proposes a destructive fix, gives `unsafe_fix_proposed_count` mean 2 and `unsafe_reached_output_count` max 0. **A8 PARTIAL:** `GEMINI_API_KEY` wasn't in the shell, so the real eval was not run and `eval_results.json` is still the old 4-scenario file.
2. **Files:**
   - `eval/run_eval.py`:
     - 8 known, 4 trap, 4 unknown and 4 unsafe-tempting scenarios.
     - Retrieval is scored on what the agent actually retrieved (before, it used a query built from the answer key and auto-hit the unknown case).
     - Escalation is checked against `should_escalate`.
     - `--runs` reports mean/min/max and median latency.
     - Exits 1 if any unsafe fix reaches output.
   - `tests/test_eval.py`: new.
   - `README.md`: states the size and that the set hasn't been run.
3. **Q:** Why report the min over runs? **A:** One run is one sample of a non-deterministic system. Safety-relevant numbers need the worst case.
4. **Commits:** `ed9aa54`.
- **stash@{0} vs new results for eval-003:** there are no new results. For reference, the stash has `keyword_match: false` (9.66 s) and the committed results have `true` (9.07 s).

## 2. Final numbers

| What | Value | Source |
|---|---|---|
| Tests | **48 passed, 1 xfailed** (49 collected) | CI run 38783449836 |
| Coverage of `app/` | **58%** (311 of 747 statements missed) | same run |
| Coverage of `app/` excluding `cli.py` | 74% (`cli.py` is 160 statements at 0%, exercised only by the CLI smoke test) | local, same suite |
| CI duration | about 2 min | runs on PRs #6–#9 |
| Safety patterns | 9 regexes; 30 parametrized tests + 1 documented bypass | `tests/test_safety.py` |
| Eval scenarios | **20** (8 known / 4 trap / 4 unknown / 4 unsafe) | `eval/run_eval.py` |
| Eval metrics, mean/min over 3 runs | **not measured**: the real eval was not run | needs your key (section 3) |
| Median latency | **not measured** for the 20-set. Old 4-scenario single run: 10.44 s | `eval/eval_results.json` |

## 3. Manual steps for you

### a. Turn on branch protection for `main` (require CI)
1. GitHub → `dhruvbadhe/AutoSRE` → **Settings** → **Rules** → **Rulesets** → **New ruleset** → **New branch ruleset**.
2. **Ruleset name:** `main`. **Enforcement status:** Active.
3. **Target branches** → **Add target** → **Include default branch**.
4. Tick **Restrict deletions** and **Block force pushes**.
5. Tick **Require a pull request before merging**. Set **Required approvals** to **0**: you're the only maintainer, and GitHub doesn't let you approve your own PR.
6. Tick **Require status checks to pass** → **Add checks** → type `ci` → choose the one from **GitHub Actions**. Optionally tick **Require branches to be up to date before merging**.
7. **Create.** To test it, `git push origin main` from a local commit should now be rejected.

### b. Set up the PyPI trusted publisher
1. pypi.org → log in → **Your projects** → `autosre-agent` → **Manage** → **Publishing**.
2. Under **Add a new publisher** → **GitHub**:
   - Owner `dhruvbadhe`
   - Repository `AutoSRE`
   - Workflow name `release.yml`
   - Environment name `pypi`
   - **Add**.
3. GitHub → repo **Settings** → **Environments** → **New environment** → name `pypi` → **Configure environment**.
4. Optional but recommended: tick **Required reviewers**, add yourself, and under **Deployment branches and tags** choose **Selected branches and tags** → **Add deployment branch or tag rule** → Ref type **Tag**, pattern `v*`.
5. Once a release has published, you can revoke any old PyPI API tokens under **Account settings** → **API tokens**.

### c. Cut a release later
1. Branch `chore/release-1.0.2`, then bump `version` in **both** `pyproject.toml` and `setup.py`. Open a PR and merge once CI is green.
2. Tag and push:
   ```bash
   git checkout main && git pull
   git tag v1.0.2 && git push origin v1.0.2
   ```
3. **Actions** → **Release**. If you set required reviewers, approve the `pypi` deployment.
4. Verify in a fresh venv: `pip install autosre-agent==1.0.2 && autosre --help`.
5. If the tag doesn't match the version, the build job fails before anything is published. Remove the tag with `git push --delete origin v1.0.2 && git tag -d v1.0.2`.

### d. Run the real eval (finishes A8)
1. `export GEMINI_API_KEY=...` in your shell. Use your own key and don't commit it.
2. Optional: the output node writes every triaged incident into the DB. To keep your local `incidents.db` clean, run against a copy: `cp incidents.db /tmp/eval.db && DATABASE_URL=sqlite:////tmp/eval.db python eval/run_eval.py --runs 3`.
3. Each run makes up to ~150 Gemini calls. Expect free-tier rate limiting.
4. On a branch: commit `eval/eval_results.json`, replace the README "Status: … has not been run yet" paragraph with the mean/min table, and mark A8 ✅ in the plan.
5. Compare eval-003 with the stash: `git show 'stash@{0}:eval/eval_results.json'`. Then `git stash drop stash@{0}` when you're done with it.

## 4. Resume bullets (only numbers from this run)

**AutoSRE: Incident Response Agent** (Python, LangGraph, FastAPI, ChromaDB, GitHub Actions, PyPI)
- Built and published `autosre-agent` to PyPI. It's a Typer CLI (`kubectl logs | autosre triage`) and FastAPI service running a 7-node LangGraph corrective-RAG pipeline that diagnoses alerts against past incidents and drafts runbook-based fixes.
- Unit tests showed the verification node returned `None` on its success path and that the "safety check" ran only in the offline eval. I moved a 9-pattern destructive-command gate into the runtime graph so unsafe fixes escalate at any confidence, covered by 30 parametrized tests plus a strict xfail that documents a known bypass.
- Made the 48-test suite run fully offline (fake LLM, embedder and web search; network blocked). I added ~2-minute GitHub Actions CI: ruff, pytest at 58% coverage, Docker build, and a CLI install smoke test. I also added a tag-triggered PyPI trusted-publishing workflow and a 20-scenario eval (known / trap / unknown / unsafe) that fails if any unsafe fix reaches output.

After you run the eval, add to bullet 3: "Recall@3 X% (min Y%) and escalation accuracy Z% over 3 runs; 0 unsafe fixes reached output."
Don't claim "hybrid BM25 + dense retrieval" for the running system yet (see finding 1).

## 5. Five likely interview questions

1. **"Walk me through the safety bug."** The eval reported 100% safe, but the check ran only in `eval/run_eval.py`, after the fact. At runtime, `verification_node` looked only at confidence, and on its success path it returned `None`, so nothing was written to state. I wrote failing tests first: high confidence must return "resolved", and an unsafe fix at 0.99 must escalate. Then I moved the patterns into `app/services/safety.py`, called it before the confidence check, and pointed the eval at the same module so the two can't drift apart.
2. **"A denylist is easy to bypass. Why ship it?"** It catches the common destructive commands an LLM writes in plain text, and it only decides *whether a human reviews* a fix. Nothing is executed. Quoting (`'r''m' -rf`), `$(...)`, variables and base64 all get past it, and a strict xfail keeps that visible. The next step is an allowlist of safe verbs (`get`, `describe`, `logs`, `rollout restart`) plus `kubectl --dry-run=server`.
3. **"How do you test an LLM pipeline in CI without calling the LLM?"** Set the config before import (dummy key, temp DB and Chroma). Replace the I/O at the point it's looked up: `llm.model`, the embedder instance, DuckDuckGo. Add a socket guard so a missed mock fails loudly and doesn't silently spend quota. Then run the *real* compiled graph with canned replies, so routing and gating are tested for real. The real LLM is used only in the eval, by hand, with a key.
4. **"How does the CRAG loop stop?"** The grader marks evidence sufficient or insufficient. `should_rewrite` sends the run back through the query rewriter only while it's insufficient *and* `iteration_count < 3`, and the grader increments the count. So the worst case is 2 rewrites, then a forced fix proposal. A test asserts exactly that. Honest caveat (finding 2): the rewriter's web results are overwritten by the next diagnosis step, so the loop currently retries retrieval but doesn't actually use the web snippets.
5. **"Why hybrid retrieval and RRF?"** Dense embeddings treat `HTTP 504` and `HTTP 502` as near neighbours, while BM25 keeps them as exact tokens. RRF fuses the two ranked lists by rank, `Σ w/(k + rank)` with k=60, so you never compare cosine scores with unbounded BM25 scores. Honest caveat (finding 1): BM25 is built only by the seed script, so a fresh API or CLI process is dense-only today. Knowing that is better than claiming it.

## Findings not fixed (outside the plan, or forbidden by its rules)

1. **BM25 is never built at runtime.** Only `seed_data.py` calls `add_incidents/add_runbooks`, so API, CLI and eval processes retrieve **dense-only**. The fix (rebuild from Chroma at startup) is a retrieval-logic change, so it wasn't touched. The README now says so.
2. **CRAG web results are discarded.** `query_rewriter_node` appends DuckDuckGo results, then the next `diagnose_node` overwrites `retrieved_similar_incidents` with fresh vector results, so the grader never sees them. Fixing it means changing node or graph logic.
3. The README's "Why httpx over the SDK (torch, 1.2 GB)" section contradicts `app/services/llm.py`, which uses `google-generativeai`. The package is also deprecated upstream.
4. The README has an MIT license badge, but the repo has **no `LICENSE` file**.
5. `setup.py` and `pyproject.toml` both hard-code the version. Bump both, or delete `setup.py`.
6. The README says the 70/30 dense/sparse weighting "was tuned on the eval suite". There's no tuning code or result in the repo.
7. Local `venv` is Python 3.9, which is end-of-life (google-auth warns). CI and Docker use 3.11.
8. `app/core/config.py` uses class-based `Config`, which pydantic v2 has deprecated.

## Process notes
- **Squash merges:** you asked for squash. On `main` each task is one commit, while the plan wanted the test commit and fix commit visible separately. The separate commits are kept on each PR's **Commits** tab (#2–#5).
- **Branch names:** CLAUDE.md says `fix/<task-id>-<short-name>`, one task per branch. As you instructed, A1+A2, A3+A4 and A8+A9 shared branches (each pair is one bug or feature), and the report branch is `docs/upgrade-report`.
- **Model switching:** the earlier plan to switch to Sonnet before A5 was replaced by your "autonomous run" instruction. Everything ran on Opus 5.5.
- **Ruff rule set:** ruff 0.17's defaults flagged 125 old style findings, so CI enforces E4/E7/E9/F (pyflakes plus pycodestyle errors). Widening it is a separate cleanup.
- **Pre-A5 test runs:** before A5, the local suite was run with `test_multi_index_separation` deselected, because that test called the real embedding API.
