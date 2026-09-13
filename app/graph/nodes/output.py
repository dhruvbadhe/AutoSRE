from datetime import datetime
from app.graph.state import IncidentState
from app.core.database import SessionLocal
from app.models.db_models import Incident, AgentAuditLog
from app.services.llm import generate_text

def output_node(state: IncidentState) -> dict:
    parsed = state.get("parsed_incident", {})
    service = parsed.get("service", "unknown-service")
    severity = parsed.get("severity", "MEDIUM")
    error_type = parsed.get("error_type", "Unknown")
    hypothesis = state.get("hypothesis", "")
    proposed_fix = state.get("proposed_fix", "")
    fix_confidence = state.get("fix_confidence", 0.0)
    verification_result = state.get("verification_result", "unresolved")
    escalate = state.get("escalate", False)
    reasoning_trace = state.get("reasoning_trace" , [])

    prompt = f"""You are an SRE Technical Writer drafting an automated incident post-mortem.
Service: {service}
Severity: {severity}
Error: {error_type}
Hypothesis: {hypothesis}
Proposed Mitigation: {proposed_fix}
Verification Status: {verification_result}
Escalated: {escalate}
Draft a concise, standardized post-mortem markdown report with the following sections:
## Incident Summary
## Root Cause Analysis
## Remediation Actions
## Preventative Recommendations
"""
    post_mortem = generate_text(prompt).strip()

    final_status = "ESCALATED" if escalate else "RESOLVED"
    incident_id = parsed.get("incident_id")

    db = SessionLocal()
    try:
        db_incident = None
        if incident_id:
            db_incident = db.query(Incident).filter(Incident.id == incident_id).first()

        if not db_incident:
            ingestion_time_str = parsed.get("timestamp")
            if ingestion_time_str:
                try:
                    incident_created_at = datetime.fromisoformat(ingestion_time_str)
                except Exception:
                    incident_created_at = datetime.utcnow()
            else:
                incident_created_at = datetime.utcnow()

            db_incident = Incident(
                service=service,
                severity=severity,
                error_type=error_type,
                raw_alert=state.get("raw_alert", ""),
                status=final_status,
                hypothesis=hypothesis,
                proposed_fix=proposed_fix,
                fix_confidence=fix_confidence,
                verification_result=verification_result,
                post_mortem_draft=post_mortem,
                created_at=incident_created_at,
                resolved_at=datetime.utcnow() if not escalate else None
            )
            db.add(db_incident)
            db.flush()
        else:
            db_incident.status = final_status
            db_incident.hypothesis = hypothesis
            db_incident.proposed_fix = proposed_fix
            db_incident.fix_confidence = fix_confidence
            db_incident.verification_result = verification_result
            db_incident.post_mortem_draft = post_mortem
            if not escalate:
                db_incident.resolved_at = datetime.utcnow()

        for step in reasoning_trace:
            audit = AgentAuditLog(
                incident_id=db_incident.id,
                node_name="graph_execution",
                decision_text=step
            )
            db.add(audit)
        db.commit()
        saved_incident_id = db_incident.id
    finally:
        db.close()

    reasoning_step = f"Output Node: Compiled post-mortem draft and committed incident status '{final_status}' to relational database."
    updated_trace = reasoning_trace + [reasoning_step]

    parsed["incident_id"] = saved_incident_id

    return {
        "parsed_incident": parsed,
        "post_mortem_draft": post_mortem,
        "reasoning_trace": updated_trace
    }
