from typing import TypedDict, List, Dict, Any

class IncidentState(TypedDict):
    raw_alert: str
    raw_logs: List[str]
    parsed_incident: Dict[str, Any]
    retrieved_similar_incidents: List[Dict[str, Any]]
    hypothesis: str
    retrieval_grade: str
    retrieved_runbooks: List[Dict[str, Any]]
    proposed_fix: str
    fix_confidence: float
    verification_result: str
    escalate: bool
    reasoning_trace: List[str]
    post_mortem_draft: str
    iteration_count: int