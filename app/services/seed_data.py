import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from app.services.vector_store import vector_store

def seed_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    incidents_path = os.path.join(base_dir, "data", "logs", "historical_incidents.json")
    runbooks_path = os.path.join(base_dir, "data", "runbooks", "sre_runbooks.json")
    with open(incidents_path, "r") as f:
        incidents = json.load(f)
    vector_store.add_incidents(incidents)
    with open(runbooks_path, "r") as f:
        runbooks = json.load(f)
    vector_store.add_runbooks(runbooks)
if __name__ == "__main__":
    seed_database()