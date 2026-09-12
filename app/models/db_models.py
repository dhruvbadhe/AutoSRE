import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    service = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, default="MEDIUM")
    error_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="OPEN", index=True)
    raw_alert = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)
    proposed_fix = Column(Text, nullable=True)
    fix_confidence = Column(Float, nullable=True, default=0.0)
    verification_result = Column(String, nullable=True)
    post_mortem_draft = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    audit_logs = relationship("AgentAuditLog", back_populates="incident", cascade="all, delete-orphan")

class Runbook(Base):
    __tablename__ = "runbooks"

    id = Column(String, primary_key = True)
    title = Column(String, nullable=False)
    service = Column(String, nullable=False, index = True)
    procedure = Column(Text, nullable=False)
    command_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, index=True)
    node_name = Column(String, nullable=False)
    decision_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    incident = relationship("Incident", back_populates="audit_logs")