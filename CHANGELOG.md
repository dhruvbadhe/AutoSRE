# Changelog

All notable changes to `autosre-agent` are listed here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.2] - Unreleased (set the date when the `v1.0.2` tag is pushed)

### Fixed
- `GET /api/incidents/metrics` always returned HTTP 500: the handler's field names didn't match `MetricsResponse` (A0.5, #2).
- `verification_node` returned `None` when confidence was ≥ 0.60, so its result and escalation flag were never written to the graph state (A1–A2, #3).
- The destructive-command check ran only in the offline eval. It now runs inside `verification_node`, so a fix matching a destructive pattern is escalated to a human regardless of confidence (A3, #4).
- Hybrid retrieval was dense-only outside the seed script: the BM25 index is now rebuilt from ChromaDB whenever the vector store starts (API, CLI, eval). Fusion uses standard equal-weight RRF so exact error-string matches can reach the top results (B1, #11).
- Web-search results from the CRAG query rewriter were overwritten by the next diagnosis step; they now reach the grader (B2, #12).

### Added
- `app/services/safety.py`: one shared list of destructive-command patterns (`rm -rf`, `drop database/table`, `truncate`, `mkfs`, `dd if=/dev/zero`, fork bomb, `kubectl delete ns`, `scale --replicas=0`), matched after lowercasing and collapsing whitespace, with parametrized tests and a documented bypass (A3–A4, #4).
