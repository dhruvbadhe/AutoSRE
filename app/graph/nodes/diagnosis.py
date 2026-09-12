from app.graph.state import IncidentState
from app.services.vector_store import vector_store
from app.services.llm import generate_text

def diagnose_node(state: IncidentState) -> dict:
    parsed = state.get("parsed_incident", {})
    service = parsed.get("service", "")
    error_type = parsed.get("error_type", "")
    raw_logs = parsed.get("raw_logs", [])

    query = f"{service} {error_type}" + "".join(raw_logs[:3])
    retrieved_incidents = vector_store.search_incidents(query, top_k=3)

    historical_context = ""
    for idx, inc in enumerate(retrieved_incidents):
        doc = inc.get("document", "")
        meta = inc.get("metadata", {})
        historical_context += f"\n[Historical Incident {idx+1}]\nService: {meta.get('service')}\nError: {meta.get('error_type')}\nRoot Cause: {meta.get('root_cause')}\nDetails: {doc}\n"

        prompt = f"""You are a Principal Site Reliability Engineer (SRE).
Analyze the following active incident alert and raw logs against past verified post-mortems.
ACTIVE INCIDENT:
Service: {service}
Error Type: {error_type}
Raw Logs:
{chr(10).join(raw_logs[:5])}
HISTORICAL INCIDENT CONTEXT (from VectorDB):
{historical_context}
TASK:
State a concise, technical hypothesis (2-3 sentences) identifying:
1. The most probable root cause.
2. The specific subsystem or component failing.
3. The underlying mechanism (e.g. memory leak, deadlock, configuration drift).
Do not recommend fixes yet; focus strictly on root cause diagnosis."""
    hypothesis = generate_text(prompt).strip()
    reasoning_step = (
        f"Diagnosis Node: Queried incident vector index for '{service} {error_type}'. "
        f"Retrieved {len(retrieved_incidents)} matching historical incidents. "
        f"Formulated hypothesis: {hypothesis[:120]}..."
    )
    current_trace = state.get("reasoning_trace", [])
    updated_trace = current_trace + [reasoning_step]
    return {
        "retrieved_similar_incidents": retrieved_incidents,
        "hypothesis": hypothesis,
        "reasoning_trace": updated_trace
    }

