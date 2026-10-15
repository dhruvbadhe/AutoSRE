from app.graph.nodes.verification import verification_node


def test_high_confidence_fix_is_resolved():
    output = verification_node({"proposed_fix": "kubectl rollout restart deployment/auth-service", "fix_confidence": 0.9})

    assert output["verification_result"] == "resolved"
    assert output["escalate"] is False
    assert output["reasoning_trace"][-1].startswith("Verification Node: Pre-flight check PASSED")


def test_low_confidence_fix_is_escalated():
    output = verification_node({"proposed_fix": "kubectl rollout restart deployment/auth-service", "fix_confidence": 0.3})

    assert output["verification_result"] == "unresolved"
    assert output["escalate"] is True


def test_unsafe_fix_is_escalated_even_with_high_confidence():
    output = verification_node({"proposed_fix": "Run: kubectl delete namespace production", "fix_confidence": 0.99})

    assert output["verification_result"] == "unresolved"
    assert output["escalate"] is True
