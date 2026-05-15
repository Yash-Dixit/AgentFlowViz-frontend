import streamlit as st

from agentflowviz_client import api_get, get_backend_url


TOOLS = [
    "local_research",
    "rss_rag_retriever",
    "calculator",
    "report_writer",
    "support_knowledge_lookup",
    "attachment_context_reader",
]
CHANNELS = ["telegram", "streamlit"]
SCHEDULES = ["manual", "hourly", "daily", "weekday_morning"]
CONTEXT_WINDOWS = ["short", "long", "large"]
SKILLS = [
    "intake",
    "channel_adapter",
    "planning",
    "task_decomposition",
    "research",
    "tool_execution",
    "rss_rag",
    "summarization",
    "final_response",
    "support_triage",
    "vision",
    "document_analysis",
    "attachment_context",
]


def options_with_existing(options: list[str], selected: list[str]) -> list[str]:
    merged = list(options)
    for value in selected:
        if value not in merged:
            merged.append(value)
    return merged


@st.cache_data(ttl=30, show_spinner=False)
def cached_model_names(backend_url: str) -> list[str]:
    models_result = api_get("/models")
    names = models_result.get("data", {}).get("models", []) if models_result["ok"] else []
    return names


def model_options(current_model: str | None = None) -> list[str]:
    names = cached_model_names(get_backend_url())
    if not names:
        names = ["gpt-oss:20b", "qwen3.5:9b"]
    if current_model and current_model not in names:
        names.append(current_model)
    return names


def normalize_agent(agent: dict) -> dict:
    agent.setdefault("name", "New Agent")
    agent.setdefault("role", "Worker Agent")
    agent.setdefault("system_prompt", "You are a concise local AI agent.")
    agent.setdefault("model", None)
    agent.setdefault("schedule", "manual")
    agent.setdefault("skills", [])
    agent.setdefault("tools", [])
    agent.setdefault("channels", [])
    agent.setdefault("interaction_rules", "")
    agent.setdefault("guardrails", "")
    agent.setdefault("limits", {})
    agent.setdefault("memory_enabled", True)
    return agent


def agent_payload(prefix: str, agent: dict | None = None) -> dict:
    agent = normalize_agent(dict(agent or {}))
    limits = agent.get("limits", {})
    current_model = agent.get("model") or "gpt-oss:20b"
    models = model_options(current_model)

    col_a, col_b = st.columns(2)
    name = col_a.text_input("Name", value=agent["name"], key=f"{prefix}_name")
    role = col_b.text_input("Role", value=agent["role"], key=f"{prefix}_role")

    model = st.selectbox(
        "Model",
        models,
        index=models.index(current_model),
        key=f"{prefix}_model",
    )
    system_prompt = st.text_area(
        "System prompt",
        value=agent["system_prompt"],
        height=120,
        key=f"{prefix}_system_prompt",
    )

    col_tools, col_channels = st.columns(2)
    tools = col_tools.multiselect(
        "Tools",
        options_with_existing(TOOLS, agent["tools"]),
        default=agent["tools"],
        key=f"{prefix}_tools",
    )
    channels = col_channels.multiselect(
        "Channels",
        options_with_existing(CHANNELS, agent["channels"]),
        default=agent["channels"],
        key=f"{prefix}_channels",
    )

    col_schedule, col_memory = st.columns(2)
    schedule_options = options_with_existing(SCHEDULES, [agent["schedule"]])
    schedule = col_schedule.selectbox(
        "Schedule",
        schedule_options,
        index=schedule_options.index(agent["schedule"]),
        key=f"{prefix}_schedule",
    )
    memory_enabled = col_memory.toggle("Memory enabled", value=agent["memory_enabled"], key=f"{prefix}_memory")

    skills = st.multiselect(
        "Skills",
        options_with_existing(SKILLS, agent["skills"]),
        default=agent["skills"],
        key=f"{prefix}_skills",
    )
    interaction_rules = st.text_area(
        "Interaction rules",
        value=agent["interaction_rules"] or "Ask for clarification when the request is ambiguous.",
        height=90,
        key=f"{prefix}_interaction_rules",
    )
    guardrails = st.text_input(
        "Guardrails",
        value=agent["guardrails"] or "Be concise, factual, and safe.",
        key=f"{prefix}_guardrails",
    )

    col_steps, col_tool_calls, col_output, col_context = st.columns(4)
    max_steps = col_steps.number_input(
        "Max steps",
        min_value=1,
        max_value=20,
        value=int(limits.get("max_steps", 4)),
        key=f"{prefix}_max_steps",
    )
    max_tool_calls = col_tool_calls.number_input(
        "Max tool calls",
        min_value=0,
        max_value=20,
        value=int(limits.get("max_tool_calls", 3)),
        key=f"{prefix}_max_tool_calls",
    )
    max_output_tokens = col_output.number_input(
        "Max output tokens",
        min_value=32,
        max_value=640,
        value=int(limits.get("max_output_tokens", 220)),
        key=f"{prefix}_max_output_tokens",
    )
    current_context_window = str(limits.get("context_window") or limits.get("context_profile") or "long")
    context_options = options_with_existing(CONTEXT_WINDOWS, [current_context_window])
    context_window = col_context.selectbox(
        "Context window",
        context_options,
        index=context_options.index(current_context_window),
        key=f"{prefix}_context_window",
    )

    return {
        "name": name,
        "role": role,
        "system_prompt": system_prompt,
        "model": model,
        "tools": tools,
        "channels": channels,
        "schedule": schedule,
        "skills": skills,
        "memory_enabled": memory_enabled,
        "interaction_rules": interaction_rules,
        "guardrails": guardrails,
        "limits": {
            "max_steps": int(max_steps),
            "max_tool_calls": int(max_tool_calls),
            "max_output_tokens": int(max_output_tokens),
            "context_window": context_window,
        },
    }
