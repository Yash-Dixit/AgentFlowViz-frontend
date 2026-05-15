# Orchestration Workflow Examples

Use this guide to create your own orchestration workflows.

Fastest path: create the full workflow package by pasting JSON into Streamlit, then use the same page to review or fine-tune the agents.

Manual path: if you do not want to use JSON, skip to **Before You Create Any Workflow** and follow the click-by-click Streamlit steps.

## Quick Path: Create Workflows With JSON

Use this path when you want to create the workflow structure quickly and avoid manually entering every node and edge row.

The JSON can create or update the workflow graph:

```text
Workflow name
Description
Enabled/disabled status
Nodes
Edges
Canvas positions
```

The same JSON can also update the agent configs when it includes an `agents` array:

- **Agent name** - Must match the workflow node name exactly.
- **Role** - Defines what type of agent it is, like orchestrator, researcher, analyst, or final writer.
- **System prompt** - Main instruction that tells the agent how to behave and what task to perform.
- **Model** - Ollama model used by that agent, such as `qwen3.5:9b` or `gpt-oss:20b`.
- **Tools** - Backend capabilities the agent can call, like calculator, RSS RAG, or attachment reader.
- **Channels** - Where the agent can interact, such as `streamlit` or `telegram`.
- **Schedule** - When the agent is meant to run, usually `manual` for normal workflows.
- **Skills** - Descriptive tags for what the agent is good at, such as `planning`, `rss_rag`, or `final_response`.
- **Memory setting** - Controls whether the agent can use saved conversation memory.
- **Interaction rules** - Extra behavior rules for how the agent should coordinate or respond.
- **Guardrails** - Safety and quality boundaries, such as staying factual or hiding internal logs.
- **Execution and token limits** - Caps steps, tool calls, and output length so runs stay controlled.
- **Context window** - Controls how much prior context the agent can receive: `short`, `long`, or `large`.

Internally, workflow templates and agent configs are saved as separate records, but Streamlit can update both from one JSON payload.

After creating the workflow JSON, you have two choices:

```text
Graph-only JSON    Open Streamlit, click Create Missing Agent Configs, then edit prompts/tools in the UI.
Complete JSON      Include an agents array so the same paste updates graph plus agent configs.
```

For most demos, use the complete JSON examples below. They include the workflow graph and every agent config needed to run the workflow.

### Where To Paste The JSON In Streamlit

1. Make sure the Docker stack is running.
2. Open Streamlit:

```text
http://127.0.0.1:8501
```

3. Go to **Workflows**.
4. Open **Paste Workflow JSON**.
5. Paste one of the workflow JSON payloads below.
6. Keep **Update existing workflow with the same key** enabled if you want to overwrite an older version.
7. Click **Import Workflow JSON**.
8. Select the imported workflow from the **Workflow** dropdown.
9. Open **Workflow Agents**.
10. Click **Create Missing Agent Configs** if any nodes show `configured: no`.
11. If the JSON included an `agents` array, the attached agent configs are updated automatically.
12. If the JSON was graph-only, open **Edit Attached Agent Configs** and apply the agent values from the detailed manual section for that workflow.

If Streamlit says the workflow already exists, either keep the update checkbox enabled or change the `name` field in the JSON.

### Editing JSON After Import

After a workflow exists, you can edit the selected workflow's JSON directly from the same **Workflows** page:

1. Select the workflow from the **Workflow** dropdown.
2. Scroll to **Workflow JSON**.
3. Edit the JSON in **Selected workflow JSON**.
4. Click **Apply Workflow JSON**.

The saved JSON updates the same workflow graph used by the canvas, edge table, and inspector. After you apply JSON, the page refreshes so node and edge inspector options reflect the new graph.

The sync works both ways:

```text
Edit JSON and apply it       Canvas, edge table, inspector, and attached agent configs reload from the JSON.
Edit canvas or edge table    Save the workflow, then the Workflow JSON panel shows the new graph.
Edit a node in inspector     The matching Agent config is saved, and the Workflow JSON panel includes it after refresh.
```

The **Workflow JSON** panel includes an `agents` array for every configured agent attached to the selected workflow. That makes it the best place to copy a complete reusable workflow package.

### Backend API Alternative

Use Streamlit for the complete all-in-one JSON path. The Streamlit importer updates both the workflow graph and the `agents` array.

You can also paste the workflow JSON through the backend API docs, but **POST `/workflows/templates` only stores the workflow graph**. If you use the backend API directly, create or update agents separately through **POST `/agents`** or **PATCH `/agents/{agent_id}`**.

1. Open `http://127.0.0.1:8000/docs`.
2. Find **workflows**.
3. Open **POST `/workflows/templates`**.
4. Click **Try it out**.
5. Delete the example body.
6. Paste one of the workflow JSON payloads below.
7. Click **Execute**.

If the API returns `409 Workflow template name already exists`, either delete the old workflow from Streamlit or change the `name` field in the JSON.

### PowerShell Alternative

You can also save the JSON into a file such as `workflow.json`, then run this for the workflow graph. Agent configs still need Streamlit import or separate `/agents` requests.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/workflows/templates" `
  -ContentType "application/json" `
  -Body (Get-Content .\workflow.json -Raw)
```

### JSON 1: Image And Document Review Router

Paste this into **Paste Workflow JSON** in Streamlit. It creates the workflow graph and configures every attached agent.

```json
{
  "name": "media_review_router",
  "description": "Routes uploaded images or documents to the right specialist before drafting one final answer.",
  "is_active": true,
  "graph": {
    "nodes": [
      "Media Intake",
      "Media Orchestrator",
      "Image Specialist",
      "Document Specialist",
      "Media Reply Writer"
    ],
    "edges": [
      {
        "source": "Media Intake",
        "target": "Media Orchestrator",
        "condition": "always",
        "feedback_loop": false
      },
      {
        "source": "Media Orchestrator",
        "target": "Image Specialist",
        "condition": "image_request",
        "feedback_loop": false
      },
      {
        "source": "Media Orchestrator",
        "target": "Document Specialist",
        "condition": "document_request",
        "feedback_loop": false
      },
      {
        "source": "Image Specialist",
        "target": "Media Reply Writer",
        "condition": "image_done",
        "feedback_loop": false
      },
      {
        "source": "Document Specialist",
        "target": "Media Reply Writer",
        "condition": "document_done",
        "feedback_loop": false
      },
      {
        "source": "Media Reply Writer",
        "target": "Media Orchestrator",
        "condition": "needs_more_context",
        "feedback_loop": true
      }
    ],
    "positions": {
      "Media Intake": {"x": 0, "y": 180},
      "Media Orchestrator": {"x": 280, "y": 180},
      "Image Specialist": {"x": 580, "y": 80},
      "Document Specialist": {"x": 580, "y": 280},
      "Media Reply Writer": {"x": 900, "y": 180}
    }
  },
  "agents": [
    {
      "name": "Media Intake",
      "role": "Intake Agent",
      "system_prompt": "Summarize the uploaded file context and the user's requested output. Identify whether the upload looks like a document, screenshot, image, report, article, CSV, or diagram. Do not answer the user yet.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["intake", "channel_adapter", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Keep the handoff short and pass the useful attachment context forward.",
      "guardrails": "Be concise, factual, and do not expose internal workflow details.",
      "limits": {
        "max_steps": 2,
        "max_tool_calls": 1,
        "max_output_tokens": 120,
        "context_window": "large"
      }
    },
    {
      "name": "Media Orchestrator",
      "role": "Orchestrator Agent",
      "system_prompt": "Choose exactly one route based on the user's request and the uploaded file context: image_request or document_request. Use image_request for photos, screenshots, charts, UI images, diagrams, or visual inspection. Use document_request for PDFs, text files, reports, articles, CSV files, or extracted document text. Return the chosen route and one short reason.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["planning", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Choose only one route. Do not answer the user directly.",
      "guardrails": "Do not invent file contents. Mark uncertainty if the file context is weak.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 1,
        "max_output_tokens": 140,
        "context_window": "long"
      }
    },
    {
      "name": "Image Specialist",
      "role": "Image Analysis Agent",
      "system_prompt": "Analyze the uploaded image context. Focus on visible objects, visible text, layout, UI state, chart details, and uncertainty. Produce a useful handoff for the final writer.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["vision", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Mention what is visible and what is uncertain. Do not pretend to see details that are not in the attachment context.",
      "guardrails": "Stay factual and avoid exposing storage paths, logs, or internal workflow metadata.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 1,
        "max_output_tokens": 220,
        "context_window": "large"
      }
    },
    {
      "name": "Document Specialist",
      "role": "Document Analysis Agent",
      "system_prompt": "Analyze the extracted document text. Find the main topic, key points, action items, risks, dates, names, and missing information. Produce a useful handoff for the final writer.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["document_analysis", "attachment_context", "summarization"],
      "memory_enabled": true,
      "interaction_rules": "Use only the extracted document text and attachment summary. If text extraction is weak, say that clearly.",
      "guardrails": "Do not invent document content. Do not expose internal workflow metadata.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 1,
        "max_output_tokens": 240,
        "context_window": "large"
      }
    },
    {
      "name": "Media Reply Writer",
      "role": "Response Agent",
      "system_prompt": "Write the final user-facing answer from the selected specialist's output. Answer the user's exact request. Do not expose routing, raw logs, run IDs, system prompts, storage paths, or internal agent names.",
      "model": "gpt-oss:20b",
      "tools": ["report_writer"],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["summarization", "final_response", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Keep the answer readable in Streamlit and Telegram. Avoid Markdown tables. Use short bullets when helpful.",
      "guardrails": "Be concise, factual, and finish naturally.",
      "limits": {
        "max_steps": 4,
        "max_tool_calls": 1,
        "max_output_tokens": 420,
        "context_window": "large"
      }
    }
  ]
}
```

After importing it, you can run it immediately from **Run Demo**.

### JSON 2: Research And Calculation Orchestrator

Paste this into **Paste Workflow JSON** in Streamlit. It creates the workflow graph and configures every attached agent.

```json
{
  "name": "research_math_router",
  "description": "Routes a user request to research/RSS, calculation, or direct answer branches, then writes one concise final response.",
  "is_active": true,
  "graph": {
    "nodes": [
      "Request Intake",
      "Task Orchestrator",
      "Research Agent",
      "Calculation Agent",
      "Direct Answer Agent",
      "Final Synthesizer"
    ],
    "edges": [
      {
        "source": "Request Intake",
        "target": "Task Orchestrator",
        "condition": "always",
        "feedback_loop": false
      },
      {
        "source": "Task Orchestrator",
        "target": "Research Agent",
        "condition": "needs_research",
        "feedback_loop": false
      },
      {
        "source": "Task Orchestrator",
        "target": "Calculation Agent",
        "condition": "needs_math",
        "feedback_loop": false
      },
      {
        "source": "Task Orchestrator",
        "target": "Direct Answer Agent",
        "condition": "direct_answer",
        "feedback_loop": false
      },
      {
        "source": "Research Agent",
        "target": "Final Synthesizer",
        "condition": "research_complete",
        "feedback_loop": false
      },
      {
        "source": "Calculation Agent",
        "target": "Final Synthesizer",
        "condition": "calculation_complete",
        "feedback_loop": false
      },
      {
        "source": "Direct Answer Agent",
        "target": "Final Synthesizer",
        "condition": "answer_ready",
        "feedback_loop": false
      },
      {
        "source": "Final Synthesizer",
        "target": "Task Orchestrator",
        "condition": "incomplete_answer",
        "feedback_loop": true
      }
    ],
    "positions": {
      "Request Intake": {"x": 0, "y": 200},
      "Task Orchestrator": {"x": 280, "y": 200},
      "Research Agent": {"x": 580, "y": 60},
      "Calculation Agent": {"x": 580, "y": 200},
      "Direct Answer Agent": {"x": 580, "y": 340},
      "Final Synthesizer": {"x": 920, "y": 200}
    }
  },
  "agents": [
    {
      "name": "Request Intake",
      "role": "Intake Agent",
      "system_prompt": "Capture the user's goal, constraints, expected output format, and any important numbers or time-sensitive words. Do not solve the request yet.",
      "model": "qwen3.5:9b",
      "tools": [],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["intake", "channel_adapter"],
      "memory_enabled": true,
      "interaction_rules": "Keep the handoff compact and preserve the user's exact intent.",
      "guardrails": "Do not expose internal workflow details.",
      "limits": {
        "max_steps": 2,
        "max_tool_calls": 0,
        "max_output_tokens": 120,
        "context_window": "long"
      }
    },
    {
      "name": "Task Orchestrator",
      "role": "Orchestrator Agent",
      "system_prompt": "Choose exactly one route: needs_research, needs_math, or direct_answer. Use needs_research for latest news, RSS, leads, market updates, comparisons, or fact-finding. Use needs_math for percentages, totals, conversions, calculations, or numeric reasoning. Use direct_answer for simple writing, explanation, or prompt-generation requests. Return the chosen route and one short reason.",
      "model": "qwen3.5:9b",
      "tools": [],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["planning", "task_decomposition"],
      "memory_enabled": true,
      "interaction_rules": "Choose only one route and do not answer the user directly.",
      "guardrails": "If the request is time-sensitive, prefer needs_research. If the request contains numbers that must be calculated, prefer needs_math.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 0,
        "max_output_tokens": 140,
        "context_window": "long"
      }
    },
    {
      "name": "Research Agent",
      "role": "Research Agent",
      "system_prompt": "Use rss_rag_retriever for latest news, RSS, lead, or recent update requests. Use local_research for general non-live research. Summarize only the most useful findings for the final writer.",
      "model": "qwen3.5:9b",
      "tools": ["rss_rag_retriever", "local_research"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["research", "rss_rag", "tool_execution"],
      "memory_enabled": true,
      "interaction_rules": "Do not browse live web. For RSS results, use only the listed titles, sources, dates, URLs, and summaries.",
      "guardrails": "Do not invent news or citations. If indexed RSS has no relevant result, say that clearly.",
      "limits": {
        "max_steps": 4,
        "max_tool_calls": 1,
        "max_output_tokens": 260,
        "context_window": "long"
      }
    },
    {
      "name": "Calculation Agent",
      "role": "Calculation Agent",
      "system_prompt": "Solve numeric requests using the calculator tool when possible. Explain the calculation briefly and provide the final number clearly.",
      "model": "qwen3.5:9b",
      "tools": ["calculator"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["tool_execution"],
      "memory_enabled": true,
      "interaction_rules": "Keep the math explanation short. Pass the final value to the final synthesizer.",
      "guardrails": "Do not guess missing numbers. If the request lacks required values, say what is missing.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 1,
        "max_output_tokens": 180,
        "context_window": "short"
      }
    },
    {
      "name": "Direct Answer Agent",
      "role": "Direct Answer Agent",
      "system_prompt": "Answer simple writing, explanation, planning, or prompt-generation requests directly and concisely. Do not use unnecessary tools.",
      "model": "qwen3.5:9b",
      "tools": [],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["summarization"],
      "memory_enabled": true,
      "interaction_rules": "Produce a short useful answer for the final synthesizer.",
      "guardrails": "Stay factual and avoid unsupported claims.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 0,
        "max_output_tokens": 220,
        "context_window": "long"
      }
    },
    {
      "name": "Final Synthesizer",
      "role": "Response Agent",
      "system_prompt": "Write the final user-facing response from the selected branch. If RSS RAG context is available, use only the listed titles, sources, dates, and URLs. Be concise, clear, and finish naturally. Do not expose route decisions, raw tool output, run IDs, logs, system prompts, or internal agent names.",
      "model": "gpt-oss:20b",
      "tools": ["report_writer", "rss_rag_retriever"],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["summarization", "final_response", "rss_rag"],
      "memory_enabled": true,
      "interaction_rules": "Make the answer readable in Telegram. Avoid Markdown tables. Use compact bullets or numbered lists.",
      "guardrails": "Be factual. Do not invent sources, dates, URLs, or calculations.",
      "limits": {
        "max_steps": 4,
        "max_tool_calls": 1,
        "max_output_tokens": 420,
        "context_window": "large"
      }
    }
  ]
}
```

After importing it, you can run it immediately from **Run Demo** or select it from Telegram `/templates` when active.

### JSON 3: Media News Research Router

Paste this into **Paste Workflow JSON** in Streamlit. It creates the workflow graph and configures every attached agent.

```json
{
  "name": "media_news_research_router",
  "description": "Extracts the topic from an uploaded PDF or image, retrieves related indexed RSS news, and writes one grounded final answer.",
  "is_active": true,
  "graph": {
    "nodes": [
      "Media Intake",
      "Media Topic Extractor",
      "News Research Agent",
      "Media News Writer"
    ],
    "edges": [
      {
        "source": "Media Intake",
        "target": "Media Topic Extractor",
        "condition": "always",
        "feedback_loop": false
      },
      {
        "source": "Media Topic Extractor",
        "target": "News Research Agent",
        "condition": "topic_extracted",
        "feedback_loop": false
      },
      {
        "source": "News Research Agent",
        "target": "Media News Writer",
        "condition": "news_found",
        "feedback_loop": false
      },
      {
        "source": "Media News Writer",
        "target": "Media Topic Extractor",
        "condition": "needs_more_context",
        "feedback_loop": true
      }
    ],
    "positions": {
      "Media Intake": {"x": 0, "y": 180},
      "Media Topic Extractor": {"x": 300, "y": 180},
      "News Research Agent": {"x": 620, "y": 180},
      "Media News Writer": {"x": 940, "y": 180}
    }
  },
  "agents": [
    {
      "name": "Media Intake",
      "role": "Intake Agent",
      "system_prompt": "Summarize the uploaded file context and the user's requested output. Identify whether the upload looks like a document, screenshot, image, report, article, or diagram. Do not answer the user yet.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["intake", "channel_adapter", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Keep the handoff short and pass the useful attachment context forward.",
      "guardrails": "Be concise, factual, and do not expose internal workflow details.",
      "limits": {
        "max_steps": 2,
        "max_tool_calls": 1,
        "max_output_tokens": 120,
        "context_window": "large"
      }
    },
    {
      "name": "Media Topic Extractor",
      "role": "Topic Extraction Agent",
      "system_prompt": "Extract the main topic, entities, company names, product names, technologies, dates, keywords, and user intent from the uploaded image or document context. Produce a compact search-focused handoff for RSS news retrieval. Do not invent details that are not present.",
      "model": "qwen3.5:9b",
      "tools": ["attachment_context_reader"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["planning", "attachment_context", "research"],
      "memory_enabled": true,
      "interaction_rules": "Prefer 3 to 8 high-quality search keywords over a long paragraph.",
      "guardrails": "Clearly mark uncertainty when the uploaded content is blurry, incomplete, or has weak OCR.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 1,
        "max_output_tokens": 160,
        "context_window": "large"
      }
    },
    {
      "name": "News Research Agent",
      "role": "RSS Research Agent",
      "system_prompt": "Use rss_rag_retriever to find the latest indexed RSS items related to the extracted topic. Use only indexed RSS results. Return titles, sources, dates, URLs, and a short note explaining why each item is relevant to the uploaded content.",
      "model": "qwen3.5:9b",
      "tools": ["rss_rag_retriever"],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["research", "rss_rag", "tool_execution"],
      "memory_enabled": true,
      "interaction_rules": "Do not browse the live web. Do not invent news. If RSS RAG has no relevant result, say that clearly.",
      "guardrails": "Use only the listed RSS titles, sources, dates, URLs, and summaries from the tool output.",
      "limits": {
        "max_steps": 4,
        "max_tool_calls": 1,
        "max_output_tokens": 240,
        "context_window": "long"
      }
    },
    {
      "name": "Media News Writer",
      "role": "Response Agent",
      "system_prompt": "Write the final user-facing answer by connecting the uploaded file context with the latest indexed RSS results. Use only the listed RSS titles, sources, dates, and URLs. If no relevant RSS item is found, say that clearly and explain what was extracted from the upload. Do not expose workflow logs, route decisions, raw tool output, or internal agent names.",
      "model": "gpt-oss:20b",
      "tools": ["report_writer"],
      "channels": ["streamlit", "telegram"],
      "schedule": "manual",
      "skills": ["summarization", "final_response", "rss_rag", "attachment_context"],
      "memory_enabled": true,
      "interaction_rules": "Keep the answer readable for Telegram. Avoid Markdown tables. Use short bullets or a numbered list.",
      "guardrails": "Be concise, factual, and finish naturally.",
      "limits": {
        "max_steps": 4,
        "max_tool_calls": 1,
        "max_output_tokens": 420,
        "context_window": "large"
      }
    }
  ]
}
```

After importing it, you can run it immediately from **Run Demo** with a PDF or image upload.

### Optional: Agent JSON Shape

If you want one JSON paste to update everything, include an `agents` array at the top level of the workflow JSON. Each item should use this shape:

```json
{
  "name": "example_router",
  "description": "Example workflow with one configured agent.",
  "is_active": true,
  "graph": {
    "nodes": ["Task Orchestrator"],
    "edges": [],
    "positions": {
      "Task Orchestrator": {"x": 0, "y": 120}
    }
  },
  "agents": [
    {
      "name": "Task Orchestrator",
      "role": "Orchestrator Agent",
      "system_prompt": "Choose exactly one route and explain the reason briefly.",
      "model": "qwen3.5:9b",
      "tools": [],
      "channels": ["streamlit"],
      "schedule": "manual",
      "skills": ["planning", "task_decomposition"],
      "memory_enabled": true,
      "interaction_rules": "Choose only one route and do not answer the user directly.",
      "guardrails": "Stay factual and do not expose internal workflow details.",
      "limits": {
        "max_steps": 3,
        "max_tool_calls": 0,
        "max_output_tokens": 140,
        "context_window": "long"
      }
    }
  ]
}
```

The agent name must exactly match one of the names in `graph.nodes`.

You can also save an agent separately through **POST `/agents`** in the backend API docs. Use this body shape:

```json
{
  "name": "Task Orchestrator",
  "role": "Orchestrator Agent",
  "system_prompt": "Choose exactly one route: needs_research, needs_math, or direct_answer. Use needs_research for latest news, RSS, leads, market updates, comparisons, or fact-finding. Use needs_math for percentages, totals, conversions, calculations, or numeric reasoning. Use direct_answer for simple writing, explanation, or prompt-generation requests. Return the chosen route and one short reason.",
  "model": "qwen3.5:9b",
  "tools": [],
  "channels": ["streamlit"],
  "schedule": "manual",
  "skills": ["planning", "task_decomposition"],
  "memory_enabled": true,
  "interaction_rules": "Choose only one route and do not answer the user directly.",
  "guardrails": "If the request is time-sensitive, prefer needs_research. If the request contains numbers that must be calculated, prefer needs_math.",
  "limits": {
    "max_steps": 3,
    "max_tool_calls": 0,
    "max_output_tokens": 140,
    "context_window": "long"
  }
}
```

For the remaining agents, use the same JSON field names and copy the values from the manual agent sections below.

If **POST `/agents`** returns a duplicate-name error, the agent already exists. Edit it from Streamlit or use **PATCH `/agents/{agent_id}`** in the API docs.

## Manual Path: Use Streamlit Forms

Open `http://127.0.0.1:8501`, go to **Workflows**, and use **Create Workflow**. The important rule is simple: every node name in the workflow should have a matching Agent config with the same name. If a node is missing an Agent config, create it from the node inspector.

## Before You Create Any Workflow

The Workflows page has three useful areas for editing the same template:

```text
Canvas / Inspector       Best for clicking a node or edge and editing it quickly.
Edit Builder             Best for pasting the full node list and edge table.
Workflow Agents tab      Best for checking whether every node has a saved Agent config.
```

For the fastest setup, use **Edit Builder** first, then use **Workflow Agents** to create and edit the matching agent configs.

Important rule:

```text
Every workflow node name must match an Agent name exactly.
```

Example: if the node is named `Task Orchestrator`, the agent config must also be named `Task Orchestrator`.

Orchestrator rule:

```text
The orchestrator prompt should mention the exact route names used by its outgoing edge conditions.
```

Example: if the outgoing edges are `needs_research`, `needs_math`, and `direct_answer`, the orchestrator prompt should say: "Choose exactly one route: needs_research, needs_math, or direct_answer."

Feedback-loop note:

```text
A feedback-loop edge is saved and shown in the workflow context as a possible revision path. The normal forward execution path still follows non-feedback edges.
```

## Workflow 1: Image And Document Review Router

Use this when a user uploads a PDF, text file, screenshot, or image and you want the workflow to route the request to either an image specialist or a document specialist before writing one final answer.

This is the easiest custom workflow to understand because the orchestrator has only two choices:

```text
image_request
document_request
```

### Step 1: Create The Workflow

1. Open `http://127.0.0.1:8501`.
2. Click **Workflows** in the left sidebar.
3. Open the **Create Workflow** expander near the top.
4. Enter these values:

```text
Workflow key: media_review_router
Description: Routes uploaded images or documents to the right specialist before drafting one final answer.
Enabled: on
```

5. Click **Create Workflow**.
6. In the **Workflow** dropdown, select **Media Review Router**.

### Step 2: Paste The Nodes

1. Scroll down to **Edit Builder**.
2. In **Nodes, one per line**, replace everything with this exact list:

```text
Media Intake
Media Orchestrator
Image Specialist
Document Specialist
Media Reply Writer
```

### Step 3: Enter The Edge Rows

In the edge table under the node list, enter these rows. Add rows if the table does not already have enough blank rows.

```text
source: Media Intake
target: Media Orchestrator
condition: always
feedback_loop: false

source: Media Orchestrator
target: Image Specialist
condition: image_request
feedback_loop: false

source: Media Orchestrator
target: Document Specialist
condition: document_request
feedback_loop: false

source: Image Specialist
target: Media Reply Writer
condition: image_done
feedback_loop: false

source: Document Specialist
target: Media Reply Writer
condition: document_done
feedback_loop: false

source: Media Reply Writer
target: Media Orchestrator
condition: needs_more_context
feedback_loop: true
```

Then click **Save Workflow Template**.

### Step 4: Create Missing Agent Configs

1. Scroll to **Workflow and Agent Details**.
2. Open the **Workflow Agents** tab.
3. If any row says `configured: no`, click **Create Missing Agent Configs**.
4. Wait for the page to refresh.
5. Confirm every row now says `configured: yes`.

### Step 5: Edit The Agent Configs

1. Stay in **Workflow and Agent Details**.
2. Open **Edit Attached Agent Configs**.
3. Edit one agent at a time.
4. After changing an agent, click **Save `<agent name>`** before moving to the next one.

#### Media Intake

Enter these values:

```text
Name: Media Intake
Role: Intake Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: intake, channel_adapter, attachment_context
System prompt: Summarize the uploaded file context and the user's requested output. Identify whether the upload looks like a document, screenshot, image, report, article, CSV, or diagram. Do not answer the user yet.
Interaction rules: Keep the handoff short and pass the useful attachment context forward.
Guardrails: Be concise, factual, and do not expose internal workflow details.
Max steps: 2
Max tool calls: 1
Max output tokens: 120
Context window: large
```

Why this agent exists: it reads the attachment context and creates a compact handoff.

#### Media Orchestrator

Enter these values:

```text
Name: Media Orchestrator
Role: Orchestrator Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: planning, attachment_context
System prompt: Choose exactly one route based on the user's request and the uploaded file context: image_request or document_request. Use image_request for photos, screenshots, charts, UI images, diagrams, or visual inspection. Use document_request for PDFs, text files, reports, articles, CSV files, or extracted document text. Return the chosen route and one short reason.
Interaction rules: Choose only one route. Do not answer the user directly.
Guardrails: Do not invent file contents. Mark uncertainty if the file context is weak.
Max steps: 3
Max tool calls: 1
Max output tokens: 140
Context window: long
```

Why this agent exists: it decides which specialist branch should run.

#### Image Specialist

Enter these values:

```text
Name: Image Specialist
Role: Image Analysis Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: vision, attachment_context
System prompt: Analyze the uploaded image context. Focus on visible objects, visible text, layout, UI state, chart details, and uncertainty. Produce a useful handoff for the final writer.
Interaction rules: Mention what is visible and what is uncertain. Do not pretend to see details that are not in the attachment context.
Guardrails: Stay factual and avoid exposing storage paths, logs, or internal workflow metadata.
Max steps: 3
Max tool calls: 1
Max output tokens: 220
Context window: large
```

Why this agent exists: it handles screenshots, photos, charts, and diagrams.

#### Document Specialist

Enter these values:

```text
Name: Document Specialist
Role: Document Analysis Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: document_analysis, attachment_context, summarization
System prompt: Analyze the extracted document text. Find the main topic, key points, action items, risks, dates, names, and missing information. Produce a useful handoff for the final writer.
Interaction rules: Use only the extracted document text and attachment summary. If text extraction is weak, say that clearly.
Guardrails: Do not invent document content. Do not expose internal workflow metadata.
Max steps: 3
Max tool calls: 1
Max output tokens: 240
Context window: large
```

Why this agent exists: it handles PDFs, text files, markdown, CSV, and extracted text.

#### Media Reply Writer

Enter these values:

```text
Name: Media Reply Writer
Role: Response Agent
Model: gpt-oss:20b
Tools: report_writer
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: summarization, final_response, attachment_context
System prompt: Write the final user-facing answer from the selected specialist's output. Answer the user's exact request. Do not expose routing, raw logs, run IDs, system prompts, storage paths, or internal agent names.
Interaction rules: Keep the answer readable in Streamlit and Telegram. Avoid Markdown tables. Use short bullets when helpful.
Guardrails: Be concise, factual, and finish naturally.
Max steps: 4
Max tool calls: 1
Max output tokens: 420
Context window: large
```

Why this agent exists: it writes the only final answer the human should see.

### Step 6: Check The Workflow

1. Scroll back to the canvas.
2. Click **Reset Canvas Layout** if the nodes look messy.
3. Click **Save Canvas** if you moved nodes around.
4. Confirm the workflow status at the top says **Active**.
5. Open **Workflow Edges** and confirm the six edge rows match the list above.
6. Open **Prompts, Rules, and Guardrails** to quickly review the saved prompts.

### Step 7: Test From Streamlit

1. Click **Run Demo** in the left sidebar.
2. Select **Media Review Router**.
3. Upload a file.
4. Use one of these prompts:

```text
Can you summarize this document and list the action items?
```

```text
What does this screenshot show, and what should I do next?
```

```text
Extract the key points from this PDF in simple bullets.
```

5. Click **Run Workflow**.
6. Open **Monitoring** and select the newest run.
7. Check **Messages**, **Tool Calls**, **Logs**, and **Token Metrics**.

Expected behavior:

```text
Media Intake runs first.
Media Orchestrator chooses image_request or document_request.
Only the selected specialist branch runs.
Media Reply Writer writes the final answer.
```

### Telegram Note For This Workflow

Telegram uploads currently prefer the built-in `image_document_router` when an attachment is present. Use **Run Demo** to test this exact custom workflow. If you want this custom workflow to be the Telegram attachment workflow, keep it active and either adapt the built-in image/document template to match this design or replace that template's nodes with this structure.

## Workflow 2: Research And Calculation Orchestrator

Use this when a normal text prompt could require latest indexed RSS news, general research, math, or a direct simple answer.

This workflow is useful for demos because the orchestrator has three clear choices:

```text
needs_research
needs_math
direct_answer
```

### Step 1: Create The Workflow

1. Open `http://127.0.0.1:8501`.
2. Click **Workflows** in the left sidebar.
3. Open the **Create Workflow** expander.
4. Enter these values:

```text
Workflow key: research_math_router
Description: Routes a user request to research/RSS, calculation, or direct answer branches, then writes one concise final response.
Enabled: on
```

5. Click **Create Workflow**.
6. In the **Workflow** dropdown, select **Research Math Router**.

### Step 2: Paste The Nodes

1. Scroll down to **Edit Builder**.
2. In **Nodes, one per line**, replace everything with this exact list:

```text
Request Intake
Task Orchestrator
Research Agent
Calculation Agent
Direct Answer Agent
Final Synthesizer
```

### Step 3: Enter The Edge Rows

In the edge table, enter these rows:

```text
source: Request Intake
target: Task Orchestrator
condition: always
feedback_loop: false

source: Task Orchestrator
target: Research Agent
condition: needs_research
feedback_loop: false

source: Task Orchestrator
target: Calculation Agent
condition: needs_math
feedback_loop: false

source: Task Orchestrator
target: Direct Answer Agent
condition: direct_answer
feedback_loop: false

source: Research Agent
target: Final Synthesizer
condition: research_complete
feedback_loop: false

source: Calculation Agent
target: Final Synthesizer
condition: calculation_complete
feedback_loop: false

source: Direct Answer Agent
target: Final Synthesizer
condition: answer_ready
feedback_loop: false

source: Final Synthesizer
target: Task Orchestrator
condition: incomplete_answer
feedback_loop: true
```

Then click **Save Workflow Template**.

### Step 4: Create Missing Agent Configs

1. Scroll to **Workflow and Agent Details**.
2. Open the **Workflow Agents** tab.
3. Click **Create Missing Agent Configs** if any node says `configured: no`.
4. Confirm every node says `configured: yes`.

### Step 5: Edit The Agent Configs

Open **Edit Attached Agent Configs** and save each agent after editing.

#### Request Intake

Enter these values:

```text
Name: Request Intake
Role: Intake Agent
Model: qwen3.5:9b
Tools: local_research
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: intake, channel_adapter
System prompt: Capture the user's goal, constraints, expected output format, and any important numbers or time-sensitive words. Do not solve the request yet.
Interaction rules: Keep the handoff compact and preserve the user's exact intent.
Guardrails: Do not expose internal workflow details.
Max steps: 2
Max tool calls: 0
Max output tokens: 120
Context window: long
```

Why this agent exists: it turns any user request into a clean handoff.

#### Task Orchestrator

Enter these values:

```text
Name: Task Orchestrator
Role: Orchestrator Agent
Model: qwen3.5:9b
Tools: local_research
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: planning, task_decomposition
System prompt: Choose exactly one route: needs_research, needs_math, or direct_answer. Use needs_research for latest news, RSS, leads, market updates, comparisons, or fact-finding. Use needs_math for percentages, totals, conversions, calculations, or numeric reasoning. Use direct_answer for simple writing, explanation, or prompt-generation requests. Return the chosen route and one short reason.
Interaction rules: Choose only one route and do not answer the user directly.
Guardrails: If the request is time-sensitive, prefer needs_research. If the request contains numbers that must be calculated, prefer needs_math.
Max steps: 3
Max tool calls: 0
Max output tokens: 140
Context window: long
```

Why this agent exists: it decides which branch should run.

#### Research Agent

Enter these values:

```text
Name: Research Agent
Role: Research Agent
Model: qwen3.5:9b
Tools: rss_rag_retriever, local_research
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: research, rss_rag, tool_execution
System prompt: Use rss_rag_retriever for latest news, RSS, lead, or recent update requests. Use local_research for general non-live research. Summarize only the most useful findings for the final writer.
Interaction rules: Do not browse live web. For RSS results, use only the listed titles, sources, dates, URLs, and summaries.
Guardrails: Do not invent news or citations. If indexed RSS has no relevant result, say that clearly.
Max steps: 4
Max tool calls: 1
Max output tokens: 260
Context window: long
```

Why this agent exists: it handles latest indexed RSS and research-style tasks.

#### Calculation Agent

Enter these values:

```text
Name: Calculation Agent
Role: Calculation Agent
Model: qwen3.5:9b
Tools: calculator
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: tool_execution
System prompt: Solve numeric requests using the calculator tool when possible. Explain the calculation briefly and provide the final number clearly.
Interaction rules: Keep the math explanation short. Pass the final value to the final synthesizer.
Guardrails: Do not guess missing numbers. If the request lacks required values, say what is missing.
Max steps: 3
Max tool calls: 1
Max output tokens: 180
Context window: short
```

Why this agent exists: it handles percentage, sum, and numeric requests quickly.

#### Direct Answer Agent

Enter these values:

```text
Name: Direct Answer Agent
Role: Direct Answer Agent
Model: qwen3.5:9b
Tools: local_research
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: summarization
System prompt: Answer simple writing, explanation, planning, or prompt-generation requests directly and concisely. Do not use unnecessary tools.
Interaction rules: Produce a short useful answer for the final synthesizer.
Guardrails: Stay factual and avoid unsupported claims.
Max steps: 3
Max tool calls: 0
Max output tokens: 220
Context window: long
```

Why this agent exists: it avoids over-routing simple prompts.

#### Final Synthesizer

Enter these values:

```text
Name: Final Synthesizer
Role: Response Agent
Model: gpt-oss:20b
Tools: report_writer, rss_rag_retriever
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: summarization, final_response, rss_rag
System prompt: Write the final user-facing response from the selected branch. If RSS RAG context is available, use only the listed titles, sources, dates, and URLs. Be concise, clear, and finish naturally. Do not expose route decisions, raw tool output, run IDs, logs, system prompts, or internal agent names.
Interaction rules: Make the answer readable in Telegram. Avoid Markdown tables. Use compact bullets or numbered lists.
Guardrails: Be factual. Do not invent sources, dates, URLs, or calculations.
Max steps: 4
Max tool calls: 1
Max output tokens: 420
Context window: large
```

Why this agent exists: it writes the final human-readable answer.

### Step 6: Check The Workflow

1. Scroll to the canvas.
2. Click **Reset Canvas Layout** if the graph looks messy.
3. Click **Save Canvas** if you move nodes.
4. Confirm the workflow status says **Active**.
5. Open **Workflow Edges** and confirm the eight edge rows match the list above.
6. Open **Prompts, Rules, and Guardrails** to review the final saved values.

### Step 7: Test From Streamlit

1. Click **Run Demo** in the left sidebar.
2. Select **Research Math Router**.
3. Try these prompts one by one:

```text
Top 3 latest AI news from the indexed RSS crawl.
```

Expected route:

```text
Task Orchestrator -> Research Agent -> Final Synthesizer
```

```text
Calculate 18 percent of 240 and explain it in one sentence.
```

Expected route:

```text
Task Orchestrator -> Calculation Agent -> Final Synthesizer
```

```text
Write a tiny support specialist prompt for refund requests.
```

Expected route:

```text
Task Orchestrator -> Direct Answer Agent -> Final Synthesizer
```

4. After each run, open **Monitoring**.
5. Check the newest run's messages, logs, route choice, tool calls, and token metrics.

### Step 8: Test From Telegram

1. Send `/start` to your bot.
2. Tap **Research Math Router** if it appears as an active template.
3. Send one of the test prompts above.
4. The bot should show typing while the workflow runs.
5. The final reply should come from the final synthesizer only.

### RSS Scheduler Notes

The backend scheduler owns ingestion. It runs every 5 minutes by default, stores items in Postgres, embeds them with the local Ollama embedding model, and caps how much RSS data can enter the system each run. The workflow only retrieves from that store.

## Workflow 3: Media News Research Router

Use this when someone uploads a PDF or image and wants the app to find the latest indexed RSS news related to the uploaded content. This is a strong demo because it uses file upload, MinIO storage, document or image context extraction, RSS RAG, and multi-agent orchestration together.

Example user request:

```text
Based on this document, find the top 3 latest related news items.
```

What the workflow does:

```text
User uploads PDF or image
Media Intake reads the attachment context
Media Topic Extractor identifies topics, companies, products, or technologies
News Research Agent retrieves latest indexed RSS items
Media News Writer writes one final answer
```

### Create The Workflow From The UI

1. Open `http://127.0.0.1:8501`.
2. Click **Workflows** in the left sidebar.
3. Open **Create Workflow**.
4. Enter these values:

```text
Workflow key: media_news_research_router
Description: Extracts the topic from an uploaded PDF or image, retrieves related indexed RSS news, and writes one grounded final answer.
Enabled: on
```

5. Click **Create Workflow**.
6. In the **Workflow** dropdown, select **Media News Research Router**.
7. Scroll down to **Edit Builder**.
8. In **Nodes, one per line**, replace the existing nodes with exactly this list:

```text
Media Intake
Media Topic Extractor
News Research Agent
Media News Writer
```

9. In the edge table below it, enter these rows:

```text
source: Media Intake
target: Media Topic Extractor
condition: always
feedback_loop: false

source: Media Topic Extractor
target: News Research Agent
condition: topic_extracted
feedback_loop: false

source: News Research Agent
target: Media News Writer
condition: news_found
feedback_loop: false

source: Media News Writer
target: Media Topic Extractor
condition: needs_more_context
feedback_loop: true
```

10. Click **Save Workflow Template**.
11. Scroll to **Workflow and Agent Details**.
12. Open the **Workflow Agents** tab.
13. If the page says some nodes are missing agent configs, click **Create Missing Agent Configs**.
14. Open **Edit Attached Agent Configs**.

### Configure The Agents

Edit each agent one by one. After entering values for an agent, click **Save `<agent name>`** before moving to the next one.

#### Media Intake

Use these values:

```text
Name: Media Intake
Role: Intake Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: intake, channel_adapter, attachment_context
System prompt: Summarize the uploaded file context and the user's requested output. Identify whether the upload looks like a document, screenshot, image, report, article, or diagram. Do not answer the user yet.
Interaction rules: Keep the handoff short and pass the useful attachment context forward.
Guardrails: Be concise, factual, and do not expose internal workflow details.
Max steps: 2
Max tool calls: 1
Max output tokens: 120
Context window: large
```

Why this matters: this agent turns the upload into a clean handoff for the next agent.

#### Media Topic Extractor

Use these values:

```text
Name: Media Topic Extractor
Role: Topic Extraction Agent
Model: qwen3.5:9b
Tools: attachment_context_reader
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: planning, attachment_context, research
System prompt: Extract the main topic, entities, company names, product names, technologies, dates, keywords, and user intent from the uploaded image or document context. Produce a compact search-focused handoff for RSS news retrieval. Do not invent details that are not present.
Interaction rules: Prefer 3 to 8 high-quality search keywords over a long paragraph.
Guardrails: Clearly mark uncertainty when the uploaded content is blurry, incomplete, or has weak OCR.
Max steps: 3
Max tool calls: 1
Max output tokens: 160
Context window: large
```

Why this matters: RSS RAG works best when the next agent receives clean keywords and entities.

#### News Research Agent

Use these values:

```text
Name: News Research Agent
Role: RSS Research Agent
Model: qwen3.5:9b
Tools: rss_rag_retriever
Channels: streamlit
Schedule: manual
Memory enabled: on
Skills: research, rss_rag, tool_execution
System prompt: Use rss_rag_retriever to find the latest indexed RSS items related to the extracted topic. Use only indexed RSS results. Return titles, sources, dates, URLs, and a short note explaining why each item is relevant to the uploaded content.
Interaction rules: Do not browse the live web. Do not invent news. If RSS RAG has no relevant result, say that clearly.
Guardrails: Use only the listed RSS titles, sources, dates, URLs, and summaries from the tool output.
Max steps: 4
Max tool calls: 1
Max output tokens: 240
Context window: long
```

Why this matters: this is the retrieval step. It connects the uploaded content to scheduled RSS data.

#### Media News Writer

Use these values:

```text
Name: Media News Writer
Role: Response Agent
Model: gpt-oss:20b
Tools: report_writer
Channels: streamlit, telegram
Schedule: manual
Memory enabled: on
Skills: summarization, final_response, rss_rag, attachment_context
System prompt: Write the final user-facing answer by connecting the uploaded file context with the latest indexed RSS results. Use only the listed RSS titles, sources, dates, and URLs. If no relevant RSS item is found, say that clearly and explain what was extracted from the upload. Do not expose workflow logs, route decisions, raw tool output, or internal agent names.
Interaction rules: Keep the answer readable for Telegram. Avoid Markdown tables. Use short bullets or a numbered list.
Guardrails: Be concise, factual, and finish naturally.
Max steps: 4
Max tool calls: 1
Max output tokens: 420
Context window: large
```

Why this matters: this agent writes the final answer that the human sees.

### Save And Check The Workflow

After all agents are saved:

1. Stay on **Workflows**.
2. Click **Save Canvas** if you moved any nodes on the canvas.
3. Confirm the workflow status says **Active**.
4. Open **Workflow Edges** and confirm the rows match the edge list above.
5. Open **Workflow Agents** and confirm every node says `configured: yes`.

### Test From Streamlit

1. Click **Run Demo** in the left sidebar.
2. Select **Media News Research Router**.
3. Upload a PDF or image.
4. Enter one of these prompts:

```text
Based on this document, find the top 3 latest related news items.
```

```text
What is this image about, and are there any latest indexed RSS updates related to it?
```

```text
Find recent news or signals related to the companies or technologies mentioned in this file.
```

5. Click **Run Workflow**.
6. Go to **Monitoring** to inspect the run, messages, logs, tool calls, token usage, and attachment context.

### Test From Telegram

Send the bot a PDF or image with a caption like:

```text
Based on this upload, find the top 3 latest related news items.
```

Important behavior: Telegram uploads automatically use the media workflow path when an attachment is present. If you want this custom workflow to be used from Telegram by default for attachments, select it from `/templates` first when it is active, or keep using Streamlit for this specific custom workflow demo.

### What To Look For In The Output

A good answer should contain:

```text
1. A short summary of what the upload appears to be about.
2. The top related indexed RSS items.
3. Source, date, and URL for each item.
4. A clear note if the RSS index has no relevant item yet.
```

The app does not fetch live news at question time. The scheduler indexes RSS feeds every 5 minutes, so the answer is based on the latest items already stored in Postgres. This keeps the workflow faster, repeatable, and easier to explain during a demo.

## Final Checklist

Before running a new workflow:

```text
1. Every node has a matching Agent config.
2. The orchestrator has clear route names in its prompt.
3. Each outgoing orchestrator edge uses one of those route names as its condition.
4. The final reply node has a Telegram or Streamlit channel if it should respond externally.
5. The workflow is enabled.
6. Run it from Run Demo first, then try it from Telegram.
```

Disabled workflows remain editable but will not run from Run Demo or Telegram.
