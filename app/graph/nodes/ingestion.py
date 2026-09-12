import re
from datetime import datetime
from app.graph.state import IncidentState

def log_ingestion_node(state: IncidentState) -> dict:
    raw_alert = state.get("raw_alert", "")
    raw_logs = state.get("raw_logs", [])
    combined_text = f"{raw_alert}" + " ".join(raw_logs)

    severity = "MEDIUM"
    if any(k in combined_text.upper() for k in ["CRITICAL", "FATAL", "EMERGENCY", "PANIC", "OOMKILLED"]):
        severity = "CRITICAL"
    elif any(k in combined_text.upper() for k in ["ERROR", "TIMEOUT", "504", "502", "500"]):
        severity = "HIGH"
    elif "WARN" in combined_text.upper():
        severity = "MEDIUM"

    service_match = re.search(r"\b([a-zA-Z0-9_\-]+(?:service|api|worker|db|cache)[a-zA-Z0-9_\-]*)\b", combined_text, re.IGNORECASE)
    service_name = service_match.group(1).lower() if service_match else "unknown-service"

    error_patterns = [
        r"(OOMKilled)",
        r"(OutOfMemoryError[^\n]*)",
        r"(TimeoutError[^\n]*)",
        r"(504 Gateway Timeout)",
        r"(CrashLoopBackOff)",
        r"(Connection refused)",
        r"(SIGSEGV)",
        r"(DatabaseConnectionTimeout)"
    ]

    error_type = "GenericApplicationError"
    for pat in error_patterns:
        match = re.search(pat, combined_text, re.IGNORECASE)
        if match:
            error_type = match.group(1)
            break
    parsed_incident = {
        "service": service_name,
        "severity": severity,
        "error_type": error_type,
        "timestamp": datetime.utcnow().isoformat(),
        "log_volume": len(raw_logs)
    }

    reasoning_step = (
        f"Log Ingestion Node: Ingested alert for '{service_name}' with severity '{severity}'. "
        f"Extracted error signature: '{error_type}' across {len(raw_logs)} log lines."
    )
    current_trace = state.get("reasoning_trace", [])
    updated_trace = current_trace + [reasoning_step]

    return {
        "parsed_incident": parsed_incident,
        "reasoning_trace": updated_trace,
        "iteration_count": 0
    }
