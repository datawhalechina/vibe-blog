<div align="center">

> **Alpha software:** Vibe Blog is under active development. Features and data formats may change. Please report problems through [GitHub Issues](https://github.com/datawhalechina/vibe-blog/issues).

<img width="220" src="docs/assets/brand/vibe-blog.png" alt="Vibe Blog logo">

# Vibe Blog

_Turn complex technology into long-form stories people can understand._

**English | [简体中文](README.zh-CN.md)**

[![Version](https://img.shields.io/badge/version-v0.1.0-4CAF50.svg)](https://github.com/datawhalechina/vibe-blog)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42b883?logo=vuedotjs&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)
![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-1f2937)

An AI writing workspace that coordinates research, outlining, drafting, code examples, illustrations, review, and document assembly for substantial technical articles.

[Quick start](#quick-start) · [Architecture](#architecture) · [Testing](#testing) · [Changelog](CHANGELOG.md)

</div>

## Overview

Vibe Blog is a Flask + Vue 3 application built around a LangGraph multi-agent workflow. Give it a topic or supporting material, choose the desired article shape, and follow generation through real-time Server-Sent Events (SSE). The result is stored as Markdown and can be reviewed, edited, and exported from the web interface.

The project is designed for technical writers, developer advocates, educators, product teams, and learners who need more depth than a short chat response can provide.

```text
Topic and source material
        ↓
Research and knowledge-gap discovery
        ↓
Outline planning and optional confirmation
        ↓
Section writing, questioning, and review
        ↓
Code examples and visual assets
        ↓
Assembly, history, and export
```

## What It Does

| Area | Current capability |
| --- | --- |
| Research | Multi-round web research, source curation, optional deep scraping, and local material retrieval |
| Planning | Structured outlines, audience and learning-objective analysis, and an outline confirmation flow |
| Writing | Section-by-section generation with depth checks, revision, fact checking, and style cleanup |
| Visuals | Mermaid diagrams plus optional AI-generated covers, illustrations, and cover animation |
| Knowledge | File parsing, reusable knowledge material, article history, and blog-to-book aggregation |
| Operations | SSE progress, cancellation, task recovery, dashboard views, and scheduled generation |
| Observability | Structured task logs, token tracking, and optional Langfuse tracing |

Optional and experimental integrations are disabled or inactive until their corresponding environment variables and feature flags are configured. See [`backend/.env.example`](backend/.env.example) for the authoritative list.

## Product Preview

### Writing Workspace

![Vibe Blog home screen](docs/assets/screenshots/首页图.png)

Start with a topic, select an article type and length, attach material when needed, and inspect the generated outline before the full workflow continues.

### Article Output

![Generated technical article](docs/assets/screenshots/技术博客结果图.png)

The detail view renders Markdown, syntax-highlighted code, Mermaid diagrams, references, and generated media in one reading surface.

### Book Aggregation

<table>
<tr>
<td width="50%"><img src="docs/assets/screenshots/book-reader-preview.png" alt="Book library"></td>
<td width="50%"><img src="docs/assets/screenshots/book-details-reader-preview.png" alt="Book reader"></td>
</tr>
</table>

Related articles can be organized into a book structure and read through the built-in book interface. Book scanning is controlled by `BOOK_SCAN_ENABLED`.

## Multi-Agent Workflow

![Multi-agent architecture](docs/assets/diagrams/multi-agent-architecture.png)

The workflow uses specialized agents with a shared typed state:

| Agent group | Responsibility |
| --- | --- |
| Researcher and Search Coordinator | Gather sources, refine queries, and address knowledge gaps |
| Planner | Convert evidence and objectives into a structured outline |
| Writer | Draft coherent sections for the target audience |
| Questioner, Reviewer, and Fact Checker | Challenge depth, quality, consistency, and factual support |
| Coder and Artist | Produce code examples, diagrams, and optional generated media |
| Humanizer, Voice Checker, and Thread Checker | Improve tone, voice, and cross-section continuity |
| Assembler and Summary Generator | Build the final document and derived summary |

Agents are orchestrated by LangGraph and communicate through a shared Pydantic/TypedDict state contract. The browser receives progress and terminal events over SSE.

## Architecture

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Vue 3, Vite, Pinia, TipTap | Generation controls, live progress, editing, history, books, and dashboard |
| API | Flask, Pydantic | HTTP/SSE endpoints, validation, task lifecycle, and compatibility boundaries |
| Workflow | LangGraph, LangChain | Agent orchestration, retries, context management, and tool execution |
| Services | Python service packages | LLMs, research, documents, media, publishing, review, and scheduling |
| Runtime artifacts | `var/` by default | Logs, generated files, uploads, caches, and screenshots |
| Persistent data | `backend/data/` | SQLite databases for articles, tasks, schedules, and writing sessions |

```text
vibe-blog/
├── backend/                 # Flask API, agents, services, tests
│   └── data/                # Persistent SQLite databases
├── frontend/                # Vue 3 application and Vitest tests
├── tests/e2e/               # Playwright end-to-end scenarios
├── docker/                  # Local and container startup tooling
├── docs/                    # Architecture, testing, and project assets
└── var/                     # Local runtime data (created as needed)
```

Detailed boundary documentation lives in [`docs/architecture/`](docs/architecture/).

## Quick Start

### Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer with npm
- API credentials for at least one configured text model provider
- `lsof` on macOS/Linux when using the local startup script

### 1. Clone and install

```bash
git clone https://github.com/datawhalechina/vibe-blog.git
cd vibe-blog

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate`.

### 2. Configure

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`. A minimal OpenAI-compatible configuration looks like this:

```env
AI_PROVIDER_FORMAT=openai
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://your-provider.example/v1
TEXT_MODEL=your-model-name
```

Do not commit `.env` or real credentials.

### 3. Start frontend and backend on macOS, Linux, or WSL

```bash
bash docker/start-local.sh
```

The script installs missing frontend dependencies, starts both services, and writes logs under `${VIBE_RUNTIME_DIR:-var}/logs/`.

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:5001>

Press `Ctrl+C` in the startup terminal to stop both services. The script requires Bash and `lsof`, claims ports 5173 and 5001, and terminates processes already using them.

### 4. Start manually, including on Windows

Run the backend and frontend in separate terminals:

```bash
# Terminal 1
cd backend
python app.py
```

```bash
# Terminal 2
cd frontend
npm install
npm run dev
```

The same frontend and backend URLs apply. Stop each process in its own terminal.

### Docker

Use the checked-in Compose stack after creating `backend/.env`:

```bash
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
```

- Reverse proxy: <http://localhost>
- Frontend direct access: <http://localhost:3000>
- Backend direct access: <http://localhost:5000>

The current Nginx configuration serves HTTP on port 80. Configure TLS in Nginx before exposing the application publicly.

## Configuration

The checked-in [`backend/.env.example`](backend/.env.example) is the source of truth. Key groups include:

| Group | Representative variables | Required? |
| --- | --- | --- |
| Text model | `AI_PROVIDER_FORMAT`, `OPENAI_API_KEY`, `OPENAI_API_BASE`, `TEXT_MODEL` | Yes, for the OpenAI-compatible path |
| Research | `ZAI_SEARCH_API_KEY`, `SERPER_API_KEY`, `JINA_API_KEY` | Optional |
| Documents | `MINERU_TOKEN`, local material settings | Optional |
| Media | `NANO_BANANA_API_KEY`, OSS and video settings | Optional |
| Tracing | `TRACE_ENABLED`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Optional |
| Feature flags | Book, XHS, derivatives, deep scraping, and agent switches | Optional |

Keep credentials in `backend/.env`. Generated artifacts, logs, uploads, and caches belong under `var/` unless `VIBE_RUNTIME_DIR` is set; persistent SQLite databases remain under `backend/data/`.

## Testing

### Frontend unit tests

```bash
cd frontend
npm test
```

### Backend tests

```bash
cd backend
python -m pytest tests/ -v
```

### End-to-end tests

Start the application first, then run from the repository root:

```bash
RUN_E2E_TESTS=1 python -m pytest tests/e2e/ -v
```

Set `E2E_HEADED=1` to show the browser. Screenshots are written to the configured runtime output area. More testing notes are available in [`docs/testing/README.md`](docs/testing/README.md).

## Contributing

Issues and pull requests are welcome:

- Report bugs or propose features in [GitHub Issues](https://github.com/datawhalechina/vibe-blog/issues).
- Keep implementation work scoped and include tests proportional to the change.
- Update [`CHANGELOG.md`](CHANGELOG.md) with every commit, following the repository contribution rules.

For Datawhale project support and governance, see the [Datawhale Open-Source Project Management Committee](https://github.com/datawhalechina/DOPMC).

<div align="center">
<img width="260" src="docs/assets/community/project-wechat.png" alt="Vibe Blog community QR code">
</div>

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](LICENSE).
