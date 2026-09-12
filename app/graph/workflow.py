from langgraph.graph import StateGraph, END
from app.graph.state import IncidentState
from app.graph.nodes.ingestion import log_ingestion_node
from app.graph.nodes.diagnosis import diagnose_node
from app.graph.nodes.grader import grader_node
from app.graph.nodes.rewriter import query_rewriter_node
from app.graph.nodes.remediation import fix_proposal_node
from app.graph.nodes.verification import verification_node
from app.graph.nodes.output import output_node

def should_rewrite(state: IncidentState) -> str:
    retrieval_grade = state.get("retrieval_grade", "insufficient")
    iteration_count = state.get("iteration_count", 0)

    if retrieval_grade == "insufficient" and iteration_count < 3:
        return "rewrite"
    return "fix"

def create_incident_graph():
    workflow = StateGraph(IncidentState)

    workflow.add_node("log_ingestion", log_ingestion_node)
    workflow.add_node("diagnosis" , diagnose_node)
    workflow.add_node("grader" , grader_node)
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("fix_proposal", fix_proposal_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("log_ingestion")
    workflow.add_edge("log_ingestion", "diagnosis")
    workflow.add_edge("diagnosis", "grader")

    workflow.add_conditional_edges(
        "grader",
        should_rewrite,
        {
            "rewrite" : "query_rewriter",
            "fix": "fix_proposal"
        }
    )
    workflow.add_edge("query_rewriter", "diagnosis")
    workflow.add_edge("fix_proposal", "verification")
    workflow.add_edge("verification", "output")
    workflow.add_edge("output", END)

    return workflow.compile()

incident_graph = create_incident_graph()