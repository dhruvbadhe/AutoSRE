import json
from types import SimpleNamespace

from app.core.database import SessionLocal
from app.graph.nodes import grader, rewriter
from app.graph.workflow import incident_graph
from app.models.db_models import Incident

ALERT = {
    "raw_alert": "CRITICAL: auth-service pod OOMKilled in production namespace",
    "raw_logs": ["2026-09-22T10:00:01Z [CRITICAL] auth-service java.lang.OutOfMemoryError: Java heap space"],
}


def run_graph():
    result = incident_graph.invoke(dict(ALERT))
    db = SessionLocal()
    try:
        status = db.query(Incident).filter(Incident.id == result["parsed_incident"]["incident_id"]).one().status
    finally:
        db.close()
    return result, status


def test_safe_confident_fix_resolves_end_to_end():
    result, status = run_graph()

    assert result["verification_result"] == "resolved"
    assert result["escalate"] is False
    assert status == "RESOLVED"


def test_unsafe_fix_is_escalated_end_to_end(fake_llm):
    fake_llm["fix"] = json.dumps({"proposed_fix": "kubectl delete namespace production", "confidence": 0.99})

    result, status = run_graph()

    assert result["verification_result"] == "unresolved"
    assert result["escalate"] is True
    assert status == "ESCALATED"


def test_insufficient_evidence_takes_the_crag_rewrite_loop(fake_llm):
    fake_llm["grader"] = "INSUFFICIENT"

    result, _ = run_graph()

    assert result["iteration_count"] == 3
    assert sum("Query Rewriter Node" in step for step in result["reasoning_trace"]) == 2


def test_web_search_results_reach_the_grader(fake_llm, monkeypatch):
    fake_llm["grader"] = "INSUFFICIENT"
    web_hit = {"title": "Heap leak in JWT cache", "body": "WEB-SNIPPET-7731 bound the token cache", "href": "https://example.com/fix"}
    monkeypatch.setattr(rewriter, "DDGS", lambda: SimpleNamespace(text=lambda query, max_results: [web_hit]))
    grader_prompts = []
    real_generate = grader.generate_text
    monkeypatch.setattr(grader, "generate_text", lambda prompt: grader_prompts.append(prompt) or real_generate(prompt))

    run_graph()

    assert len(grader_prompts) == 3
    assert "WEB-SNIPPET-7731" not in grader_prompts[0]
    assert all("WEB-SNIPPET-7731" in prompt for prompt in grader_prompts[1:])
