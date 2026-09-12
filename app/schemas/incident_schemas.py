from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class AlertIngestRequest(BaseModel):
    raw_alert: str = Field(..., description="Raw text or JSON string of the incoming alert")
    raw_logs: List[str] = Field(default_factory=list, description="List of raw log lines captured around the incident")
    service: Optional[str] = Field(None, description="Optional manual service name override")

class AuditLogResponse(BaseModel):
    node_name: str
    decision_text: str
    timestamp: datetime

    class Config:
        from_attributes = True

class IncidentResponse(BaseModel):
    id: str
    service: str
    severity: str
    error_type: str
    status: str
    raw_alert: Optional[str] = None
    hypothesis: Optional[str] = None
    proposed_fix: Optional[str] = None
    fix_confidence: Optional[float] = 0.0
    verification_result: Optional[str] = None
    post_mortem_draft : Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IncidentDetailResponse(IncidentResponse):
    audit_logs: List[AuditLogResponse] = []

class MetricsResponse(BaseModel):
    total_incidents: int
    resolved_count: int
    escalated_count: int
    open_count: int
    mttr_seconds: float

    