from datetime import datetime

import pandas as pd
import streamlit as st

from ui_helpers import fragment, get_runs, show_run_metrics, show_run_tables, show_run_timeline, workflow_label


st.set_page_config(page_title="Monitoring", page_icon="AF", layout="wide")
st.title("Monitoring")


def format_timestamp(value: str | None) -> str:
    if not value:
        return "pending"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value.replace("T", " ")[:19]


def short_message(value: str, max_chars: int = 90) -> str:
    message = " ".join((value or "").split())
    if len(message) <= max_chars:
        return message
    return message[: max_chars - 3].rstrip() + "..."


def run_label(run: dict) -> str:
    user_id = run.get("telegram_user_id")
    user_label = f"tg:{user_id}" if user_id is not None else run.get("source_channel", "streamlit")
    return (
        f"#{run['id']} | {format_timestamp(run.get('started_at'))} | "
        f"{user_label} | {run['status']} | {workflow_label(run.get('template_name'))} | "
        f"{short_message(run.get('input_message', ''))}"
    )


def run_rows(run_items: list[dict]) -> list[dict]:
    return [
        {
            "run_id": run["id"],
            "started_at": format_timestamp(run.get("started_at")),
            "completed_at": format_timestamp(run.get("completed_at")),
            "telegram_user_id": str(run["telegram_user_id"]) if run.get("telegram_user_id") is not None else "-",
            "source": run.get("source_channel", "-"),
            "workflow": workflow_label(run.get("template_name")),
            "status": run.get("status", "-"),
            "message": short_message(run.get("input_message", ""), 140),
        }
        for run in run_items
    ]


runs = get_runs()
if not runs:
    st.info("No runs to monitor yet.")
    st.stop()

telegram_user_ids = sorted(
    {
        str(run["telegram_user_id"])
        for run in runs
        if run.get("source_channel") == "telegram" and run.get("telegram_user_id") is not None
    }
)
user_options = ["All runs", "Telegram runs"] + [f"Telegram user {user_id}" for user_id in telegram_user_ids]
selected_user_filter = st.selectbox("Telegram user filter", user_options)

if selected_user_filter == "Telegram runs":
    filtered_runs = [run for run in runs if run.get("source_channel") == "telegram"]
elif selected_user_filter.startswith("Telegram user "):
    selected_user_id = selected_user_filter.removeprefix("Telegram user ")
    filtered_runs = [run for run in runs if str(run.get("telegram_user_id")) == selected_user_id]
else:
    filtered_runs = runs

if not filtered_runs:
    st.info("No runs match this filter yet.")
    st.stop()

st.dataframe(pd.DataFrame(run_rows(filtered_runs)), width="stretch", hide_index=True)

run_lookup = {run_label(run): run["id"] for run in filtered_runs}
selected_label = st.selectbox("Message / run", list(run_lookup.keys()))
selected_run_id = run_lookup[selected_label]


@fragment(run_every="1s")
def live_monitor(run_id: int) -> None:
    show_run_metrics(run_id)
    tab_messages, tab_logs = st.tabs(["Messages", "Logs and Tools"])
    with tab_messages:
        show_run_timeline(run_id)
    with tab_logs:
        show_run_tables(run_id)


live_monitor(selected_run_id)
