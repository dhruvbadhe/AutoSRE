import os
import sys
import typer
import httpx
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="autosre",
    help="⚡ AutoSRE - Autonomous Incident Response Agent CLI",
    add_completion=False
)
console = Console()

DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

PRESETS = {
    "oom": {
        "alert": "CRITICAL: auth-service pod OOMKilled in production namespace",
        "logs": [
            "2026-09-13T10:00:01Z [CRITICAL] auth-service java.lang.OutOfMemoryError: Java heap space",
            "2026-09-13T10:00:02Z [ERROR] Container terminated with ExitCode 137"
        ]
    },
    "db-pool": {
        "alert": "ALERT: order-service connection pool exhaustion database timeout",
        "logs": [
            "2026-09-13T10:15:30Z [ERROR] order-service TimeoutError: QueuePool limit of size 20 reached",
            "2026-09-13T10:15:35Z [CRITICAL] order-service unable to checkout connection from pool"
        ]
    },
    "dns": {
        "alert": "CRITICAL: billing-worker CoreDNS upstream lookup timeout failure",
        "logs": [
            "2026-09-13T11:00:10Z [ERROR] billing-worker Dial tcp: lookup payment.internal.svc on 10.96.0.10:53: i/o timeout",
            "2026-09-13T11:00:15Z [WARNING] billing-worker Retrying downstream payment dispatch"
        ]
    },
    "deadlock": {
        "alert": "ALERT: checkout-api downstream inventory deadlock 504 Gateway Timeout",
        "logs": [
            "2026-09-13T11:30:00Z [ERROR] checkout-api 504 Gateway Timeout from inventory-service",
            "2026-09-13T11:30:05Z [CRITICAL] checkout-api Thread pool exhausted waiting on DB locks"
        ]
    }
}

def execute_triage_direct(raw_alert: str, raw_logs: List[str]):
    from app.core.database import SessionLocal
    from app.models.db_models import Incident
    from app.graph.workflow import incident_graph

    initial_state = {
        "raw_alert": raw_alert,
        "raw_logs": raw_logs,
        "parsed_incident": {},
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
    service = parsed.get("service", "unknown-service")

    db = SessionLocal()
    try:
        if incident_id:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
        else:
            incident = db.query(Incident).filter(Incident.service == service).order_by(Incident.created_at.desc()).first()

        if incident:
            return {
                "id": incident.id,
                "service": incident.service,
                "severity": incident.severity,
                "status": incident.status,
                "hypothesis": incident.hypothesis,
                "proposed_fix": incident.proposed_fix,
                "fix_confidence": incident.fix_confidence,
                "post_mortem_draft": incident.post_mortem_draft,
                "audit_logs": [{"node_name": a.node_name, "decision_text": a.decision_text} for a in incident.audit_logs]
            }
    finally:
        db.close()

    return {
        "id": incident_id or "local-exec",
        "service": service,
        "severity": parsed.get("severity", "CRITICAL"),
        "status": "ESCALATED" if result.get("escalate") else "RESOLVED",
        "hypothesis": result.get("hypothesis", ""),
        "proposed_fix": result.get("proposed_fix", ""),
        "fix_confidence": result.get("fix_confidence", 0.0),
        "post_mortem_draft": result.get("post_mortem_draft", ""),
        "audit_logs": [{"node_name": "pipeline", "decision_text": trace} for trace in result.get("reasoning_trace", [])]
    }

@app.command()
def triage(
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Preset scenario: oom, db-pool, dns, deadlock"),
    alert: Optional[str] = typer.Option(None, "--alert", "-a", help="Raw infrastructure alert text"),
    logs: Optional[List[str]] = typer.Option(None, "--log", "-l", help="Log lines (can provide multiple times)"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="Backend API base URL (falls back to local execution)")
):
    """Run autonomous incident triage using Agentic Corrective RAG (CRAG)."""
    target_alert = alert
    target_logs = logs or []

    if preset:
        preset_key = preset.lower()
        if preset_key not in PRESETS:
            console.print(f"[bold red]Unknown preset '{preset}'. Available presets: {', '.join(PRESETS.keys())}[/bold red]")
            raise typer.Exit(code=1)
        target_alert = PRESETS[preset_key]["alert"]
        target_logs = PRESETS[preset_key]["logs"]

    if not target_alert:
        console.print("[bold yellow]No alert specified. Please provide --preset or --alert.[/bold yellow]")
        console.print("Example: [green]autosre triage --preset oom[/green]")
        raise typer.Exit(code=1)

    console.print(Panel.fit(
        f"[bold cyan]⚡ AutoSRE Autonomous Triage[/bold cyan]\n"
        f"[bold]Alert:[/bold] {target_alert}\n"
        f"[bold]Logs:[/bold] {len(target_logs)} line(s)",
        border_style="cyan"
    ))

    payload = {
        "raw_alert": target_alert,
        "raw_logs": target_logs
    }

    data = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task(description="[yellow]Executing 7-node LangGraph CRAG pipeline (Retrieval -> Diagnosis -> Verification)...[/yellow]", total=None)
        
        # Try REST API first
        try:
            with httpx.Client(timeout=240.0) as client:
                res = client.post(f"{api_url}/api/incidents/triage", json=payload)
                if res.status_code == 201:
                    data = res.json()
        except Exception:
            pass

        # If backend server is not running, run directly via local graph engine!
        if data is None:
            progress.update(task, description="[cyan]Server not active; executing directly via embedded LangGraph runtime...[/cyan]")
            try:
                data = execute_triage_direct(target_alert, target_logs)
            except Exception as e:
                console.print(f"[bold red]Triage execution failed: {e}[/bold red]")
                raise typer.Exit(code=1)

    incident_id = data.get("id")
    status = data.get("status")
    confidence = data.get("fix_confidence", 0.0)
    service = data.get("service")
    severity = data.get("severity")
    hypothesis = data.get("hypothesis", "")
    proposed_fix = data.get("proposed_fix", "")
    post_mortem = data.get("post_mortem_draft", "")
    audit_logs = data.get("audit_logs", [])

    table = Table(title=f"Incident Resolution Summary: {incident_id}", border_style="green")
    table.add_column("Field", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_row("Incident ID", str(incident_id))
    table.add_row("Service", str(service))
    table.add_row("Severity", f"[bold red]{severity}[/bold red]")
    table.add_row("Status", f"[bold green]{status}[/bold green]")
    table.add_row("CRAG Fix Confidence", f"{confidence:.2f} / 1.00")
    console.print(table)

    console.print(Panel(
        hypothesis,
        title="[bold yellow]Diagnostic Root Cause Hypothesis[/bold yellow]",
        border_style="yellow"
    ))

    if proposed_fix:
        console.print(Panel(
            proposed_fix,
            title="[bold green]Proposed Remediation & Runbook Actions[/bold green]",
            border_style="green"
        ))

    if audit_logs:
        trace_table = Table(title="Agentic Decision Audit Trace", border_style="magenta")
        trace_table.add_column("Step", style="bold")
        trace_table.add_column("Node", style="cyan")
        trace_table.add_column("Reasoning & Actions", style="white")
        for i, log in enumerate(audit_logs, 1):
            trace_table.add_row(f"#{i}", log.get("node_name", "graph"), log.get("decision_text", ""))
        console.print(trace_table)

    if post_mortem:
        console.print("\n[bold cyan]─── Post-Mortem Report ───[/bold cyan]")
        console.print(Markdown(post_mortem))

@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent incidents to fetch"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="Backend API base URL")
):
    """View historical incidents logged by AutoSRE."""
    incidents = []
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{api_url}/api/incidents/")
            if res.status_code == 200:
                incidents = res.json()
    except Exception:
        pass

    if not incidents:
        # Fall back to local SQLite DB directly!
        try:
            from app.core.database import SessionLocal
            from app.models.db_models import Incident
            db = SessionLocal()
            db_incs = db.query(Incident).order_by(Incident.created_at.desc()).limit(limit).all()
            incidents = [
                {
                    "id": inc.id,
                    "service": inc.service,
                    "severity": inc.severity,
                    "status": inc.status,
                    "fix_confidence": inc.fix_confidence,
                    "hypothesis": inc.hypothesis
                }
                for inc in db_incs
            ]
            db.close()
        except Exception:
            pass

    if not incidents:
        console.print("[yellow]No incidents recorded yet.[/yellow]")
        return

    table = Table(title=f"AutoSRE Incident Ledger (Top {min(limit, len(incidents))})", border_style="blue")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Service", style="bold white")
    table.add_column("Severity", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Hypothesis Summary", style="dim white")

    for inc in incidents[:limit]:
        hyp = inc.get("hypothesis") or "N/A"
        if len(hyp) > 60:
            hyp = hyp[:57] + "..."
        table.add_row(
            str(inc.get("id")),
            str(inc.get("service")),
            str(inc.get("severity")),
            str(inc.get("status")),
            f"{inc.get('fix_confidence', 0.0):.2f}",
            hyp
        )
    console.print(table)

@app.command()
def benchmark():
    """Run quantitative evaluation benchmark against curated incident scenarios."""
    console.print(Panel("[bold green]Starting AutoSRE Evaluation Benchmark Suite...[/bold green]", border_style="green"))
    import subprocess
    cmd = [sys.executable, "eval/run_eval.py"]
    subprocess.run(cmd)

if __name__ == "__main__":
    app()
