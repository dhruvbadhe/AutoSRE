# Incident Response Agent — Project Deep Dive

## What Problem Does This Actually Solve?

When a production system goes down, an on-call engineer gets paged at 2 AM. They have to:

1. Read the alert (e.g., "API latency spike", "Jenkins build failed", "Pod OOMKilled")
2. Dig through logs to find root cause
3. Search internal runbooks / Confluence / Slack history for "has this happened before?"
4. Apply a fix
5. Verify it worked
6. Write a post-mortem

This entire process takes 30–90 minutes on average, even for experienced engineers. Most of that time is **information retrieval + cross-referencing**, not actual fixing.

Your agent automates steps 1–4 and assists with step 6.

---

## What Your Agent Does (End-to-End Flow)

```
Alert Triggered (simulated webhook)
        ↓
  Log Ingestion Node
  - Parse raw logs (Nginx, Jenkins, CloudWatch format)
  - Extract: service name, error type, timestamp, severity
        ↓
  Diagnosis Node (RAG over log corpus)
  - Vector search: find similar past incidents
  - Retrieve top-k relevant log patterns
  - LLM generates hypothesis: "Likely OOM due to memory leak in auth-service"
        ↓
  Grader Node (CRAG-style self-correction)
  - "Is my retrieved context sufficient to confirm this hypothesis?"
  - If NO → trigger Retrieval Expansion Node
    - Search runbook RAG for this error type
    - Pull related service dependency context
  - If YES → proceed to Fix Proposal
        ↓
  Fix Proposal Node
  - RAG over runbook corpus: "What's the standard fix for this?"
  - LLM generates: step-by-step remediation plan with commands
        ↓
  Verification Node
  - Simulate fix applied → check if log pattern resolves
  - If unresolved → escalate flag = True, loop back with expanded context
        ↓
  Output Node
  - Structured incident report:
    → Root cause
    → Fix applied
    → Confidence score
    → Reasoning trace (every node's decision)
    → Post-mortem draft
```

---

## Why LangGraph Is Genuinely Necessary Here

Most RAG pipelines are linear: query → retrieve → generate. That's a chain, not a graph.

This agent needs **conditional branching and loops**:

- Grader node says "context insufficient" → loop back to retrieval with different query
- Verification node says "fix didn't work" → escalate branch, not terminate
- Multiple parallel retrievals (log corpus + runbook corpus simultaneously)

LangGraph's `StateGraph` with typed state, conditional edges, and cycle support handles all of this. A LangChain chain cannot.

---

## Tech Stack Breakdown

| Layer | Technology | Why |
|---|---|---|
| Agent Orchestration | LangGraph | Stateful multi-node graph with conditional edges |
| RAG - Log Corpus | Advanced RAG + VectorDB | Retrieve similar past incidents |
| RAG - Runbooks | Advanced RAG + VectorDB | Retrieve remediation steps |
| VectorDB | Qdrant or ChromaDB | Store log embeddings + runbook chunks |
| Embeddings | HuggingFace / OpenAI | Convert logs + docs to vectors |
| Backend | FastAPI | Webhook endpoint, agent trigger, result API |
| LLM | Groq API (Llama 3.1) | Fast inference, free tier sufficient |
| Frontend | Vibe-coded React UI | Show reasoning trace, incident timeline |
| Deployment | Docker + Render | Containerised, live demo |

---

## Advanced RAG — What Makes It "Advanced"

Standard RAG: embed query → cosine similarity → top-k chunks → generate.

Your project uses:

### 1. Hybrid Search
- Dense retrieval (semantic similarity via embeddings)
- Sparse retrieval (BM25 keyword match for exact error codes like `OOMKilled`, `500`, `SIGSEGV`)
- Reciprocal Rank Fusion to merge results

### 2. Re-ranking
- Retrieved chunks re-scored by a cross-encoder before passing to LLM
- Filters out semantically similar but contextually irrelevant logs

### 3. CRAG (Corrective RAG)
- Grader node evaluates retrieval quality
- If graded insufficient → reformulate query → retrieve again
- Prevents hallucinated root causes from low-quality retrieval

### 4. Multi-Index RAG
- Separate vector indices for logs vs runbooks
- Agent decides which index to query based on current node's need

---

## Data Sources (No Fake Data Needed)

### Public Log Datasets
- **Loghub** (GitHub) — 2 billion real log lines across 16 systems: HDFS, Hadoop, Spark, Linux, Apache, Nginx, Windows, Mac
- **Awesome Log Analysis** (GitHub) — curated list of public log datasets
- **Jenkins public build logs** — scrape from any public Jenkins instance

### Public Runbooks
- **Awesome Runbook** (GitHub) — collection of real DevOps runbooks
- **SRE Book by Google** (free online) — incident response procedures
- **PagerDuty Incident Response Docs** (public) — real runbook templates
- **Kubernetes official troubleshooting docs** — pod crash, OOM, network issues

You have enough public data to make this look real without needing production access.

---

## LangGraph State Design

```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph

class IncidentState(TypedDict):
    # Input
    raw_alert: str
    raw_logs: List[str]
    
    # Diagnosis
    parsed_incident: dict
    retrieved_similar_incidents: List[dict]
    hypothesis: str
    retrieval_grade: str  # "sufficient" | "insufficient"
    
    # Fix
    retrieved_runbooks: List[dict]
    proposed_fix: str
    fix_confidence: float
    
    # Verification
    verification_result: str  # "resolved" | "unresolved"
    escalate: bool
    
    # Output
    reasoning_trace: List[str]
    post_mortem_draft: str
    iteration_count: int  # prevent infinite loops
```

---

## FastAPI Backend Design

```
POST /webhook/alert        → Receives simulated PagerDuty/Grafana alert → triggers agent
GET  /incident/{id}        → Returns full incident report + reasoning trace
GET  /incidents            → List all processed incidents
POST /ingest/logs          → Upload log files to VectorDB
POST /ingest/runbooks      → Upload runbook docs to VectorDB
GET  /health               → System health
```

---

## What the UI Shows

This is where you differentiate from a script:

1. **Incident Feed** — list of alerts processed, status (resolved/escalated), confidence score
2. **Reasoning Trace Panel** — step-by-step: what each node retrieved, what it decided, why
3. **Fix Panel** — proposed remediation with exact runbook citations + line references
4. **Post-mortem Draft** — auto-generated, editable
5. **Confidence Timeline** — chart showing how agent's confidence evolved across iterations

The reasoning trace is the killer feature. It makes the agent's intelligence *visible* instead of being a black box.

---

## What Makes This Resume-Worthy

| Signal | What It Proves |
|---|---|
| LangGraph stateful graph | You understand agentic orchestration, not just chains |
| CRAG grader node | You know retrieval quality is a real problem, not just "RAG works" |
| Hybrid search + re-ranking | Production RAG knowledge beyond tutorials |
| FastAPI webhook + async | Backend engineering discipline |
| Real public log data | Not a toy demo |
| Reasoning trace UI | System design thinking — observability |
| Docker + Render deployment | Production discipline (already proven in SBA) |
| DevOps domain knowledge | You understand the logs you're parsing — unfakeable |

---

## Honest Risks

1. **LLM hallucinating root causes** — mitigate by making confidence scores prominent and never claiming the agent is 100% correct
2. **Log parsing complexity** — different log formats are messy; scope to 2-3 formats max (Nginx, Jenkins, generic syslog)
3. **Demo brittleness** — pre-select 3-4 incident scenarios that work reliably for demos; don't do live unknown inputs
4. **Scope creep** — auto-remediation (actually executing fixes) is tempting but out of scope; propose only, never execute

---

## Suggested Phased Build Plan (4 Weeks)

### Week 1 — Data + RAG Foundation
- Set up Qdrant locally + Docker
- Ingest Loghub datasets (HDFS + Nginx subset)
- Ingest public runbooks
- Build hybrid search (dense + BM25) with re-ranking
- Test retrieval quality manually

### Week 2 — LangGraph Agent
- Design StateGraph with all nodes
- Build: ingestion → diagnosis → grader → fix proposal → verification → output
- Implement CRAG loop with iteration cap
- Test on 5-10 synthetic incidents end-to-end

### Week 3 — FastAPI Backend
- Webhook endpoint + agent trigger
- Async job processing (agent runs in background)
- All REST endpoints
- Docker containerisation

### Week 4 — UI + Polish + Deployment
- Reasoning trace UI
- Incident feed + fix panel
- Deploy on Render
- Record demo video with 3 pre-selected incident scenarios
- Write README with architecture diagram
