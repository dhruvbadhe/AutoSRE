# AutoSRE upgrade report (2026-10-15, follow-up B1–B4 on 2026-10-16)

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
| Report | `docs/upgrade-report` | [#10](https://github.com/dhruvbadhe/AutoSRE/pull/10) | ✅ merged |
| B1 BM25 at startup + equal-weight RRF | `fix/B1-bm25-at-startup` | [#11](https://github.com/dhruvbadhe/AutoSRE/pull/11) | ✅ merged, CI green |
| B2 web results reach the grader | `fix/B2-web-fallback-kept` | [#12](https://github.com/dhruvbadhe/AutoSRE/pull/12) | ✅ merged, CI green |
| B3 CLI tests | `test/B3-cli-tests` | [#13](https://github.com/dhruvbadhe/AutoSRE/pull/13) | ✅ merged, CI green |
| B4 release prep 1.0.2 (no tag) | `chore/B4-release-1.0.2` | [#14](https://github.com/dhruvbadhe/AutoSRE/pull/14) | ✅ merged, CI green |
| Docs after B1–B4 | `docs/post-b-updates` | this PR | — |

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

### B1: hybrid retrieval was dense-only outside the seed script
1. **PASS.** A new `MultiIndexVectorStore` built over data already on disk must return a document that only BM25 can find (an exact error string; the embeddings put 3 decoys nearest). Before: `assert 'target' in ['decoy-1', 'decoy-2', 'decoy-3']` failed. After: `3 passed`. Checked against your real `chroma_db` (read-only, no API calls): a fresh process loads 5 incidents and 5 runbooks into BM25.
2. **Files:** `app/services/vector_store.py` and `tests/test_retrieval.py`.
   - BM25 is built from Chroma in `__init__`. `add_*` rebuild from the collection.
   - Sparse hits use the same id, document and metadata as dense hits.
   - Zero-score BM25 rows are dropped.
   - **RRF uses equal weights.** With 0.7/0.3, a BM25-only hit (≤ 0.3/61) always lost to the 3rd dense hit (≥ 0.7/63), so loading the index alone could not meet the done-check.
3. **Q:** What was actually wrong with "hybrid" retrieval? **A:** Two separate bugs. The index only existed in the seed process, and the fusion weights made lexical-only matches impossible to surface.
4. **Commits:** test `d5c80cf` → fix.

### B2: CRAG web-search results were discarded
1. **PASS.** The real graph runs with a fake LLM grading `INSUFFICIENT` and a fake DuckDuckGo hit; the test records every grader prompt. Before: the snippet never reached the grader. After: absent from grader call 1, present in calls 2 and 3. `4 passed`.
2. **Files:** `app/graph/nodes/diagnosis.py` now appends the `web-*` entries already in state after its fresh vector hits, where before it overwrote them. Prompt template, node order and edges are unchanged. The test is in `tests/test_graph.py`. Limit: the diagnosis prompt still uses vector hits only.
3. **Q:** How did the loop "work" yet do nothing? **A:** LangGraph replaces a key's value unless a reducer is declared, so the next node overwrote the rewriter's results.
4. **Commits:** test `4fa7f37` → fix `1aad10e`.

### B3: CLI tests
1. **PASS.** `tests/test_cli.py` gives `5 passed`. `app/cli.py` coverage went from 0% to 66%.
2. **Files:** `tests/test_cli.py`, using `CliRunner` and a fake `httpx.Client`. It covers:
   - `--help`;
   - piped stdin becoming the alert and logs (with an exact payload assert);
   - no alert → exit 1;
   - API down → local fallback succeeds;
   - API down plus local failure → exit 1 with `Triage execution failed: <cause>`.
3. **Q:** How do you test piped stdin? **A:** `CliRunner(input=...)` gives a non-TTY stdin, so the `isatty()` branch runs exactly as in a real pipe.
4. **Commits:** one test commit.

### B4: release prep 1.0.2
1. **PASS.**
   - `pyproject.toml` and `setup.py` are both at 1.0.2.
   - The tag check dry run allows `v1.0.2` and blocks `v1.0.1`.
   - `CHANGELOG.md` lists A0.5, A1–A4, B1 and B2.
   - **No tag pushed.**
2. **Files:** `pyproject.toml`, `setup.py`, `CHANGELOG.md`. `app/main.py`'s FastAPI `version="1.0.0"` is the API doc version and is left unchanged.
3. **Q:** Why a changelog when you have git? **A:** It's for users deciding whether to upgrade, grouped by version and linked to PRs.
4. **Commits:** one commit.

## 2. Final numbers

| What | Value | Source |
|---|---|---|
| Tests | **55 passed, 1 xfailed** (56 collected); was 48 + 1 before B1–B3 | CI run 38786741625 (PR #13); same count on #14 |
| Coverage of `app/` | **75%** (189 of 744 statements missed); was 58% | same run |
| Coverage of `app/cli.py` | 66% (was 0%) | local, same suite |
| Retrieval | Hybrid in every process: BM25 rebuilt from Chroma at startup, equal-weight RRF (k=60) | B1, `tests/test_retrieval.py` |
| Package version | 1.0.2 in `pyproject.toml` and `setup.py`, **not tagged or published** | B4 |
| CI duration | about 2 min | runs on PRs #6–#9 |
| Safety patterns | 9 regexes; 30 parametrized tests + 1 documented bypass | `tests/test_safety.py` |
| Eval scenarios | **20** (8 known / 4 trap / 4 unknown / 4 unsafe) | `eval/run_eval.py` |
| Eval metrics, mean/min over 3 runs | **not measured**: the real eval was not run | needs your key (section 3) |
| Median latency | **not measured** for the 20-set. Old 4-scenario single run: 10.44 s | `eval/eval_results.json` |

Note: while B1–B4 were in progress you started `eval/run_eval.py --runs 3` in the main working tree. It loaded the B1+B2 code at startup. Those results aren't in this report. Commit `eval/eval_results.json` from that run on its own branch (section 3d).

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
1. Version 1.0.2 is already bumped in both files and has a CHANGELOG entry (B4, #14). For later releases, bump **both** files on a `chore/release-x.y.z` branch and add a CHANGELOG section. In the CHANGELOG, replace "Unreleased" with the release date before tagging.
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
- Built and published `autosre-agent` to PyPI. It's a Typer CLI (`kubectl logs | autosre triage`) and FastAPI service running a 7-node LangGraph corrective-RAG pipeline over hybrid retrieval (BM25 + dense embeddings, reciprocal rank fusion) that diagnoses alerts against past incidents and drafts runbook-based fixes.
- Test-first debugging found 4 silent pipeline bugs, each fixed behind a regression test:
  - the verification node returned `None` on its success path;
  - the destructive-command check ran only in the offline eval (now a runtime gate with 9 patterns, 30 parametrized tests and a documented bypass);
  - BM25 was never built outside the seed script, and 0.7/0.3 RRF weights made BM25-only matches impossible to surface;
  - CRAG web-search results were overwritten before the grader saw them.
- Built a 55-test suite that runs fully offline (fake LLM, embedder and web search; network blocked) at 75% coverage, and GitHub Actions CI (~2 min): ruff, pytest, Docker build, CLI install smoke test. Added a tag-gated PyPI trusted-publishing release and a 20-scenario eval (known / trap / unknown / unsafe) over 3 runs that fails if any unsafe fix reaches output.

After you commit the eval results, add to bullet 3: "Recall@3 X% (min Y%) and escalation accuracy Z% over 3 runs; 0 unsafe fixes reached output." Until then, claim the eval's design, not its scores.

## 5. Five likely interview questions

1. **"Walk me through the safety bug."** The eval reported 100% safe, but the check ran only in `eval/run_eval.py`, after the fact. At runtime, `verification_node` looked only at confidence, and on its success path it returned `None`, so nothing was written to state. I wrote failing tests first: high confidence must return "resolved", and an unsafe fix at 0.99 must escalate. Then I moved the patterns into `app/services/safety.py`, called it before the confidence check, and pointed the eval at the same module so the two can't drift apart.
2. **"A denylist is easy to bypass. Why ship it?"** It catches the common destructive commands an LLM writes in plain text, and it only decides *whether a human reviews* a fix. Nothing is executed. Quoting (`'r''m' -rf`), `$(...)`, variables and base64 all get past it, and a strict xfail keeps that visible. The next step is an allowlist of safe verbs (`get`, `describe`, `logs`, `rollout restart`) plus `kubectl --dry-run=server`.
3. **"How do you test an LLM pipeline in CI without calling the LLM?"** Set the config before import (dummy key, temp DB and Chroma). Replace the I/O at the point it's looked up: `llm.model`, the embedder instance, DuckDuckGo. Add a socket guard so a missed mock fails loudly and doesn't silently spend quota. Then run the *real* compiled graph with canned replies, so routing and gating are tested for real. The real LLM is used only in the eval, by hand, with a key.
4. **"How does the CRAG loop stop?"** The grader marks evidence sufficient or insufficient. `should_rewrite` sends the run back through the query rewriter only while it's insufficient *and* `iteration_count < 3`, and the grader increments the count. So the worst case is 2 rewrites, then a forced fix proposal. A test asserts exactly that. Follow-up story (B2): the rewriter's web results used to be overwritten by the next diagnosis step, because LangGraph replaces a key's value unless it has a reducer. A test that records the grader's prompts caught it, and diagnosis now carries them forward.
5. **"Why hybrid retrieval and RRF?"** Dense embeddings treat `HTTP 504` and `HTTP 502` as near neighbours, while BM25 keeps them as exact tokens. RRF fuses the two ranked lists by rank, `Σ 1/(k + rank)` with k=60, so you never compare cosine scores with unbounded BM25 scores. Follow-up story (B1): it was dense-only in practice for two reasons. BM25 was built only by the seed script, and with 0.7/0.3 weights a BM25-only hit could never beat the 3rd dense hit. Both are fixed, with a test that builds a fresh store and proves an exact error string surfaces a document that dense search ranks last.

## Findings not fixed (outside the plan, or forbidden by its rules)

1. ~~BM25 is never built at runtime.~~ **Fixed in B1 (#11).**
2. ~~CRAG web results are discarded.~~ **Fixed in B2 (#12).** The diagnosis prompt still uses vector hits only, which is a possible follow-up.
3. The README's "Why httpx over the SDK (torch, 1.2 GB)" section contradicts `app/services/llm.py`, which uses `google-generativeai`. The package is also deprecated upstream.
4. The README has an MIT license badge, but the repo has **no `LICENSE` file**.
5. `setup.py` and `pyproject.toml` both hard-code the version (both are at 1.0.2 after B4). Bump both, or delete `setup.py`.
6. ~~70/30 weighting "tuned on the eval suite".~~ Replaced by equal-weight RRF in B1; the README now explains why.
9. The CLI's "API down" path silently falls back to local execution. If that also fails, the error names the local cause but not that the API was unreachable (B3 tests the current behaviour).
7. Local `venv` is Python 3.9, which is end-of-life (google-auth warns). CI and Docker use 3.11.
8. `app/core/config.py` uses class-based `Config`, which pydantic v2 has deprecated.

## Process notes
- **Squash merges:** you asked for squash. On `main` each task is one commit, while the plan wanted the test commit and fix commit visible separately. The separate commits are kept on each PR's **Commits** tab (#2–#5).
- **Branch names:** CLAUDE.md says `fix/<task-id>-<short-name>`, one task per branch. As you instructed, A1+A2, A3+A4 and A8+A9 shared branches (each pair is one bug or feature), and the report branch is `docs/upgrade-report`.
- **Model switching:** the earlier plan to switch to Sonnet before A5 was replaced by your "autonomous run" instruction. Everything ran on Opus 5.5.
- **Ruff rule set:** ruff 0.17's defaults flagged 125 old style findings, so CI enforces E4/E7/E9/F (pyflakes plus pycodestyle errors). Widening it is a separate cleanup.
- **B1–B4 working tree:** after B2 your working tree was switched to `main` and an eval run started there. To stay out of its way, B3, B4 and this docs pass were done in a separate git worktree, with files staged by explicit path, so the eval's `eval/eval_results.json` can't end up in these commits. `incidents_eval.db` wasn't touched.
- **Pre-A5 test runs:** before A5, the local suite was run with `test_multi_index_separation` deselected, because that test called the real embedding API.
