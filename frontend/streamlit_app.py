import os
import streamlit as st
import requests
import json

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Incident Response Agent",
    page_icon="🛡️",
    layout="wide"
)

st.title("Autonomous Incident Response Agent")
st.caption("Agentic Corrective RAG (CRAG) with Multi-Index Hybrid Search for Automated SRE Remediation")

def fetch_metrics():
    try:
        res = requests.get(f"{API_BASE_URL}/api/incidents/metrics", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def fetch_incidents():
    try:
        res = requests.get(f"{API_BASE_URL}/api/incidents", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def fetch_incident_detail(incident_id: str):
    try:
        res = requests.get(f"{API_BASE_URL}/api/incidents/{incident_id}", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

metrics = fetch_metrics()
if metrics:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Incidents", metrics.get("total_incidents", 0))
    c2.metric("Resolved", metrics.get("resolved_count", 0))
    c3.metric("Escalated", metrics.get("escalated_count", 0))
    c4.metric("Mean Time to Resolution (MTTR)", f"{metrics.get('mttr_seconds', 0.0)} s")

st.divider()

tab_trigger, tab_feed = st.tabs(["Trigger New Incident", "Incident Explorer & Audit Trace"])

with tab_trigger:
    st.subheader("Simulate Incoming Infrastructure Alert")
    
    presets = {
        "Custom Payload": ("", []),
        "Auth Service OOMKilled": (
            "CRITICAL: auth-service pod OOMKilled in production namespace",
            [
                "2026-09-13T10:00:01Z [CRITICAL] auth-service java.lang.OutOfMemoryError: Java heap space",
                "2026-09-13T10:00:02Z [ERROR] Container terminated with ExitCode 137"
            ]
        ),
        "Order Service Database Pool Exhaustion": (
            "CRITICAL: order-service PostgreSQL connection pool exhausted",
            [
                "2026-09-13T00:10:00Z [ERROR] order-service sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached",
                "2026-09-13T00:10:01Z [CRITICAL] order-service DatabaseConnectionTimeout: terminating connection due to administrator command"
            ]
        ),
        "Payment API Gateway Timeout (504)": (
            "HIGH: payment-api 504 Gateway Timeout downstream dependency failure",
            [
                "2026-09-13T11:00:00Z [WARN] payment-api upstream request latency > 3000ms",
                "2026-09-13T11:00:03Z [ERROR] payment-api 504 Gateway Timeout connecting to stripe-gateway-service"
            ]
        )
    }

    selected_preset = st.selectbox("Select Scenario Preset", list(presets.keys()))
    default_alert, default_logs = presets[selected_preset]

    alert_input = st.text_area("Raw Alert Payload", value=default_alert, height=70)
    logs_input = st.text_area(
        "Raw Container / Pod Logs (One log per line)",
        value="\n".join(default_logs),
        height=120
    )

    if st.button("Trigger Autonomous Triage", type="primary"):
        if not alert_input.strip():
            st.error("Please provide an alert payload.")
        else:
            raw_logs_list = [line.strip() for line in logs_input.strip().split("\n") if line.strip()]
            payload = {
                "raw_alert": alert_input.strip(),
                "raw_logs": raw_logs_list
            }

            with st.spinner("Agentic StateGraph executing (Ingestion -> Diagnosis -> CRAG Evaluation -> Runbook Retrieval -> Post-Mortem)..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/incidents/triage", json=payload, timeout=90)
                    if res.status_code == 201:
                        data = res.json()
                        st.success(f"Incident Triage Completed! Assigned ID: {data.get('id')}")
                        st.rerun()
                    else:
                        st.error(f"API Error ({res.status_code}): {res.text}")
                except requests.exceptions.Timeout:
                    st.error("Request timed out waiting for the LLM agentic pipeline.")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

with tab_feed:
    st.subheader("Historical Incidents & Agent Reasoning Traces")
    incidents_list = fetch_incidents()

    if not incidents_list:
        st.info("No incidents recorded yet. Trigger an alert from the tab above.")
    else:
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            incident_options = {
                f"[{inc['status']}] {inc['service']} - {inc['id']}": inc["id"]
                for inc in incidents_list
            }
            selected_label = st.radio("Select Incident", list(incident_options.keys()))
            selected_id = incident_options[selected_label]

        with col_detail:
            inc_detail = fetch_incident_detail(selected_id)
            if inc_detail:
                st.markdown(f"### Incident `{inc_detail.get('id')}`")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.write(f"**Service:** `{inc_detail.get('service')}`")
                m2.write(f"**Severity:** `{inc_detail.get('severity')}`")
                m3.write(f"**Status:** `{inc_detail.get('status')}`")
                confidence = inc_detail.get("fix_confidence") or 0.0
                m4.write(f"**Confidence:** `{confidence:.2f}`")

                st.markdown("#### Diagnostic Root Cause Hypothesis")
                st.info(inc_detail.get("hypothesis") or "No hypothesis formulated.")

                st.markdown("#### Proposed Remediation")
                proposed_code = inc_detail.get("proposed_fix") or ""
                st.code(proposed_code if proposed_code else "No fix generated.", language="bash")

                with st.expander("Step-by-Step Agent Audit Trace (LangGraph Decisions)", expanded=True):
                    audit_logs = inc_detail.get("audit_logs", [])
                    if audit_logs:
                        for step_idx, log in enumerate(audit_logs):
                            st.markdown(f"**Step {step_idx + 1}:** `{log.get('node_name')}`")
                            st.write(log.get("decision_text"))
                            st.caption(f"Timestamp: {log.get('timestamp')}")
                            st.divider()
                    else:
                        st.write("No audit trace records found.")

                with st.expander("Automated Post-Mortem Draft", expanded=False):
                    post_mortem_text = inc_detail.get("post_mortem_draft") or ""
                    st.markdown(post_mortem_text if post_mortem_text else "No post-mortem drafted.")