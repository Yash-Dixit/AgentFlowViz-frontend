import pandas as pd
import streamlit as st

from agentflowviz_client import api_get


WORKFLOW_LABELS = {
    "smart_task_router": "Smart Task Router",
    "image_document_router": "Image and Document Router",
    "research_to_report": "Research Report",
    "support_triage": "Support Triage",
    "orchestrated_task_router": "Orchestrated Router",
}


def fragment(run_every: str):
    if hasattr(st, "fragment"):
        return st.fragment(run_every=run_every)

    def decorator(func):
        return func

    return decorator


def show_api_error(result: dict) -> None:
    st.error(f"Backend request failed: {result.get('error', 'Unknown error')}")
    st.caption(result.get("url", ""))


def get_runs() -> list[dict]:
    result = api_get("/runs")
    if not result["ok"]:
        return []
    return result["data"]


def workflow_label(template_name: str | None) -> str:
    if not template_name:
        return "-"
    return WORKFLOW_LABELS.get(template_name, template_name.replace("_", " ").title())


def workflow_option_label(template: dict) -> str:
    status = "" if template.get("is_active", True) else " [Disabled]"
    return f"{workflow_label(template.get('name'))}{status} - {template.get('description', '')}"


def show_run_timeline(run_id: int) -> None:
    messages_result = api_get(f"/runs/{run_id}/messages")
    if not messages_result["ok"]:
        show_api_error(messages_result)
        return

    for message in messages_result["data"]:
        sender = message["sender"]
        avatar = "user" if "User" in sender else "assistant"
        with st.chat_message(avatar):
            st.caption(f"{sender} -> {message['recipient']} - {message['created_at']}")
            st.markdown(message["content"])


def show_run_metrics(run_id: int) -> None:
    metrics_result = api_get(f"/runs/{run_id}/metrics")
    if not metrics_result["ok"]:
        return

    metrics = metrics_result["data"]
    cols = st.columns(6)
    cols[0].metric("Messages", metrics["message_count"])
    cols[1].metric("Tool Calls", metrics["tool_call_count"])
    cols[2].metric("Tokens", metrics["total_tokens"])
    cols[3].metric("Tok/s", metrics["average_tokens_per_second"])
    cols[4].metric("Energy", f"{metrics.get('estimated_energy_kwh', 0):.8f} kWh")
    cols[5].metric("Cost", f"${metrics['local_cost_usd']:.6f}")

    if metrics.get("semantic_cache_hits") or metrics.get("saved_total_tokens"):
        saved_cols = st.columns(4)
        saved_cols[0].metric("Cache Hits", metrics.get("semantic_cache_hits", 0))
        saved_cols[1].metric("LLM Calls Saved", metrics.get("saved_model_calls", 0))
        saved_cols[2].metric("Prompt Tokens Saved", metrics.get("saved_prompt_tokens", 0))
        saved_cols[3].metric("Output Tokens Saved", metrics.get("saved_output_tokens", 0))


def show_run_tables(run_id: int) -> None:
    logs_result = api_get(f"/runs/{run_id}/logs")
    tools_result = api_get(f"/runs/{run_id}/tool-calls")
    attachments_result = api_get(f"/runs/{run_id}/attachments")

    if attachments_result["ok"] and attachments_result["data"]:
        st.subheader("Attachments")
        attachment_rows = []
        for row in attachments_result["data"]:
            attachment = row.get("attachment") or {}
            context = row.get("context") or {}
            attachment_rows.append(
                {
                    "filename": attachment.get("filename"),
                    "mime_type": attachment.get("mime_type"),
                    "file_size": attachment.get("file_size"),
                    "context_type": context.get("context_type"),
                    "summary": context.get("summary"),
                    "stored": attachment.get("object_key"),
                }
            )
        st.dataframe(pd.DataFrame(attachment_rows), width="stretch", hide_index=True)

    if logs_result["ok"] and logs_result["data"]:
        logs = pd.DataFrame(logs_result["data"])
        st.dataframe(logs, width="stretch", hide_index=True)
    else:
        st.info("No logs yet.")

    if tools_result["ok"] and tools_result["data"]:
        st.subheader("Tool Calls")
        tools = pd.DataFrame(tools_result["data"])
        st.dataframe(tools, width="stretch", hide_index=True)
