# Simplon RAG Sample

<!-- markdownlint-disable -->
<p align="center">
  <strong>Sample RAG support chatbot — powered by RAG, LangChain, and Mistral</strong>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  </a>
  <a href="https://python-semantic-release.readthedocs.io/">
    <img src="https://img.shields.io/badge/semantic--release-python-e10079?logo=semantic-release" alt="semantic-release: python" />
  </a>
</p>
<!-- markdownlint-restore -->

---

Intelligent support chatbot example, built on a Retrieval-Augmented Generation (RAG) architecture
using LangChain, LangGraph, PostgreSQL/pgvector for vector storage, and Mistral for both
embeddings and LLM inference.

## Features

- **Document Ingestion** - PDF upload with SHA-256 deduplication, chunking, and embedding
- **RAG Pipeline** - Semantic retrieval via pgvector cosine similarity + LLM generation
- **LangGraph Agent** - Stateful multi-step graph: routing, retrieval, generation, history
- **Mistral AI** - `mistral-embed` (1024 dims) for embeddings, `mistral-large-latest` for LLM
- **PostgreSQL + pgvector** - HNSW index for fast approximate nearest-neighbour search
- **FastAPI REST API** - 8 endpoints under `/api/v1` for ingestion, chat, and evaluation
- **Ragas Evaluation** - Faithfulness, answer relevancy, and context recall metrics

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python >= 3.14 |
| Package Manager | uv |
| LLM Framework | LangChain + LangGraph |
| LLM / Embeddings | Mistral AI |
| Vector Store | PostgreSQL + pgvector |
| ORM / Migrations | SQLAlchemy (async) + Alembic |
| API | FastAPI + uvicorn |
| RAG Evaluation | Ragas |

## Quickstart with Docker

The fastest way to spin up the full stack (PostgreSQL + API + Streamlit UI):

```bash
# 1. Configure the Mistral API key (required)
cp api/.env.example api/.env
# Edit api/.env and set MISTRAL_API_KEY

# 2. Start everything in development mode (hot reload, source bind mounts)
docker compose up -d

# 3. Open the UI
open http://localhost:8501       # Streamlit chat
# API docs:    http://localhost:8000/docs
# API health:  http://localhost:8000/api/v1/health

# 4. Tear down
docker compose down              # keep data
docker compose down -v           # also drop the postgres volume
```

For a production-like build (multi-worker uvicorn, no source mounts, postgres
port hidden from the host):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Local installation (without Docker)

```bash
# Copy and configure environment
cp api/.env.example api/.env
# Edit api/.env with your API keys and DB connection

# Install API dependencies
cd api
uv sync --extra dev          # dev tools included

# Apply database migrations (requires a running PostgreSQL with pgvector)
uv run alembic upgrade head
cd ..

# Install frontend dependencies
cd frontend
uv sync
cd ..

# Install git hooks
pre-commit install
```

## Usage (local)

```bash
# Run API (from api/)
cd api && uv run python main.py
# API available at http://localhost:8000/api/v1

# Run the Streamlit chat UI (from frontend/)
cd frontend && uv run streamlit run src/app/app.py
# UI available at http://localhost:8501
```

### CLI Tools

Standalone entry points for ingestion and evaluation, runnable without the API
(useful for cron, CI, or one-off scripts). Run from `api/`.

```bash
cd api

# Ingest every PDF in data/docs/ (idempotent via SHA-256)
uv run python -m rag.cli.ingest
uv run python -m rag.cli.ingest --docs-dir path/to/pdfs

# Run Ragas evaluation against data/evaluation/samples.json
uv run python -m rag.cli.eval
uv run python -m rag.cli.eval --samples path/to/samples.json
```

## Development

```bash
# Run API tests (from api/)
cd api && uv run pytest

# Lint all files (from repo root)
uv run pymarkdownlnt scan --recurse .
uv run yamllint .

# Commit (Conventional Commits format)
git commit -m "feat: ..."
```

## Documentation

| File | Description |
|------|-------------|
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Maxime Lenne**
