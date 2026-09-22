from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.db_models import Incident, AgentAuditLog
from app.schemas.incident_schemas import (
    AlertIngestRequest,
    IncidentResponse,
    IncidentDetailResponse,
    MetricsResponse
)
from app.graph.workflow import incident_graph

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

@router.post("/triage", response_model=IncidentDetailResponse, status_code=status.HTTP_201_CREATED)
def trigger_incident_triage(
    payload: AlertIngestRequest,
    db: Session = Depends(get_db)
):
    initial_state = {
         "raw_alert": payload.raw_alert,
        "raw_logs": payload.raw_logs,
        "parsed_incident": {"service": payload.service} if payload.service else {},
        "retrieved_similar_incidents": [],
        "hypothesis": "",
        "retrieval_grade": "",
        "retrieved_runbooks": [],
        "proposed_fix": "",
        "fix_confidence": 0.0,
        "verification_result": "",
        "escalate": False,
        "reasoning_trace": [],
        "post_mortem_draft": "",
        "iteration_count": 0
    }

    result = incident_graph.invoke(initial_state)
    parsed = result.get("parsed_incident", {})
    incident_id = parsed.get("incident_id")
    service = parsed.get("service", payload.service or "unknown-service")

    if incident_id:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
    else:
        incident = db.query(Incident).filter(
            Incident.service == service
        ).order_by(Incident.created_at.desc()).first()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Incident was processed but record could not be retrieved from database."
        )
    return incident

@router.get("", response_model=List[IncidentResponse])
@router.get("/", response_model=List[IncidentResponse], include_in_schema=False)
def list_incidents(
    status_filter: Optional[str] = None,
    service_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter.upper())
    if service_filter:
        query = query.filter(Incident.service == service_filter)
    incidents = query.order_by(Incident.created_at.desc()).all()
    return incidents

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    total = db.query(Incident).count()
    resolved = db.query(Incident).filter(Incident.status == "RESOLVED").count()
    escalated = db.query(Incident).filter(Incident.status == "ESCALATED").count()

    incidents = db.query(Incident).filter(
        Incident.status == "RESOLVED",
        Incident.resolved_at.isnot(None)
    ).all()

    mttr_seconds = 0.0
    if incidents:
        deltas = [
            (inc.resolved_at - inc.created_at).total_seconds()
            for inc in incidents
            if inc.resolved_at and inc.created_at
        ]
        if deltas:
            mttr_seconds = sum(deltas) / len(deltas)

    return {
        "total_incidents": total,
        "resolved_incidents": resolved,
        "escalated_incidents": escalated,
        "mean_time_to_resolution_seconds": round(mttr_seconds, 2)
    }

@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(
    incident_id: str,
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found."
        )
    return incident
