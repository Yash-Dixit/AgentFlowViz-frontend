import streamlit as st

from agentflowviz_client import DEFAULT_BACKEND_URL, api_get, api_post
from ui_helpers import show_api_error


st.set_page_config(page_title="Settings", page_icon="AF", layout="wide")
st.title("Settings")

if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL

st.text_input("Backend URL", key="backend_url")

health = api_get("/health")
if not health["ok"]:
    show_api_error(health)
    st.stop()

data = health["data"]
st.subheader("Backend")
st.json(
    {
        "status": data["status"],
        "database": data["database"],
        "agents": data["agents"],
        "templates": data["templates"],
        "active_templates": data.get("active_templates", 0),
        "defaults": data["defaults"],
        "semantic_cache": data.get("semantic_cache", {}),
        "conversation_memory": data.get("conversation_memory", {}),
        "context_window": data.get("context_window", {}),
        "attachments": data.get("attachments", {}),
        "final_output_guard": data.get("final_output_guard", {}),
        "local_energy_cost": data.get("local_energy_cost", {}),
        "rss_rag": data.get("rss_rag", {}),
    }
)

st.subheader("Ollama")
ollama = data.get("ollama", {})
if ollama.get("available"):
    st.success("Ollama is reachable.")
    st.write(ollama.get("models", []))
else:
    st.warning("Ollama is not reachable from the backend.")
    st.caption(ollama.get("error", "No error details returned."))

st.subheader("Telegram")
telegram = data.get("telegram", {})
cols = st.columns(4)
cols[0].metric("Configured", "yes" if telegram.get("configured") else "no")
cols[1].metric("Running", "yes" if telegram.get("running") else "no")
cols[2].metric("Setup Mode", "yes" if telegram.get("setup_mode") else "no")
cols[3].metric("Allowed Users", len(telegram.get("allowed_user_ids", [])))

diagnostics = telegram.get("diagnostics", {})
diag_cols = st.columns(4)
bot_username = diagnostics.get("bot_username") or "-"
diag_cols[0].metric("Bot", f"@{bot_username}" if bot_username != "-" else "-")
diag_cols[1].metric("Updates Seen", diagnostics.get("updates_received", 0))
diag_cols[2].metric("Last Action", diagnostics.get("last_action") or "-")
diag_cols[3].metric("Last Run", diagnostics.get("last_run_id") or "-")

semantic_cache = data.get("semantic_cache", {})
st.subheader("Semantic Cache Savings")
cache_cols = st.columns(4)
cache_cols[0].metric("Hits", semantic_cache.get("hits", 0))
cache_cols[1].metric("LLM Calls Saved", semantic_cache.get("saved_model_calls", 0))
cache_cols[2].metric("Prompt Tokens Saved", semantic_cache.get("saved_prompt_tokens", 0))
cache_cols[3].metric("Output Tokens Saved", semantic_cache.get("saved_output_tokens", 0))

rss_rag = data.get("rss_rag", {})
st.subheader("RSS RAG")
rss_cols = st.columns(4)
rss_cols[0].metric("Scheduler", "on" if rss_rag.get("scheduler", {}).get("running") else "off")
rss_cols[1].metric("Indexed Items", rss_rag.get("item_count", 0))
rss_cols[2].metric("Feeds", rss_rag.get("feed_count", 0))
rss_cols[3].metric("Top K", rss_rag.get("retrieval_limit", 0))
with st.expander("RSS RAG details"):
    st.json(rss_rag)

if telegram.get("allowed_user_ids"):
    st.write(telegram["allowed_user_ids"])
else:
    st.info("Send /whoami to your Telegram bot, then add your ID to TELEGRAM_ALLOWED_USER_IDS in the backend .env.")

if telegram.get("last_error"):
    st.warning(telegram["last_error"])

with st.expander("Telegram diagnostics"):
    st.json(diagnostics)

col_start, col_stop = st.columns(2)
if col_start.button("Start Telegram Bot"):
    result = api_post("/telegram/start")
    if result["ok"]:
        st.success(result["data"])
        st.rerun()
    else:
        show_api_error(result)

if col_stop.button("Stop Telegram Bot"):
    result = api_post("/telegram/stop")
    if result["ok"]:
        st.success(result["data"])
        st.rerun()
    else:
        show_api_error(result)
