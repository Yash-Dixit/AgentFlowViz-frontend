import hashlib
import json
import re

import pandas as pd
import streamlit as st

from agentflowviz_client import api_delete, api_get, api_patch, api_post
from components.agent_form import agent_payload, normalize_agent
from components.workflow_canvas import (
    build_flow_state,
    flow_state_to_graph,
    graph_with_appended_edge,
    graph_with_appended_node,
    graph_with_renamed_node,
    graph_with_updated_edge,
    graph_without_edge,
    graph_without_node,
    normalize_edges,
    positions_for_nodes,
    render_workflow_canvas,
)
from ui_helpers import show_api_error, workflow_option_label


st.set_page_config(page_title="Workflows", page_icon="AF", layout="wide")
st.title("Workflows")


def load_templates() -> list[dict]:
    templates_result = api_get("/workflows/templates")
    if not templates_result["ok"]:
        show_api_error(templates_result)
        st.stop()
    return templates_result["data"]


def load_agents() -> list[dict]:
    agents_result = api_get("/agents")
    if not agents_result["ok"]:
        show_api_error(agents_result)
        st.stop()
    return [normalize_agent(agent) for agent in agents_result["data"]]


def save_template_graph(template_id: int, graph_payload: dict, signature_key: str, success_message: str) -> None:
    result = api_patch(f"/workflows/templates/{template_id}", json={"graph": graph_payload})
    if result["ok"]:
        st.success(success_message)
        st.session_state.pop(signature_key, None)
        st.rerun()
    else:
        show_api_error(result)


def workflow_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return key or "custom_workflow"


def starter_workflow_graph() -> dict:
    return {
        "nodes": [
            "Custom Intake",
            "Custom Orchestrator",
            "Primary Specialist",
            "Fallback Specialist",
            "Custom Response",
        ],
        "edges": [
            {"source": "Custom Intake", "target": "Custom Orchestrator", "condition": "always"},
            {"source": "Custom Orchestrator", "target": "Primary Specialist", "condition": "primary_route"},
            {"source": "Custom Orchestrator", "target": "Fallback Specialist", "condition": "fallback_route"},
            {"source": "Primary Specialist", "target": "Custom Response", "condition": "primary_done"},
            {"source": "Fallback Specialist", "target": "Custom Response", "condition": "fallback_done"},
            {
                "source": "Custom Response",
                "target": "Custom Orchestrator",
                "condition": "needs_revision",
                "feedback_loop": True,
            },
        ],
        "positions": {
            "Custom Intake": {"x": 0, "y": 180},
            "Custom Orchestrator": {"x": 260, "y": 180},
            "Primary Specialist": {"x": 540, "y": 100},
            "Fallback Specialist": {"x": 540, "y": 260},
            "Custom Response": {"x": 840, "y": 180},
        },
    }


def render_create_workflow() -> None:
    with st.expander("Create Workflow", expanded=False):
        with st.form("create_workflow_template"):
            new_name = st.text_input("Workflow key", value="custom_orchestrator")
            new_description = st.text_area(
                "Description",
                value="Custom orchestrator workflow with two selectable specialist branches.",
                height=80,
            )
            new_is_active = st.toggle("Enabled", value=True)
            create_workflow = st.form_submit_button("Create Workflow", type="primary")

        if create_workflow:
            payload = {
                "name": workflow_key(new_name),
                "description": new_description.strip() or "Custom orchestrated workflow.",
                "graph": starter_workflow_graph(),
                "is_active": new_is_active,
            }
            result = api_post("/workflows/templates", json=payload)
            if result["ok"]:
                st.success("Workflow created.")
                st.rerun()
            else:
                show_api_error(result)


def import_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def string_list(value, field_name: str) -> tuple[list[str] | None, str]:
    if value is None:
        return [], ""
    if not isinstance(value, list):
        return None, f"{field_name} must be a list."
    return [str(item).strip() for item in value if str(item).strip()], ""


def agent_payload_from_json(raw_agent: dict, index: int, node_names: set[str]) -> tuple[dict | None, str]:
    if not isinstance(raw_agent, dict):
        return None, f"agents row {index} must be an object."

    name = str(raw_agent.get("name", "")).strip()
    if not name:
        return None, f"agents row {index} must include a non-empty name."
    if name not in node_names:
        return None, f"agents row {index} name '{name}' is not listed in graph.nodes."

    tools, error = string_list(raw_agent.get("tools"), f"agents row {index} tools")
    if error:
        return None, error
    channels, error = string_list(raw_agent.get("channels"), f"agents row {index} channels")
    if error:
        return None, error
    skills, error = string_list(raw_agent.get("skills"), f"agents row {index} skills")
    if error:
        return None, error

    limits = raw_agent.get("limits") or {}
    if not isinstance(limits, dict):
        return None, f"agents row {index} limits must be an object."

    return (
        {
            "name": name,
            "role": str(raw_agent.get("role") or "Workflow Agent").strip(),
            "system_prompt": str(
                raw_agent.get("system_prompt") or f"You are the {name} agent in this workflow."
            ).strip(),
            "model": str(raw_agent.get("model") or "gpt-oss:20b").strip(),
            "tools": tools,
            "channels": channels,
            "schedule": str(raw_agent.get("schedule") or "manual").strip(),
            "skills": skills,
            "memory_enabled": import_bool(raw_agent.get("memory_enabled"), True),
            "interaction_rules": str(
                raw_agent.get("interaction_rules") or "Coordinate cleanly with the next workflow step."
            ).strip(),
            "guardrails": str(raw_agent.get("guardrails") or "Be concise, factual, and safe.").strip(),
            "limits": limits,
        },
        "",
    )


def workflow_payload_from_json(raw_value: str) -> tuple[dict | None, list[dict], str]:
    if not raw_value.strip():
        return None, [], "Paste a workflow JSON payload first."

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        return None, [], f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}."

    if not isinstance(payload, dict):
        return None, [], "Workflow JSON must be an object."

    raw_name = str(payload.get("name", "")).strip()
    if not raw_name:
        return None, [], "Workflow JSON must include a non-empty name."

    graph = payload.get("graph")
    if not isinstance(graph, dict):
        return None, [], "Workflow JSON must include a graph object."

    raw_nodes = graph.get("nodes", [])
    if not isinstance(raw_nodes, list):
        return None, [], "graph.nodes must be a list."

    nodes = []
    seen_nodes = set()
    for raw_node in raw_nodes:
        node_name = str(raw_node).strip()
        if node_name and node_name not in seen_nodes:
            nodes.append(node_name)
            seen_nodes.add(node_name)

    if not nodes:
        return None, [], "graph.nodes must contain at least one node name."

    raw_edges = graph.get("edges", [])
    if not isinstance(raw_edges, list):
        return None, [], "graph.edges must be a list."

    edges = []
    for index, raw_edge in enumerate(raw_edges, start=1):
        if not isinstance(raw_edge, dict):
            return None, [], f"graph.edges row {index} must be an object."
        source = str(raw_edge.get("source", "")).strip()
        target = str(raw_edge.get("target", "")).strip()
        if not source or not target:
            return None, [], f"graph.edges row {index} must include source and target."
        if source not in seen_nodes:
            return None, [], f"graph.edges row {index} source '{source}' is not listed in graph.nodes."
        if target not in seen_nodes:
            return None, [], f"graph.edges row {index} target '{target}' is not listed in graph.nodes."
        condition = str(raw_edge.get("condition") or "always").strip() or "always"
        edges.append(
            {
                "source": source,
                "target": target,
                "condition": condition,
                "feedback_loop": import_bool(raw_edge.get("feedback_loop"), False),
            }
        )

    positions = {}
    raw_positions = graph.get("positions", {})
    if isinstance(raw_positions, dict):
        for node_name in nodes:
            raw_position = raw_positions.get(node_name)
            if not isinstance(raw_position, dict):
                continue
            try:
                positions[node_name] = {
                    "x": float(raw_position.get("x", 0)),
                    "y": float(raw_position.get("y", 100)),
                }
            except (TypeError, ValueError):
                return None, [], f"Position for '{node_name}' must use numeric x and y values."

    raw_agents = payload.get("agents", [])
    if raw_agents is None:
        raw_agents = []
    if not isinstance(raw_agents, list):
        return None, [], "agents must be a list when provided."

    agent_payloads = []
    for index, raw_agent in enumerate(raw_agents, start=1):
        agent_payload, error = agent_payload_from_json(raw_agent, index, seen_nodes)
        if error or not agent_payload:
            return None, [], error or f"agents row {index} could not be parsed."
        agent_payloads.append(agent_payload)

    return (
        {
            "name": workflow_key(raw_name),
            "description": str(payload.get("description") or "Imported workflow.").strip(),
            "is_active": import_bool(payload.get("is_active"), True),
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "positions": positions,
            },
        },
        agent_payloads,
        "",
    )


def agent_json_for_editor(agent: dict) -> dict:
    return {
        "name": agent.get("name", ""),
        "role": agent.get("role", ""),
        "system_prompt": agent.get("system_prompt", ""),
        "model": agent.get("model", ""),
        "tools": agent.get("tools", []),
        "channels": agent.get("channels", []),
        "schedule": agent.get("schedule", "manual"),
        "skills": agent.get("skills", []),
        "memory_enabled": agent.get("memory_enabled", True),
        "interaction_rules": agent.get("interaction_rules", ""),
        "guardrails": agent.get("guardrails", ""),
        "limits": agent.get("limits", {}),
    }


def workflow_json_for_editor(template: dict, graph_payload: dict, agents_by_name: dict[str, dict]) -> str:
    payload = {
        "name": template["name"],
        "description": template.get("description", ""),
        "is_active": template.get("is_active", True),
        "graph": graph_payload,
        "agents": [
            agent_json_for_editor(agents_by_name[node_name])
            for node_name in graph_payload.get("nodes", [])
            if node_name in agents_by_name
        ],
    }
    return json.dumps(payload, indent=2)


def upsert_agent_payloads(agent_payloads: list[dict]) -> tuple[int, str]:
    if not agent_payloads:
        return 0, ""

    agents_result = api_get("/agents")
    if not agents_result["ok"]:
        return 0, agents_result["error"]

    existing_by_name = {agent["name"]: agent for agent in agents_result["data"]}
    saved_count = 0
    for payload in agent_payloads:
        existing = existing_by_name.get(payload["name"])
        if existing:
            result = api_patch(f"/agents/{existing['id']}", json=payload)
        else:
            result = api_post("/agents", json=payload)
        if not result["ok"]:
            return saved_count, f"Could not save agent '{payload['name']}': {result['error']}"
        saved_count += 1
    return saved_count, ""


def render_import_workflow_json() -> None:
    with st.expander("Paste Workflow JSON", expanded=False):
        st.caption(
            "Paste a full workflow-template JSON payload. If a workflow with the same key exists, "
            "you can update it in place."
        )
        with st.form("import_workflow_json"):
            raw_json = st.text_area(
                "Workflow JSON",
                value="",
                height=300,
                placeholder=(
                    '{"name": "my_router", "description": "...", "is_active": true, '
                    '"graph": {"nodes": [], "edges": []}}'
                ),
            )
            update_existing = st.checkbox("Update existing workflow with the same key", value=True)
            import_workflow = st.form_submit_button("Import Workflow JSON", type="primary")

        if not import_workflow:
            return

        payload, agent_payloads, error = workflow_payload_from_json(raw_json)
        if error or not payload:
            st.error(error or "Could not import workflow JSON.")
            return

        saved_agents, agent_error = upsert_agent_payloads(agent_payloads)
        if agent_error:
            st.error(agent_error)
            return

        templates_result = api_get("/workflows/templates")
        if not templates_result["ok"]:
            show_api_error(templates_result)
            return

        existing = next(
            (template for template in templates_result["data"] if template["name"] == payload["name"]),
            None,
        )
        if existing and not update_existing:
            st.error("A workflow with this key already exists. Enable update or change the JSON name.")
            return

        if existing:
            result = api_patch(f"/workflows/templates/{existing['id']}", json=payload)
            success_message = "Workflow JSON updated."
        else:
            result = api_post("/workflows/templates", json=payload)
            success_message = "Workflow JSON imported."

        if result["ok"]:
            if saved_agents:
                success_message = f"{success_message} Saved {saved_agents} agent config(s)."
            st.success(success_message)
            st.rerun()
        else:
            show_api_error(result)


def join_values(values: list | str | None) -> str:
    if isinstance(values, list):
        return ", ".join(str(value) for value in values) or "-"
    return str(values or "-")


def draft_agent_for_node(node_name: str) -> dict:
    return {
        "name": node_name,
        "role": "Workflow Agent",
        "system_prompt": f"You are the {node_name} agent in this workflow.",
        "model": "gpt-oss:20b",
        "tools": [],
        "channels": [],
        "schedule": "manual",
        "skills": [],
        "memory_enabled": True,
        "interaction_rules": "Coordinate cleanly with the next workflow step.",
        "guardrails": "Be concise, factual, and safe.",
        "limits": {"max_steps": 4, "max_tool_calls": 3, "max_output_tokens": 220, "context_window": "long"},
    }


def workflow_agent_rows(node_names: list[str], agents_by_name: dict[str, dict]) -> list[dict]:
    rows = []
    for node_name in node_names:
        agent = agents_by_name.get(node_name)
        if not agent:
            rows.append(
                {
                    "node": node_name,
                    "configured": "no",
                    "role": "-",
                    "model": "-",
                    "tools": "-",
                    "channels": "-",
                    "schedule": "-",
                    "memory": "-",
                    "skills": "-",
                    "limits": "-",
                }
            )
            continue

        limits = agent.get("limits", {})
        rows.append(
            {
                "node": node_name,
                "configured": "yes",
                "role": agent.get("role", "-"),
                "model": agent.get("model", "-"),
                "tools": join_values(agent.get("tools")),
                "channels": join_values(agent.get("channels")),
                "schedule": agent.get("schedule", "-"),
                "memory": "on" if agent.get("memory_enabled") else "off",
                "skills": join_values(agent.get("skills")),
                "limits": (
                    f"steps {limits.get('max_steps', '-')} / "
                    f"tools {limits.get('max_tool_calls', '-')} / "
                    f"tokens {limits.get('max_output_tokens', '-')} / "
                    f"context {limits.get('context_window', 'long')}"
                ),
            }
        )
    return rows


def workflow_edge_rows(edge_rows: list[dict], agents_by_name: dict[str, dict]) -> list[dict]:
    return [
        {
            "source": edge.get("source", ""),
            "target": edge.get("target", ""),
            "condition": edge.get("condition", "always"),
            "feedback_loop": bool(edge.get("feedback_loop", False)),
            "source_agent": "configured" if edge.get("source") in agents_by_name else "missing",
            "target_agent": "configured" if edge.get("target") in agents_by_name else "missing",
        }
        for edge in edge_rows
    ]


def copy_agent_name(agent_name: str, agents_by_name: dict[str, dict]) -> str:
    base_name = f"{agent_name} Copy"
    if base_name not in agents_by_name:
        return base_name

    counter = 2
    while f"{base_name} {counter}" in agents_by_name:
        counter += 1
    return f"{base_name} {counter}"


def edge_display(edge) -> str:
    return f"{edge.source} -> {edge.target} | {edge.label or 'always'}"


def build_inspector_options(flow_state) -> tuple[list[str], dict[str, str]]:
    values = ["overview"]
    labels = {"overview": "Overview"}
    for node in flow_state.nodes:
        value = f"node::{node.id}"
        values.append(value)
        labels[value] = f"Node: {node.id}"
    for edge in flow_state.edges:
        value = f"edge::{edge.id}"
        values.append(value)
        labels[value] = f"Edge: {edge_display(edge)}"
    return values, labels


def selected_canvas_value(flow_state) -> str | None:
    if not flow_state.selected_id:
        return None
    if any(node.id == flow_state.selected_id for node in flow_state.nodes):
        return f"node::{flow_state.selected_id}"
    if any(edge.id == flow_state.selected_id for edge in flow_state.edges):
        return f"edge::{flow_state.selected_id}"
    return None


def selected_node_from_value(flow_state, value: str):
    if not value.startswith("node::"):
        return None
    node_id = value.split("::", 1)[1]
    return next((node for node in flow_state.nodes if node.id == node_id), None)


def selected_edge_from_value(flow_state, value: str):
    if not value.startswith("edge::"):
        return None
    edge_id = value.split("::", 1)[1]
    return next((edge for edge in flow_state.edges if edge.id == edge_id), None)


if st.button("Seed Default Templates"):
    result = api_post("/workflows/templates/seed")
    if result["ok"]:
        st.success("Templates are ready.")
        st.rerun()
    else:
        show_api_error(result)

render_create_workflow()
render_import_workflow_json()

templates = load_templates()
if not templates:
    st.info("No workflow templates yet. Create one above or seed the two example templates.")
    st.stop()

template_by_label = {workflow_option_label(template): template for template in templates}
selected_label = st.selectbox("Workflow", list(template_by_label.keys()))
template = template_by_label[selected_label]
template_id = template["id"]
flow_key = f"workflow_flow_state_{template_id}"
graph_signature_key = f"workflow_graph_signature_{template_id}"
is_active = template.get("is_active", True)

st.subheader(selected_label.split(" - ", 1)[0])
st.write(template["description"])

status_cols = st.columns([0.18, 0.24, 0.26, 0.32])
status_cols[0].metric("Status", "Active" if is_active else "Disabled")

toggle_label = "Disable Workflow" if is_active else "Enable Workflow"
if status_cols[1].button(toggle_label, key=f"toggle_workflow_{template_id}"):
    result = api_patch(f"/workflows/templates/{template_id}", json={"is_active": not is_active})
    if result["ok"]:
        st.success("Workflow status updated.")
        st.rerun()
    else:
        show_api_error(result)

confirm_delete = status_cols[2].checkbox("Confirm delete", key=f"confirm_delete_{template_id}")
if status_cols[3].button(
    "Delete Workflow",
    key=f"delete_workflow_{template_id}",
    disabled=not confirm_delete,
):
    result = api_delete(f"/workflows/templates/{template_id}")
    if result["ok"]:
        st.session_state.pop(flow_key, None)
        st.session_state.pop(graph_signature_key, None)
        st.success("Workflow deleted.")
        st.rerun()
    else:
        show_api_error(result)

with st.expander("Workflow Settings", expanded=False):
    with st.form(f"workflow_settings_{template_id}"):
        edited_template_name = st.text_input("Workflow key", value=template["name"])
        edited_template_description = st.text_area("Description", value=template["description"], height=80)
        edited_template_active = st.toggle("Enabled", value=is_active)
        save_workflow_settings = st.form_submit_button("Save Workflow Settings", type="primary")

    if save_workflow_settings:
        payload = {
            "name": workflow_key(edited_template_name),
            "description": edited_template_description.strip() or "Custom orchestrated workflow.",
            "is_active": edited_template_active,
        }
        result = api_patch(f"/workflows/templates/{template_id}", json=payload)
        if result["ok"]:
            st.success("Workflow settings saved.")
            st.rerun()
        else:
            show_api_error(result)

graph = template.get("graph", {})
nodes = graph.get("nodes", [])
edges = graph.get("edges", [])
positions = graph.get("positions", {})
normalized_edges = normalize_edges(edges)

agents = load_agents()
agents_by_name = {agent["name"]: agent for agent in agents}

graph_signature = str(graph)
graph_digest = hashlib.sha1(graph_signature.encode("utf-8")).hexdigest()[:10]

if st.button(
    "Reset Canvas Layout",
    help="Restore the default node layout for the selected template.",
):
    st.session_state.pop(flow_key, None)
    st.session_state.pop(graph_signature_key, None)
    st.rerun()

if flow_key not in st.session_state or st.session_state.get(graph_signature_key) != graph_signature:
    st.session_state[flow_key] = build_flow_state(nodes, normalized_edges, positions)
    st.session_state[graph_signature_key] = graph_signature

canvas_col, inspector_col = st.columns([0.62, 0.38])

with canvas_col:
    st.subheader("Drag-and-Drop Canvas")
    st.session_state[flow_key] = render_workflow_canvas(
        f"workflow_canvas_{template_id}",
        st.session_state[flow_key],
    )

    if st.button(
        "Save Canvas",
        type="primary",
        help="Persist the current canvas positions and connections.",
    ):
        graph_from_canvas = flow_state_to_graph(st.session_state[flow_key], normalized_edges)
        save_template_graph(template_id, graph_from_canvas, graph_signature_key, "Canvas saved.")

with inspector_col:
    st.subheader("Inspector")
    current_flow_state = st.session_state[flow_key]
    selection_values, selection_labels = build_inspector_options(current_flow_state)
    inspector_selection_key = f"workflow_inspector_selection_{template_id}"
    last_canvas_selection_key = f"{inspector_selection_key}_last_canvas"
    canvas_selection = selected_canvas_value(current_flow_state)

    if canvas_selection and st.session_state.get(last_canvas_selection_key) != canvas_selection:
        st.session_state[inspector_selection_key] = canvas_selection
        st.session_state[last_canvas_selection_key] = canvas_selection
    if st.session_state.get(inspector_selection_key) not in selection_values:
        st.session_state[inspector_selection_key] = "overview"

    selected_value = st.selectbox(
        "Edit",
        selection_values,
        format_func=lambda value: selection_labels.get(value, value),
        key=inspector_selection_key,
    )
    node = selected_node_from_value(current_flow_state, selected_value)
    edge = selected_edge_from_value(current_flow_state, selected_value)

    if node:
        node_names = [flow_node.id for flow_node in current_flow_state.nodes]
        agent = agents_by_name.get(node.id)
        if agent:
            st.markdown(f"**Node:** `{node.id}`")
            with st.form(f"workflow_edit_agent_{template_id}_{agent['id']}"):
                edited_payload = agent_payload(f"workflow_edit_{template_id}_{agent['id']}", agent)
                save_agent = st.form_submit_button("Save Agent And Node", type="primary")

            if save_agent:
                new_name = edited_payload["name"].strip()
                duplicate_node = new_name != node.id and new_name in node_names
                duplicate_agent = new_name != agent["name"] and new_name in agents_by_name
                if not new_name:
                    st.error("Node name is required.")
                elif duplicate_node:
                    st.error("Another node already uses that name.")
                elif duplicate_agent:
                    st.error("Another agent already uses that name.")
                else:
                    edited_payload["name"] = new_name
                    result = api_patch(f"/agents/{agent['id']}", json=edited_payload)
                    if result["ok"]:
                        updated_graph = graph_with_renamed_node(
                            current_flow_state,
                            normalized_edges,
                            node.id,
                            new_name,
                        )
                        save_template_graph(
                            template_id,
                            updated_graph,
                            graph_signature_key,
                            "Agent and workflow node saved.",
                        )
                    else:
                        show_api_error(result)
        else:
            draft_agent = draft_agent_for_node(node.id)
            st.markdown(f"**Node:** `{node.id}`")
            with st.form(f"workflow_create_agent_{template_id}_{node.id}"):
                new_payload = agent_payload(f"workflow_create_{template_id}_{node.id}", draft_agent)
                create_agent = st.form_submit_button("Create Agent", type="primary")

            if create_agent:
                new_name = new_payload["name"].strip()
                duplicate_node = new_name != node.id and new_name in node_names
                duplicate_agent = new_name in agents_by_name
                if not new_name:
                    st.error("Node name is required.")
                elif duplicate_node:
                    st.error("Another node already uses that name.")
                elif duplicate_agent:
                    st.error("Another agent already uses that name.")
                else:
                    new_payload["name"] = new_name
                    result = api_post("/agents", json=new_payload)
                    if result["ok"]:
                        updated_graph = graph_with_renamed_node(
                            current_flow_state,
                            normalized_edges,
                            node.id,
                            new_name,
                        )
                        save_template_graph(
                            template_id,
                            updated_graph,
                            graph_signature_key,
                            "Agent created and workflow node saved.",
                        )
                    else:
                        show_api_error(result)

        if agents:
            with st.form(f"workflow_attach_agent_{template_id}_{node.id}"):
                current_index = next(
                    (index for index, existing_agent in enumerate(agents) if existing_agent["name"] == node.id),
                    0,
                )
                attached_agent_name = st.selectbox(
                    "Attach existing agent",
                    [existing_agent["name"] for existing_agent in agents],
                    index=current_index,
                    key=f"attach_existing_agent_{template_id}_{node.id}",
                )
                attach_agent = st.form_submit_button("Attach Agent To Node")

            if attach_agent:
                duplicate_node = attached_agent_name != node.id and attached_agent_name in node_names
                if duplicate_node:
                    st.error("Another node already uses that agent name.")
                else:
                    updated_graph = graph_with_renamed_node(
                        current_flow_state,
                        normalized_edges,
                        node.id,
                        attached_agent_name,
                    )
                    save_template_graph(template_id, updated_graph, graph_signature_key, "Agent attached to node.")

        if st.button("Delete Node", key=f"delete_node_{template_id}_{node.id}"):
            updated_graph = graph_without_node(current_flow_state, normalized_edges, node.id)
            save_template_graph(template_id, updated_graph, graph_signature_key, "Node deleted.")
    elif edge:
        node_names = [flow_node.id for flow_node in current_flow_state.nodes]
        source_options = list(dict.fromkeys(node_names + [edge.source]))
        target_options = list(dict.fromkeys(node_names + [edge.target]))
        current_feedback = next(
            (
                bool(row.get("feedback_loop", False))
                for row in normalized_edges
                if row.get("source") == edge.source
                and row.get("target") == edge.target
                and (row.get("condition") or "always") == (edge.label or "always")
            ),
            bool(edge.animated),
        )

        st.markdown(f"**Edge:** `{edge.source}` -> `{edge.target}`")
        with st.form(f"workflow_edit_edge_{template_id}_{edge.id}"):
            source = st.selectbox(
                "Source",
                source_options,
                index=source_options.index(edge.source),
                key=f"edge_source_{template_id}_{edge.id}",
            )
            target = st.selectbox(
                "Target",
                target_options,
                index=target_options.index(edge.target),
                key=f"edge_target_{template_id}_{edge.id}",
            )
            condition = st.text_input(
                "Condition",
                value=edge.label or "always",
                key=f"edge_condition_{template_id}_{edge.id}",
            )
            feedback_loop = st.toggle(
                "Feedback loop",
                value=current_feedback,
                key=f"edge_feedback_{template_id}_{edge.id}",
            )
            save_edge = st.form_submit_button("Save Edge", type="primary")

        if save_edge:
            updated_graph = graph_with_updated_edge(
                current_flow_state,
                normalized_edges,
                edge.id,
                source,
                target,
                condition,
                feedback_loop,
            )
            save_template_graph(template_id, updated_graph, graph_signature_key, "Edge saved.")

        if st.button("Delete Edge", key=f"delete_edge_{template_id}_{edge.id}"):
            updated_graph = graph_without_edge(current_flow_state, normalized_edges, edge.id)
            save_template_graph(template_id, updated_graph, graph_signature_key, "Edge deleted.")
    else:
        metric_cols = st.columns(2)
        metric_cols[0].metric("Nodes", len(current_flow_state.nodes))
        metric_cols[1].metric("Edges", len(current_flow_state.edges))
        node_names = [flow_node.id for flow_node in current_flow_state.nodes]

        if agents:
            with st.form(f"workflow_add_existing_agent_{template_id}"):
                existing_agent_name = st.selectbox(
                    "Existing agent",
                    [agent["name"] for agent in agents],
                    key=f"existing_agent_{template_id}",
                )
                add_existing = st.form_submit_button("Add Agent Node")

            if add_existing:
                updated_graph = graph_with_appended_node(current_flow_state, normalized_edges, existing_agent_name)
                save_template_graph(template_id, updated_graph, graph_signature_key, "Agent node added.")

        if len(node_names) >= 2:
            with st.form(f"workflow_add_edge_{template_id}"):
                source = st.selectbox("Source", node_names, key=f"add_edge_source_{template_id}")
                target = st.selectbox(
                    "Target",
                    node_names,
                    index=1 if len(node_names) > 1 else 0,
                    key=f"add_edge_target_{template_id}",
                )
                condition = st.text_input("Condition", value="always", key=f"add_edge_condition_{template_id}")
                feedback_loop = st.toggle("Feedback loop", value=False, key=f"add_edge_feedback_{template_id}")
                add_edge = st.form_submit_button("Add Edge")

            if add_edge:
                if source == target:
                    st.error("Choose two different nodes for an edge.")
                else:
                    updated_graph = graph_with_appended_edge(
                        current_flow_state,
                        normalized_edges,
                        source,
                        target,
                        condition,
                        feedback_loop,
                    )
                    save_template_graph(template_id, updated_graph, graph_signature_key, "Edge added.")

        with st.expander("Create Agent Node", expanded=False):
            with st.form(f"workflow_add_new_agent_{template_id}"):
                new_payload = agent_payload(
                    f"workflow_add_new_{template_id}",
                    {"name": "New Workflow Agent", "role": "Workflow Agent"},
                )
                add_new_agent = st.form_submit_button("Create Agent Node", type="primary")

            if add_new_agent:
                new_name = new_payload["name"].strip()
                if not new_name:
                    st.error("Agent name is required.")
                elif new_name in agents_by_name:
                    st.error("Another agent already uses that name.")
                else:
                    new_payload["name"] = new_name
                    result = api_post("/agents", json=new_payload)
                    if result["ok"]:
                        updated_graph = graph_with_appended_node(current_flow_state, normalized_edges, new_name)
                        save_template_graph(template_id, updated_graph, graph_signature_key, "Agent node created.")
                    else:
                        show_api_error(result)

st.subheader("Workflow and Agent Details")
detail_agents_tab, detail_edges_tab, all_agents_tab = st.tabs(
    ["Workflow Agents", "Workflow Edges", "All Agents"]
)
current_graph = flow_state_to_graph(current_flow_state, normalized_edges)
current_nodes = current_graph["nodes"]
current_edges = current_graph["edges"]

with detail_agents_tab:
    agent_rows = workflow_agent_rows(current_nodes, agents_by_name)
    st.dataframe(pd.DataFrame(agent_rows), width="stretch", hide_index=True)
    missing_nodes = [row["node"] for row in agent_rows if row["configured"] == "no"]
    if missing_nodes:
        st.warning(
            "These workflow nodes do not have saved agent configs yet: "
            + ", ".join(missing_nodes)
        )
        if st.button("Create Missing Agent Configs", key=f"create_missing_agents_{template_id}"):
            failures = []
            for node_name in missing_nodes:
                result = api_post("/agents", json=draft_agent_for_node(node_name))
                if not result["ok"]:
                    failures.append(node_name)
            if failures:
                st.error("Could not create configs for: " + ", ".join(failures))
            else:
                st.success("Missing agent configs created.")
                st.rerun()

    configured_workflow_agents = [agents_by_name[name] for name in current_nodes if name in agents_by_name]
    with st.expander("Edit Attached Agent Configs", expanded=False):
        if not configured_workflow_agents:
            st.info("No configured agents are attached to this workflow yet.")
        for agent in configured_workflow_agents:
            with st.form(f"workflow_detail_edit_agent_{template_id}_{agent['id']}"):
                edited_payload = agent_payload(f"workflow_detail_edit_{template_id}_{agent['id']}", agent)
                save_attached_agent = st.form_submit_button(
                    f"Save {agent['name']}",
                    type="primary",
                )

            if save_attached_agent:
                new_name = edited_payload["name"].strip()
                duplicate_node = new_name != agent["name"] and new_name in current_nodes
                duplicate_agent = new_name != agent["name"] and new_name in agents_by_name
                if not new_name:
                    st.error("Agent name is required.")
                elif duplicate_node:
                    st.error("Another node already uses that name.")
                elif duplicate_agent:
                    st.error("Another agent already uses that name.")
                else:
                    edited_payload["name"] = new_name
                    result = api_patch(f"/agents/{agent['id']}", json=edited_payload)
                    if result["ok"]:
                        updated_graph = graph_with_renamed_node(
                            current_flow_state,
                            normalized_edges,
                            agent["name"],
                            new_name,
                        )
                        save_template_graph(
                            template_id,
                            updated_graph,
                            graph_signature_key,
                            "Agent config and workflow node saved.",
                        )
                    else:
                        show_api_error(result)

    with st.expander("Prompts, Rules, and Guardrails", expanded=False):
        if not configured_workflow_agents:
            st.info("No configured agents are attached to this workflow yet.")
        for agent in configured_workflow_agents:
            st.markdown(f"**{agent['name']}** - {agent['role']} - `{agent['model']}`")
            st.caption(f"Tools: {join_values(agent.get('tools'))} | Channels: {join_values(agent.get('channels'))}")
            st.text_area(
                "System prompt",
                value=agent.get("system_prompt", ""),
                height=90,
                disabled=True,
                key=f"workflow_detail_prompt_{template_id}_{agent['id']}",
            )
            st.caption(f"Interaction rules: {agent.get('interaction_rules', '-')}")
            st.caption(f"Guardrails: {agent.get('guardrails', '-')}")
            st.divider()

with detail_edges_tab:
    if current_edges:
        st.dataframe(pd.DataFrame(workflow_edge_rows(current_edges, agents_by_name)), width="stretch", hide_index=True)
    else:
        st.info("This workflow has no edges yet.")

with all_agents_tab:
    if agents:
        all_agents_df = pd.DataFrame(agents)
        st.dataframe(
            all_agents_df[
                [
                    "id",
                    "name",
                    "role",
                    "model",
                    "tools",
                    "channels",
                    "schedule",
                    "skills",
                    "memory_enabled",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
        selected_agent_name = st.selectbox(
            "Edit any configured agent",
            [agent["name"] for agent in agents],
            key=f"workflow_all_agent_selector_{template_id}",
        )
        selected_agent = agents_by_name[selected_agent_name]
        with st.form(f"workflow_all_agent_edit_{template_id}_{selected_agent['id']}"):
            edited_payload = agent_payload(f"workflow_all_edit_{template_id}_{selected_agent['id']}", selected_agent)
            action_cols = st.columns(2)
            save_any_agent = action_cols[0].form_submit_button("Save Agent Config", type="primary")
            duplicate_agent = action_cols[1].form_submit_button("Duplicate Agent")

        if save_any_agent:
            new_name = edited_payload["name"].strip()
            duplicate_node = new_name != selected_agent["name"] and new_name in current_nodes
            duplicate_agent = new_name != selected_agent["name"] and new_name in agents_by_name
            if not new_name:
                st.error("Agent name is required.")
            elif duplicate_node:
                st.error("Another node already uses that name.")
            elif duplicate_agent:
                st.error("Another agent already uses that name.")
            else:
                edited_payload["name"] = new_name
                result = api_patch(f"/agents/{selected_agent['id']}", json=edited_payload)
                if result["ok"]:
                    if selected_agent["name"] in current_nodes:
                        updated_graph = graph_with_renamed_node(
                            current_flow_state,
                            normalized_edges,
                            selected_agent["name"],
                            new_name,
                        )
                        save_template_graph(
                            template_id,
                            updated_graph,
                            graph_signature_key,
                            "Agent config and workflow node saved.",
                        )
                    else:
                        st.success("Agent config saved.")
                        st.rerun()
                else:
                    show_api_error(result)

        if duplicate_agent:
            duplicate_source_name = edited_payload["name"].strip() or selected_agent["name"]
            duplicate_payload = edited_payload | {"name": copy_agent_name(duplicate_source_name, agents_by_name)}
            result = api_post("/agents", json=duplicate_payload)
            if result["ok"]:
                st.success("Agent duplicated.")
                st.rerun()
            else:
                show_api_error(result)

        with st.expander("Delete Agent Config", expanded=False):
            if selected_agent["name"] in current_nodes:
                st.warning(
                    "This agent is attached to the selected workflow. Deleting its config keeps the node, "
                    "but the node will show as missing until another agent is attached or created."
                )
            confirm_agent_delete = st.checkbox(
                f"Confirm delete {selected_agent['name']}",
                key=f"workflow_delete_agent_confirm_{template_id}_{selected_agent['id']}",
            )
            if st.button(
                "Delete Agent Config",
                key=f"workflow_delete_agent_{template_id}_{selected_agent['id']}",
                disabled=not confirm_agent_delete,
            ):
                result = api_delete(f"/agents/{selected_agent['id']}")
                if result["ok"]:
                    st.success("Agent config deleted.")
                    st.rerun()
                else:
                    show_api_error(result)
    else:
        st.info("No agents are configured yet.")

    with st.expander("Create New Agent", expanded=False):
        with st.form(f"workflow_all_agent_create_{template_id}"):
            new_agent_payload = agent_payload(
                f"workflow_all_create_{template_id}",
                {"name": "New Agent", "role": "Worker Agent"},
            )
            create_standalone_agent = st.form_submit_button("Create Agent", type="primary")

        if create_standalone_agent:
            new_name = new_agent_payload["name"].strip()
            if not new_name:
                st.error("Agent name is required.")
            elif new_name in agents_by_name:
                st.error("Another agent already uses that name.")
            else:
                new_agent_payload["name"] = new_name
                result = api_post("/agents", json=new_agent_payload)
                if result["ok"]:
                    st.success("Agent created.")
                    st.rerun()
                else:
                    show_api_error(result)

st.subheader("Edit Builder")
with st.form(f"workflow_builder_{template_id}_{graph_digest}"):
    edited_nodes_text = st.text_area(
        "Nodes, one per line",
        value="\n".join(current_nodes),
        height=140,
        key=f"workflow_builder_nodes_{template_id}_{graph_digest}",
    )
    edges_df = pd.DataFrame(
        current_edges
        or [{"source": "", "target": "", "condition": "always", "feedback_loop": False}]
    )
    edited_edges = st.data_editor(
        edges_df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=f"workflow_builder_edges_{template_id}_{graph_digest}",
    )
    saved = st.form_submit_button("Save Workflow Template")

if saved:
    cleaned_nodes = [line.strip() for line in edited_nodes_text.splitlines() if line.strip()]
    cleaned_edges = []
    for row in edited_edges.to_dict("records"):
        if row.get("source") and row.get("target"):
            cleaned_edges.append(
                {
                    "source": row["source"],
                    "target": row["target"],
                    "condition": row.get("condition") or "always",
                    "feedback_loop": bool(row.get("feedback_loop")),
                }
            )
    flow_state = st.session_state.get(flow_key)
    position_payload = positions_for_nodes(flow_state, positions, cleaned_nodes)
    result = api_patch(
        f"/workflows/templates/{template_id}",
        json={
            "graph": {
                "nodes": cleaned_nodes,
                "edges": cleaned_edges,
                "positions": position_payload,
            }
        },
    )
    if result["ok"]:
        st.success("Workflow template saved.")
        st.rerun()
    else:
        show_api_error(result)

st.subheader("Workflow JSON")
st.caption(
    "This is the editable JSON for the selected workflow. Saving it updates the same graph and "
    "attached agent configs used by the canvas, edge table, and inspector."
)
with st.form(f"workflow_json_editor_{template_id}_{graph_digest}"):
    workflow_json_value = workflow_json_for_editor(template, current_graph, agents_by_name)
    workflow_json_digest = hashlib.sha1(workflow_json_value.encode("utf-8")).hexdigest()[:10]
    workflow_json_text = st.text_area(
        "Selected workflow JSON",
        value=workflow_json_value,
        height=520,
        key=f"workflow_json_text_{template_id}_{workflow_json_digest}",
    )
    apply_json = st.form_submit_button("Apply Workflow JSON", type="primary")

if apply_json:
    payload, agent_payloads, error = workflow_payload_from_json(workflow_json_text)
    if error or not payload:
        st.error(error or "Could not apply workflow JSON.")
    else:
        saved_agents, agent_error = upsert_agent_payloads(agent_payloads)
        if agent_error:
            st.error(agent_error)
        else:
            result = api_patch(f"/workflows/templates/{template_id}", json=payload)
            if result["ok"]:
                st.session_state.pop(flow_key, None)
                st.session_state.pop(graph_signature_key, None)
                st.session_state.pop(f"workflow_inspector_selection_{template_id}", None)
                suffix = f" Saved {saved_agents} agent config(s)." if saved_agents else ""
                st.success(f"Workflow JSON applied. Canvas and inspector refreshed.{suffix}")
                st.rerun()
            else:
                show_api_error(result)

with st.expander("Saved Template API Response", expanded=False):
    st.json(template)
