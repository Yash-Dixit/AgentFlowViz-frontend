import pandas as pd
import streamlit as st

from agentflowviz_client import DEFAULT_BACKEND_URL, api_get, api_post
from ui_helpers import (
    fragment,
    show_api_error,
    show_run_metrics,
    show_run_tables,
    show_run_timeline,
    workflow_label,
    workflow_option_label,
)


st.set_page_config(page_title="AgentFlowViz", page_icon="AF", layout="wide")

if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL
if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None

st.title("AgentFlowViz")
st.caption("Local Ollama-powered agent orchestration console")

with st.sidebar:
    st.text_input("Backend URL", key="backend_url")
    st.caption("Use the pages on the left for workflows, demo runs, monitoring, and settings.")

health = api_get("/health")
if not health["ok"]:
    show_api_error(health)
    st.stop()

health_data = health["data"]
ollama = health_data.get("ollama", {})

cols = st.columns(4)
cols[0].metric("Backend", health_data["status"])
cols[1].metric("Agents", health_data["agents"])
cols[2].metric("Templates", f"{health_data.get('active_templates', 0)}/{health_data['templates']} active")
cols[3].metric("Ollama", "online" if ollama.get("available") else "check")

telegram = health_data.get("telegram", {})
st.caption(
    f"Telegram: {'running' if telegram.get('running') else 'stopped'} - "
    f"{len(telegram.get('allowed_user_ids', []))} allowed user(s)"
)

defaults = health_data.get("defaults", {})
semantic_cache = health_data.get("semantic_cache", {})
conversation_memory = health_data.get("conversation_memory", {})
st.write(
    f"Default models: `{defaults.get('chat_model')}` for reasoning, "
    f"`{defaults.get('fast_model')}` for fast workers, "
    f"`{defaults.get('embedding_model')}` for memory."
)
st.caption(
    f"Semantic cache: {'enabled' if semantic_cache.get('enabled') else 'disabled'} - "
    f"{semantic_cache.get('entries', 0)} entrie(s) - "
    f"{semantic_cache.get('index', 'no index')} - "
    f"{semantic_cache.get('saved_model_calls', 0)} LLM call(s) saved - "
    f"{semantic_cache.get('saved_total_tokens', 0)} token(s) saved"
)
st.caption(
    "Conversation memory: "
    f"{conversation_memory.get('entries', 0)} user summary entrie(s) - "
    f"{conversation_memory.get('recent_runs', 0)} recent turn(s) injected"
)

st.divider()

templates_result = api_get("/workflows/templates")
templates = templates_result["data"] if templates_result["ok"] else []
active_templates = [template for template in templates if template.get("is_active", True)]

left, right = st.columns([0.9, 1.1])

with left:
    st.subheader("Start Demo Run")
    if not active_templates:
        st.info("No active workflows are available. Open Workflows to enable or create one.")
        submitted = False
        message = ""
        template_name = ""
    else:
        template_by_label = {workflow_option_label(template): template["name"] for template in active_templates}
        with st.form("demo_run_form"):
            selected_label = st.selectbox("Workflow", list(template_by_label.keys()))
            message = st.text_area(
                "Telegram-style user message",
                value="Route this: calculate 18 percent of 240 and explain the answer briefly.",
                height=120,
            )
            submitted = st.form_submit_button("Run Workflow")
        template_name = template_by_label[selected_label]

    if submitted:
        result = api_post("/runs/demo", json={"message": message, "template_name": template_name})
        if result["ok"]:
            st.session_state.current_run_id = result["data"]["id"]
            st.success(f"Started run #{st.session_state.current_run_id}")
            st.rerun()
        else:
            show_api_error(result)

with right:
    st.subheader("Recent Runs")
    runs_result = api_get("/runs")
    if runs_result["ok"] and runs_result["data"]:
        runs = pd.DataFrame(runs_result["data"])
        runs["workflow"] = runs["template_name"].map(workflow_label)
        st.dataframe(runs[["id", "workflow", "status", "started_at", "completed_at"]], hide_index=True)
    else:
        st.info("No runs yet.")


@fragment(run_every="1s")
def live_current_run() -> None:
    run_id = st.session_state.current_run_id
    if not run_id:
        return

    run_result = api_get(f"/runs/{run_id}")
    if not run_result["ok"]:
        show_api_error(run_result)
        return

    run = run_result["data"]
    st.divider()
    st.subheader(f"Live Run #{run_id}")
    status_cols = st.columns(3)
    status_cols[0].metric("Status", run["status"])
    status_cols[1].metric("Workflow", workflow_label(run["template_name"]))
    status_cols[2].metric("Local LLM Cost", "$0.00")

    show_run_metrics(run_id)
    show_run_timeline(run_id)
    with st.expander("Logs and tool calls", expanded=False):
        show_run_tables(run_id)


live_current_run()
