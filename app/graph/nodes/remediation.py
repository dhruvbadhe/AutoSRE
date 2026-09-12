import json
from app.graph.state import IncidentState
from app.services.llm import generate_text
from app.services.vector_store import vector_store

def fix_proposal_node(state: IncidentState) -> dict:
    parsed = state.get("parsed_incident", {})
    service = parsed.get("service", "")
    error_type = parsed.get("error_type", "")
    hypothesis = state.get("hypothesis", "")

    query = f"{service} {error_type} {hypothesis}"
    retrieved_runbooks = vector_store.search_runbooks(query=query, top_k=2)

    runbook_context = ""
    for idx, rb in enumerate(retrieved_runbooks):
        doc = rb.get("document", "")
        meta = rb.get("metadata", {})
        cmd = meta.get("command_snippet", "")
        runbook_context += f"\n [Runbook {idx+1}: {meta.get('title')}]\nProcedure: {doc}\nCommands: {cmd}\n"

        prompt = f"""You are a Lead Infrastructure Engineer formulating a precise incident remediation plan.
Target Service: {service}
Detected Error: {error_type}
Verified Hypothesis: {hypothesis}
Retrieved Standard Operating Procedures (Runbooks):
{runbook_context if runbook_context else "No direct runbook found in internal knowledge base."}
Formulate concrete, step-by-step remediation instructions. If commands are required (e.g., kubectl, systemctl, SQL), provide the exact shell commands.
Provide an estimated confidence score between 0.0 and 1.0 reflecting how well this proposed fix matches verified runbooks.
Respond in strict valid JSON format with keys:
- "proposed_fix": detailed remediation procedure and commands
- "confidence": float between 0.0 and 1.0
"""

    raw_response = generate_text(prompt).strip()
    if raw_response.startswith("```json"):
        raw_response = raw_response[7:]
    if raw_response.startswith("```"):
        raw_response = raw_response[3:]
    if raw_response.endswith("```"):
        raw_response = raw_response[:-3]

    try:
        parsed_data = json.loads(raw_response.strip())
        proposed_fix = parsed_data.get("proposed_fix", "")
        fix_confidence = float(parsed_data.get("confidence" , 0.75))
    except Exception:
        proposed_fix = raw_response
        fix_confidence = 0.50

    reasoning_step = (
        f"Fix Proposal Node: Queried runbook corpus for '{service}'. "
        f"Retrieved {len(retrieved_runbooks)} runbooks. "
        f"Proposed remediation with confidence score {fix_confidence:.2f}."
    )
    current_trace = state.get("reasoning_trace" , [])
    updated_trace = current_trace + [reasoning_step]

    return {
        "retrieved_runbooks": retrieved_runbooks,
        "proposed_fix": proposed_fix,
        "fix_confidence": fix_confidence,
        "reasoning_trace": updated_trace 
    }