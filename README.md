# Simplon RAG Sample

---

Chatbot de support intelligent basé sur une architecture RAG (Retrieval-Augmented Generation),
utilisant LangChain, LangGraph, PostgreSQL/pgvector pour le stockage vectoriel,
et Google Vertex AI pour les embeddings et l'inférence LLM.

## Features

- **Document Ingestion** - PDF upload with SHA-256 deduplication, chunking, and embedding
- **RAG Pipeline** - Semantic retrieval via pgvector cosine similarity + LLM generation
- **LangGraph Agent** - Stateful multi-step graph: routing, retrieval, generation, history
- **Vertex AI** - `text-multilingual-embedding-002` (768 dims) for embeddings, `gemini-2.5-flash` for LLM
- **PostgreSQL + pgvector** - HNSW index for fast approximate nearest-neighbour search
- **FastAPI REST API** - 8 endpoints under `/api/v1` for ingestion, chat, and evaluation
- **Ragas Evaluation** - Faithfulness, answer relevancy, and context recall metrics

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python >= 3.14 |
| Package Manager | uv |
| LLM Framework | LangChain + LangGraph |
| LLM / Embeddings | Vertex AI (Gemini 2.5 Flash / text-multilingual-embedding-002) |
| Vector Store | PostgreSQL + pgvector |
| ORM / Migrations | SQLAlchemy (async) + Alembic |
| API | FastAPI + uvicorn |
| RAG Evaluation | Ragas |
| CI/CD | GitHub Actions + Workload Identity Federation |

## Quickstart with Docker

```bash
# 1. Configure environment
cp api/.env.example api/.env

# 2. Start everything in development mode
docker compose up -d

# 3. Open the UI
open http://localhost:8501       # Streamlit chat
# API docs:    http://localhost:8000/docs
# API health:  http://localhost:8000/api/v1/health

# 4. Tear down
docker compose down
docker compose down -v           # also drop the postgres volume
```

## Local installation (without Docker)

```bash
cp api/.env.example api/.env

cd api
uv sync --extra dev
uv run alembic upgrade head
cd ..

cd frontend
uv sync
cd ..

pre-commit install
```

## Usage (local)

```bash
cd api && uv run python main.py
cd frontend && uv run streamlit run src/app/app.py
```

### CLI Tools

```bash
cd api

# Ingest PDFs from local directory
uv run python -m rag.cli.ingest --docs-dir path/to/pdfs

# Ingest PDFs from GCS bucket (production)
STORAGE_ENDPOINT_URL="" STORAGE_BUCKET="simplon-floralex-rag" \
  uv run python -m rag.cli.ingest

# Run Ragas evaluation
uv run python -m rag.cli.eval
uv run python -m rag.cli.eval --samples path/to/samples.json
```

## Development

```bash
cd api && uv run pytest
cd api && uv run ruff check src/
git commit -m "feat: ..."
```

---

## ☁️ Déploiement GCP

### URLs de production

| Service | URL |
|---------|-----|
| API | <https://api-976732347859.europe-west1.run.app |
| Frontend | <https://frontend-976732347859.europe-west1.run.app |
| Health check | <https://api-976732347859.europe-west1.run.app/api/v1/health |

### Services GCP utilisés

| Service | Rôle |
|---------|------|
| Cloud Run | Héberge l'API FastAPI et le frontend Streamlit (scale-to-zero) |
| Cloud SQL | Base de données PostgreSQL + pgvector pour les embeddings et conversations |
| Cloud Storage | Stockage des PDFs du corpus (`gs://simplon-floralex-rag/corpus/`) |
| Artifact Registry | Registre Docker pour les images versionnées (v1 à v8) |
| Secret Manager | Gestion sécurisée des secrets (clé API, mot de passe BDD, utilisateur BDD) |
| Vertex AI | LLM `gemini-2.5-flash` et embeddings `text-multilingual-embedding-002` via IAM |
| Workload Identity Federation | Authentification GitHub Actions vers GCP sans clé JSON |

### Rôles IAM du service account `cloud-run-sa`

| Rôle | Justification |
|------|---------------|
| `roles/storage.objectUser` | Lire/écrire les PDFs dans GCS — pas `storage.admin` (accès limité au bucket) |
| `roles/cloudsql.client` | Connexion au socket Unix Cloud SQL — ne donne pas accès aux données de la base |
| `roles/secretmanager.secretAccessor` | Lecture seule des secrets — ne peut pas créer ni modifier |
| `roles/aiplatform.user` | Appeler les modèles Vertex AI — rôle minimal sans accès au training |
| `roles/iam.workloadIdentityUser` | Auth GitHub Actions via WIF — limité au repo du projet |

### Rollback d'une révision Cloud Run

```bash
# Lister les révisions disponibles
gcloud run revisions list --service=api --region=europe-west1

# Basculer 100% du trafic vers une révision précédente
gcloud run services update-traffic api \
  --to-revisions=NOM_REVISION=100 \
  --region=europe-west1
```

---

## Documentation

| File | Description |
|------|-------------|
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Maxime Lenne**
