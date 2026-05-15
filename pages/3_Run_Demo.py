import streamlit as st

from agentflowviz_client import api_get, api_post, api_post_multipart
from ui_helpers import (
    fragment,
    show_api_error,
    show_run_metrics,
    show_run_tables,
    show_run_timeline,
    workflow_label,
    workflow_option_label,
)


st.set_page_config(page_title="Run Demo", page_icon="AF", layout="wide")
st.title("Run Demo")

if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None

templates_result = api_get("/workflows/templates")
templates = templates_result["data"] if templates_result["ok"] else []
active_templates = [template for template in templates if template.get("is_active", True)]

if not active_templates:
    st.info("No active workflow templates are available. Enable or create one on the Workflows page.")
    st.stop()

template_by_label = {workflow_option_label(template): template["name"] for template in active_templates}
selected_label = st.selectbox("Workflow", list(template_by_label.keys()))
template_name = template_by_label[selected_label]
is_media_workflow = template_name == "image_document_router"

if is_media_workflow:
    with st.form("media_run_form", clear_on_submit=True):
        media_message = st.text_area(
            "Prompt",
            value="Analyze the uploaded file and summarize what matters.",
            height=90,
        )
        uploaded_files = st.file_uploader(
            "Images or documents",
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "webp", "gif", "pdf", "txt", "md", "csv", "json"],
        )
        start_media_run = st.form_submit_button("Run Image and Document Workflow", type="primary")

    if start_media_run:
        if not uploaded_files:
            st.error("Upload at least one image or document.")
        else:
            files = [
                (
                    "files",
                    (
                        file.name,
                        file.getvalue(),
                        file.type or "application/octet-stream",
                    ),
                )
                for file in uploaded_files
            ]
            result = api_post_multipart(
                "/runs/demo/attachments",
                data={"message": media_message, "template_name": template_name},
                files=files,
                timeout=90,
            )
            if result["ok"]:
                st.session_state.current_run_id = result["data"]["id"]
                st.rerun()
            else:
                show_api_error(result)
else:
    message = st.chat_input("Send a Telegram-style message to the intake agent")
    if message:
        result = api_post("/runs/demo", json={"message": message, "template_name": template_name})
        if result["ok"]:
            st.session_state.current_run_id = result["data"]["id"]
            st.rerun()
        else:
            show_api_error(result)

if not st.session_state.current_run_id:
    if is_media_workflow:
        st.info("Upload an image or document to start the media workflow.")
    else:
        st.info("Send a message to start the local multi-agent workflow.")


@fragment(run_every="1s")
def render_live_run() -> None:
    run_id = st.session_state.current_run_id
    if not run_id:
        return

    run_result = api_get(f"/runs/{run_id}")
    if not run_result["ok"]:
        show_api_error(run_result)
        return

    run = run_result["data"]
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Run", f"#{run_id}")
    col_b.metric("Status", run["status"])
    col_c.metric("Workflow", workflow_label(run["template_name"]))

    show_run_metrics(run_id)
    show_run_timeline(run_id)
    with st.expander("Logs and tools", expanded=True):
        show_run_tables(run_id)


render_live_run()
