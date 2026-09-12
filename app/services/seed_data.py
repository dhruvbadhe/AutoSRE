import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from app.core.database import engine, Base, SessionLocal
from app.models.db_models import Incident, Runbook
from app.services.vector_store import vector_store

def seed_database():
    Base.metadata.create_all(bind=engine)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    incidents_path = os.path.join(base_dir, "data", "logs", "historical_incidents.json")
    runbooks_path = os.path.join(base_dir, "data", "runbooks", "sre_runbooks.json")

    with open(incidents_path, "r") as f:
        incidents = json.load(f)
    vector_store.add_incidents(incidents)

    with open(runbooks_path, "r") as f:
        runbooks = json.load(f)
    vector_store.add_runbooks(runbooks)

    db = SessionLocal()
    try:
        for inc in incidents:
            existing = db.query(Incident).filter(Incident.id == inc["id"]).first()
            if not existing:
                db_incident = Incident(
                    id=inc["id"],
                    service=inc["service"],
                    severity=inc.get("severity", "MEDIUM"),
                    error_type=inc["error_type"],
                    status="RESOLVED",
                    raw_alert=inc.get("log_snippet", ""),
                    hypothesis=inc.get("root_cause", ""),
                    fix_confidence=1.0,
                    verification_result="resolved"
                )
                db.add(db_incident)

        for rb in runbooks:
            existing = db.query(Runbook).filter(Runbook.id == rb["id"]).first()
            if not existing:
                db_runbook = Runbook(
                    id=rb["id"],
                    title=rb["title"],
                    service=rb["service"],
                    procedure=rb["procedure"],
                    command_snippet=rb.get("command_snippet", "")
                )
                db.add(db_runbook)

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()