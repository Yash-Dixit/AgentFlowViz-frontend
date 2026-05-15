# AgentFlowViz Frontend

Streamlit control-plane UI for the AgentFlowViz AI Agent Orchestration Platform.

This repository is intentionally isolated from the backend. Keep Streamlit pages, UI components, frontend-only helpers, visual workflow builder code, and frontend dependencies here.

For the shortest local setup path, use [STARTUP.md](STARTUP.md).

## Repository Pairing And Setup Order

AgentFlowViz is split into two sibling repositories:

```text
AgentFlowViz-frontend    Streamlit UI, workflow editor, monitoring, settings
AgentFlowViz-backend     FastAPI, LangGraph runtime, Postgres, Telegram, Ollama calls
```

Set up the backend repo first. The backend repository owns Docker Compose for the full local stack and builds this frontend container automatically when the repos are siblings.

## Role In The System

The frontend is responsible for:

- Unified workflow and agent CRUD screens
- Visual workflow building
- Template selection
- Agent configuration panels
- Live workflow monitoring
- Message history views
- Token and cost dashboards
- Demo controls for running end-to-end workflows

The backend should own real agent execution, persistence, messaging integrations, and API/runtime logic.

## Technology Choice Justification

- Streamlit gives the product a working web UI quickly without a heavy frontend build system.
- `streamlit-flow-component` provides the visual workflow builder, drag-and-drop nodes, edge editing, and selected-element inspection.
- Native Streamlit forms and tables keep the code readable for a live walkthrough.
- The frontend is intentionally thin: it edits configuration and monitors runs while the backend owns runtime execution.

## Local Model Strategy

The UI should expose model selection, but it should only list models served by the local Ollama backend.

Recommended default options for the current hosting rig:

```text
Planner / coordinator    gpt-oss:20b
Fast worker agents       qwen3.5:9b
Image attachment vision  llava:7b
Memory / RAG             qwen3-embedding:4b
```

The frontend should display Ollama runtime health from the backend:

- current model loaded
- available local models
- per-run prompt tokens and output tokens
- tokens per second
- estimated kWh and local electricity cost from backend wattage settings
- model load/generation duration
- semantic cache status, entries, threshold, and index type
- RSS RAG scheduler status, indexed item count, and freshness window
- semantic cache savings: cache hits, LLM calls saved, and prompt/output tokens saved
- conversation memory summary entries and short-term turn window
- VRAM warning if multiple large chat models are selected

## Simplicity-First UI

Keep the Streamlit code readable and demo-focused:

- Prefer native Streamlit widgets before custom frontend code.
- Use native Streamlit widgets and `streamlit-flow-component` for the workflow canvas.
- Use `st.fragment(run_every="1s")` for live updates instead of extra refresh libraries.
- Keep each page small and purpose-specific.
- Store UI state in `st.session_state`, not hidden global variables.
- Let the backend own workflow execution, persistence, Telegram, and Ollama calls.

Minimum product UI:

```text
Workflows page       Visual builder, workflow lifecycle, agent CRUD, node/edge inspector,
                     attached-agent editing, and all-agent management
Run Demo page        Start any active orchestrated workflow
Monitoring page      Live logs, messages, tool calls, tokens, status, Telegram user filters
Settings page        Backend URL, local model visibility, Telegram status
```

## Recommended UX

The main Streamlit app should feel like an orchestration console:

```text
Left sidebar      Workflows, demo runs, monitoring, settings
Center canvas     Drag-and-drop agent workflow graph
Right inspector   Selected node or agent configuration
Bottom drawer     Live logs, inter-agent messages, tool calls, cost
Top controls      Run, pause, stop, replay, save template
```

For a highly interactive UI, use:

- `st.session_state` for selected nodes, open panels, current run, and unsaved edits
- `st.fragment(run_every="1s")` for live logs and run status
- `st.chat_input` and `st.chat_message` for agent testing
- `st.data_editor` for fast configuration tables
- `streamlit-flow-component` for a draggable canvas with node, edge, and agent configuration panels

## Suggested Setup

For a quick Docker startup, use [STARTUP.md](STARTUP.md). The commands below are for manual development.

One-command Windows setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

Manual setup:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Suggested Run Command

Scripted:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

Runtime stdout/stderr logs are written under `logs/`.

Manual:

```bash
streamlit run app.py
```

## Docker Run

The full local stack can be started from the sibling backend repository:

```powershell
cd ..\AgentFlowViz-backend
docker compose up --build
```

That compose file builds this frontend image, starts the backend and Postgres, and points Streamlit at `http://backend:8000` inside Docker. Ollama should keep running on the host machine.

Important Ollama caveat: the Docker stack runs the frontend, backend, and Postgres, but it expects Ollama to already be running on the host machine with the configured models pulled. If Ollama is stopped or a model is missing, the Settings page will show the backend/model health problem and agent runs will not complete normally.

## Live Telegram Demo

The frontend does not store Telegram secrets. Configure Telegram in the backend `.env`, then use the Settings page to confirm:

```text
Telegram configured = yes
Telegram running = yes
Allowed users = 1
```

To watch the live flow:

1. Open Streamlit at `http://127.0.0.1:8501`.
2. Go to Settings and confirm Telegram is running.
3. Send `/start` to your Telegram bot.
4. Choose `Smart Task Router` or `Image and Document Router`.
5. Send a normal prompt to your Telegram bot.
6. Go to Monitoring and select the newest run.
7. Watch messages, tool calls, logs, tokens, and the final response update live.

## Capability Checklist Covered In UI

```text
Agent CRUD                  Workflows inspector and All Agents tab
Agent configuration          Prompt, model, tools, channels, schedules, memory,
                             skills, interaction rules, guardrails, execution/token limits
Visual builder               Drag/drop canvas with saved positions
Conditions and loops         Edge inspector and editable edge table
Workflow templates           Template selector and seed button
Workflow lifecycle           Create, edit, enable/disable, delete, and reseed templates
Orchestration routing        Both default templates include a visible orchestrator decision node
Media workflow               Upload images/documents in Run Demo; backend stores them in MinIO
Context profiles             Agent configs expose short, long, and large Ollama context windows
External channel             Settings and Monitoring visibility for Telegram runs
Live monitoring              Logs, messages, tool calls, token metrics, status
Energy telemetry             kWh and wattage-based cost estimate for local Ollama runs
RSS RAG                      Settings visibility for scheduled RSS ingestion and indexed items
Cache savings                Saved LLM calls and prompt/output tokens on cache-hit runs
Telegram run filtering       Filter Monitoring by Telegram user ID and dated conversation runs
End-to-end demo              Run Demo page and Telegram-to-monitoring workflow
```

## Editing Workflows

For complete example workflows, see [WORKFLOW_EXAMPLES.md](WORKFLOW_EXAMPLES.md).

1. Open Workflows.
2. Create a workflow, seed examples, or select an existing template.
3. Enable or disable the selected workflow depending on whether it should be runnable.
4. Drag nodes on the canvas.
5. Click a node to edit that agent in the inspector.
6. Click an edge to edit source, target, condition, or feedback-loop status.
7. Add an existing agent or create a new agent node directly in the inspector.
8. Review, duplicate, delete, and edit Workflow Agents, Workflow Edges, and All Agents on the same page.
9. Save the canvas or workflow template.
10. Delete a workflow only after confirming it in the lifecycle controls.

## Environment Variables

Create a local `.env` file for frontend settings:

```env
BACKEND_URL=http://localhost:8000
DEFAULT_CHAT_MODEL=gpt-oss:20b
DEFAULT_FAST_MODEL=qwen3.5:9b
DEFAULT_EMBEDDING_MODEL=qwen3-embedding:4b
```

Do not commit real secrets.

## Page Structure

```text
app.py
components/
  agent_form.py
  workflow_canvas.py
pages/
  1_Workflows.py
  3_Run_Demo.py
  4_Monitoring.py
  5_Settings.py
```
