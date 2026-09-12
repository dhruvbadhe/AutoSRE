from app.graph.state import IncidentState

def verification_node(state: IncidentState) -> dict:
    proposed_fix = state.get("proposed_fix", "")
    fix_confidence = state.get("fix_confidence", 0.0)

    if fix_confidence >= 0.60 and proposed_fix:
        verification_result = "resolved"
        escalate = False
        status_msg = "PASSED: Confidence threshold met (>=0.60). Ready for automated or approved execution."

    else:
        verification_result = "unresolved"
        escalate = True
        status_msg = "FAILED: Confidence below safety threshold (<0.60). Escalating to human on-call engineer."

        reasoning_step = f"Verification Node: Pre-flight check {status_msg}"
        current_trace = state.get("reasoning_trace" , [])
        updated_trace = current_trace + [reasoning_step]

        return {
            "verification_result": verification_result,
            "escalate": escalate,
            "reasoning_trace": updated_trace
        }