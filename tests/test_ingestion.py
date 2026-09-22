import pytest
from app.graph.nodes.ingestion import log_ingestion_node

def test_log_ingestion_parses_service_and_severity():
    state = {
        "raw_alert": "CRITICAL: auth-service pod OOMKilled in production namespace",
        "raw_logs": [
            "2026-09-22T10:00:01Z [CRITICAL] auth-service java.lang.OutOfMemoryError: Java heap space",
            "2026-09-22T10:00:02Z [ERROR] Container terminated with ExitCode 137"
        ]
    }
    output = log_ingestion_node(state)
    parsed = output.get("parsed_incident", {})
    
    assert parsed.get("service") == "auth-service"
    assert parsed.get("severity") == "CRITICAL"
    assert parsed.get("error_type") == "OOMKilled"
    assert parsed.get("log_volume") == 2
    assert output.get("iteration_count") == 0

def test_log_ingestion_fallback_for_unknown_format():
    state = {
        "raw_alert": "WARN: transient blip detected on unmapped component",
        "raw_logs": []
    }
    output = log_ingestion_node(state)
    parsed = output.get("parsed_incident", {})

    assert parsed.get("service") == "unknown-service"
    assert parsed.get("severity") == "MEDIUM"
    assert parsed.get("error_type") == "GenericApplicationError"