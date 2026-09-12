from app.graph.state import IncidentState
from app.services.llm import generate_text

def grader_node(state: IncidentState) -> dict:
    hypothesis = state.get("hypothesis", "")
    retrieved_incidents = state.get("retrieved_similar_incidents", [])
    iteration_count = state.get("iteration_count", 0)

    context_summary = ""
    for idx, inc in enumerate(retrieved_incidents):
        meta = inc.get("metadata", {})
        context_summary += f"Past Case {idx+1}: {meta.get('service')} - {meta.get('error_type')}: {meta.get('root_cause')}\n"

    prompt = f"""You are a strict SRE Audit Grader evaluating the validity of a root-cause hypothesis.
PROPOSED HYPOTHESIS:
{hypothesis}
RETRIEVED HISTORICAL EVIDENCE:
{context_summary if context_summary else "No historical evidence retrieved."}
TASK:
Determine if the retrieved historical evidence directly supports and explains the hypothesis.
- If the evidence clearly identifies the failing mechanism, respond with: 'SUFFICIENT'
- If the evidence is generic, missing, or does not clearly validate the root cause, respond with: 'INSUFFICIENT'
Answer with ONLY one word: 'SUFFICIENT' or 'INSUFFICIENT'."""

    grade_response = generate_text(prompt).strip().upper()
    grade = "sufficient" if "SUFFICIENT" in grade_response and "INSUFFICIENT" not in grade_response else "insufficient"

    reasoning_step = (
        f"Grader Node (CRAG): Evaluated hypothesis grounding against retrieved evidence."
        f"Assigned grade: '{grade.upper()}'. Iteration count: {iteration_count+1}."
    )
    current_trace = state.get("reasoning_trace", [])
    updated_trace = current_trace + [reasoning_step]

    return {
        "retrieval_grade": grade,
        "iteration_count": iteration_count + 1,
        "reasoning_trace": updated_trace
    }