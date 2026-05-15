# 2-Minute Startup

The full app is started from the sibling backend repo because Docker Compose owns the backend, frontend, and Postgres services.

## Prerequisites

- Docker Desktop is running.
- Ollama is installed and running on the host machine.
- Backend and frontend repos are sibling folders.

Pull the local models once:

```powershell
ollama pull gpt-oss:20b
ollama pull qwen3.5:9b
ollama pull qwen3-embedding:4b
ollama pull llava:7b
```

If Ollama is not already running:

```powershell
ollama serve
```

## Start Everything

```powershell
cd C:\Users\Admin\Desktop\codes\AgentFlowViz\AgentFlowViz-backend
docker compose up --build
```

Open:

```text
Frontend: http://127.0.0.1:8501
Backend health: http://127.0.0.1:8000/health
MinIO console: http://127.0.0.1:9001
```

## Optional Telegram

Configure Telegram in the backend `.env`, then restart Docker:

```env
TELEGRAM_BOT_TOKEN=your_botfather_token
TELEGRAM_ALLOWED_USER_IDS=your_numeric_telegram_user_id
```

```powershell
docker compose up -d --build
```

## Stop

```powershell
docker compose down
```

First Docker image builds or first Ollama model pulls can take longer. After that, startup should normally be quick.
