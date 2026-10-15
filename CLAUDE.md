# AutoSRE: notes for Claude

- Test: `venv/bin/python -m pytest -q tests/`
- Lint: `ruff check .`
- Never call a real LLM, embedding API or network in tests or CI. Mock `generate_text` and `embedder`.
- Never edit prompts, retrieval logic, node order or graph edges (`app/graph/workflow.py`).
- One task per branch: `fix/<task-id>-<short-name>`. Never commit to `main`.
- Never write secrets. `.env` is local only; use `.env.example` placeholders.
