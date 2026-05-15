from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
from streamlit_flow.state import StreamlitFlowState


def normalize_edges(edges: list) -> list[dict]:
    normalized_edges = []
    for edge in edges:
        if isinstance(edge, dict):
            normalized_edges.append(
                {
                    "source": edge.get("source", ""),
                    "target": edge.get("target", ""),
                    "condition": edge.get("condition", "always"),
                    "feedback_loop": bool(edge.get("feedback_loop", False)),
                }
            )
        else:
            source, target = edge
            normalized_edges.append(
                {"source": source, "target": target, "condition": "always", "feedback_loop": False}
            )
    return normalized_edges


def build_flow_state(node_names: list[str], edge_rows: list[dict], saved_positions: dict) -> StreamlitFlowState:
    flow_nodes = []
    for index, node_name in enumerate(node_names):
        position = saved_positions.get(node_name, {"x": index * 260, "y": 100})
        flow_nodes.append(
            StreamlitFlowNode(
                id=node_name,
                pos=(float(position.get("x", index * 260)), float(position.get("y", 100))),
                data={"content": node_name},
                node_type=_node_type(index, len(node_names)),
                source_position="right",
                target_position="left",
                draggable=True,
                selectable=True,
                connectable=True,
                deletable=True,
                style={
                    "background": "#F8FAFC",
                    "border": "1px solid #94A3B8",
                    "borderRadius": "8px",
                    "padding": "10px",
                    "fontSize": "14px",
                    "minWidth": "150px",
                },
            )
        )

    flow_edges = []
    for index, row in enumerate(edge_rows):
        source = row.get("source", "")
        target = row.get("target", "")
        if not source or not target:
            continue
        feedback_loop = bool(row.get("feedback_loop", False))
        flow_edges.append(
            StreamlitFlowEdge(
                id=f"{source}-{target}-{row.get('condition', 'always')}-{index}",
                source=source,
                target=target,
                edge_type="smoothstep",
                animated=feedback_loop,
                label=row.get("condition", "always"),
                marker_end={"type": "arrowclosed"},
                style={"stroke": "#DC2626" if feedback_loop else "#2563EB", "strokeWidth": 2},
            )
        )
    return StreamlitFlowState(flow_nodes, flow_edges)


def _node_type(index: int, node_count: int) -> str:
    if index == 0:
        return "input"
    if index == node_count - 1:
        return "output"
    return "default"


def render_workflow_canvas(key: str, state: StreamlitFlowState) -> StreamlitFlowState:
    return streamlit_flow(
        key,
        state,
        height=520,
        fit_view=True,
        show_controls=True,
        show_minimap=True,
        allow_new_edges=True,
        animate_new_edges=False,
        get_node_on_click=True,
        get_edge_on_click=True,
        enable_pane_menu=True,
        enable_node_menu=True,
        enable_edge_menu=True,
        hide_watermark=True,
    )


def flow_state_to_graph(flow_state: StreamlitFlowState, edge_rows: list[dict]) -> dict:
    known_feedback = {
        (row["source"], row["target"], row.get("condition") or "always"): bool(row.get("feedback_loop", False))
        for row in edge_rows
        if row.get("source") and row.get("target")
    }
    node_names = [node.id for node in flow_state.nodes]
    node_positions = {
        node.id: {"x": node.position["x"], "y": node.position["y"]}
        for node in flow_state.nodes
    }
    flow_edges = []
    for edge in flow_state.edges:
        if edge.source not in node_names or edge.target not in node_names:
            continue
        flow_edges.append(
            {
                "source": edge.source,
                "target": edge.target,
                "condition": edge.label or "always",
                "feedback_loop": known_feedback.get(
                    (edge.source, edge.target, edge.label or "always"),
                    bool(edge.animated),
                ),
            }
        )
    return {"nodes": node_names, "edges": flow_edges, "positions": node_positions}


def positions_for_nodes(
    flow_state: StreamlitFlowState | None,
    saved_positions: dict,
    node_names: list[str],
) -> dict:
    if flow_state is None:
        return {name: saved_positions.get(name) for name in node_names if saved_positions.get(name)}
    return {
        node.id: {"x": node.position["x"], "y": node.position["y"]}
        for node in flow_state.nodes
        if node.id in node_names
    }


def selected_node(flow_state: StreamlitFlowState) -> StreamlitFlowNode | None:
    return next((node for node in flow_state.nodes if node.id == flow_state.selected_id), None)


def selected_edge(flow_state: StreamlitFlowState) -> StreamlitFlowEdge | None:
    return next((edge for edge in flow_state.edges if edge.id == flow_state.selected_id), None)


def graph_with_renamed_node(
    flow_state: StreamlitFlowState,
    edge_rows: list[dict],
    old_name: str,
    new_name: str,
) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    if old_name == new_name:
        return graph_payload

    graph_payload["nodes"] = [new_name if node == old_name else node for node in graph_payload["nodes"]]
    for edge in graph_payload["edges"]:
        if edge["source"] == old_name:
            edge["source"] = new_name
        if edge["target"] == old_name:
            edge["target"] = new_name

    node_positions = graph_payload.get("positions", {})
    if old_name in node_positions:
        node_positions[new_name] = node_positions.pop(old_name)
    return graph_payload


def graph_with_appended_node(flow_state: StreamlitFlowState, edge_rows: list[dict], node_name: str) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    if node_name not in graph_payload["nodes"]:
        graph_payload["nodes"].append(node_name)
        graph_payload.setdefault("positions", {})[node_name] = {
            "x": max(len(graph_payload["nodes"]) - 1, 0) * 260,
            "y": 220,
        }
    return graph_payload


def graph_without_node(flow_state: StreamlitFlowState, edge_rows: list[dict], node_name: str) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    graph_payload["nodes"] = [node for node in graph_payload["nodes"] if node != node_name]
    graph_payload["edges"] = [
        edge
        for edge in graph_payload["edges"]
        if edge["source"] != node_name and edge["target"] != node_name
    ]
    graph_payload["positions"] = {
        node: position
        for node, position in graph_payload.get("positions", {}).items()
        if node != node_name
    }
    return graph_payload


def graph_with_updated_edge(
    flow_state: StreamlitFlowState,
    edge_rows: list[dict],
    selected_edge_id: str,
    source: str,
    target: str,
    condition: str,
    feedback_loop: bool,
) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    updated_edges = []
    for edge in flow_state.edges:
        if edge.source not in graph_payload["nodes"] or edge.target not in graph_payload["nodes"]:
            continue
        if edge.id == selected_edge_id:
            updated_edges.append(
                {
                    "source": source,
                    "target": target,
                    "condition": condition or "always",
                    "feedback_loop": feedback_loop,
                }
            )
        else:
            updated_edges.append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "condition": edge.label or "always",
                    "feedback_loop": _edge_feedback(edge_rows, edge.source, edge.target, edge.label, edge.animated),
                }
            )
    graph_payload["edges"] = updated_edges
    return graph_payload


def graph_with_appended_edge(
    flow_state: StreamlitFlowState,
    edge_rows: list[dict],
    source: str,
    target: str,
    condition: str,
    feedback_loop: bool,
) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    if source not in graph_payload["nodes"] or target not in graph_payload["nodes"]:
        return graph_payload

    edge = {
        "source": source,
        "target": target,
        "condition": condition or "always",
        "feedback_loop": feedback_loop,
    }
    if edge not in graph_payload["edges"]:
        graph_payload["edges"].append(edge)
    return graph_payload


def graph_without_edge(flow_state: StreamlitFlowState, edge_rows: list[dict], selected_edge_id: str) -> dict:
    graph_payload = flow_state_to_graph(flow_state, edge_rows)
    graph_payload["edges"] = [
        {
            "source": edge.source,
            "target": edge.target,
            "condition": edge.label or "always",
            "feedback_loop": _edge_feedback(edge_rows, edge.source, edge.target, edge.label, edge.animated),
        }
        for edge in flow_state.edges
        if edge.id != selected_edge_id and edge.source in graph_payload["nodes"] and edge.target in graph_payload["nodes"]
    ]
    return graph_payload


def _edge_feedback(edge_rows: list[dict], source: str, target: str, label: str, animated: bool) -> bool:
    return next(
        (
            bool(row.get("feedback_loop", False))
            for row in edge_rows
            if row.get("source") == source
            and row.get("target") == target
            and (row.get("condition") or "always") == (label or "always")
        ),
        bool(animated),
    )
