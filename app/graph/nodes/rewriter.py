from duckduckgo_search import DDGS
from app.graph.state import IncidentState
from app.services.llm import generate_text

def query_rewriter_node(state: IncidentState) -> dict:
    parsed = state.get("parsed_incident", {})
    service = parsed.get("service", "")
    error_type = parsed.get("error_type", "")
    hypothesis = state.get("hypothesis", "")
    raw_logs = state.get("raw_logs", [])

    prompt = f"""You are a DevOps Search Optimization Specialist.
The initial vector search failed to find sufficient matching incident logs for this alert:
Service: {service}
Error: {error_type}
Hypothesis so far: {hypothesis}
Log line: {raw_logs[0] if raw_logs else ''}
Rewrite this into a concise search query (max 6-8 words) optimized to search technical documentation, GitHub issues, or StackOverflow for the exact failure mechanism.
Output ONLY the search query string, nothing else."""

    rewritten_query = generate_text(prompt).strip().replace("", '')

    web_results = []
    try:
        ddgs = DDGS()
        results = list(ddgs.text(rewritten_query, max_results=2))
        for res in results:
            web_results.append({
                "id": f"web-{len(web_results)+1}",
                "document": f"{res.get('title', '')}: {res.get('body', '')}",
                "metadata": {
                    "service": service,
                    "error_type": error_type,
                    "root_cause": res.get("body", "")[:120],
                    "source": res.get("href", "web")
                }
            })
    except Exception:
        web_results = []

    reasoning_step = (
        f"Query Rewriter Node (CRAG Fallback): Context was insufficient. "
        f"Formulated search query: '{rewritten_query}'. "
        f"Retrieved {len(web_results)} external reference snippets via DuckDuckGo."
    )
    current_trace = state.get("reasoning_trace", [])
    updated_trace = current_trace + [reasoning_step]

    existing_incidents = state.get("retrieved_similar_incidents", [])
    merged_incidents = existing_incidents + web_results

    return {
        "retrieved_similar_incidents": merged_incidents,
        "reasoning_trace": updated_trace
    }
