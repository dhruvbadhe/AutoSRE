from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers import incidents

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoSRE",
    description="Autonomous SRE Agent powered by Corrective RAG (CRAG) for root-cause diagnosis, runbook remediation, and post-mortem generation.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(incidents.router)

@app.get("/health", tags=["health"])
def health_check():
    return {
        "status" : "healthy",
        "service" : "AutoSRE",
        "orchestrator" : "LangGraph CRAG"
    }

