# Enterprise Multi-Tenant AI Chatbot Platform — Backend

A production-grade, reusable **chatbot engine** that embeds into many products
(ERP, CRM, HRM, Medical, School, Inventory, Accounting…). **One engine, many
products** — every tenant gets isolated users, documents, vector indexes, chat
history, settings and analytics.

Built with **FastAPI · PostgreSQL · SQLAlchemy · Alembic · Redis · Celery ·
Qdrant · Anthropic / OpenAI / Gemini · LangChain / LlamaIndex**.

The default LLM is **Claude `claude-opus-4-8`** with adaptive thinking and
streaming, behind a provider-agnostic abstraction so any tenant can switch
provider/model.

---

## 1. Folder structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, metrics, lifespan
│   ├── core/                    # config, db, redis, security, rbac, logging, exceptions
│   ├── models/                  # SQLAlchemy ORM (tenant-scoped tables)
│   ├── schemas/                 # Pydantic request/response models
│   ├── repositories/            # Tenant-scoped data access (isolation enforced here)
│   ├── services/                # Business logic (auth, chat, ingestion, memory, tools…)
│   ├── llm/                     # Provider abstraction (Anthropic/OpenAI/Gemini), pricing
│   ├── rag/                     # embeddings, chunking, extractors, vectorstore, retrieval, reranker
│   ├── security/                # prompt-injection / RAG-poisoning / output guards
│   ├── api/
│   │   ├── deps.py              # auth principal + RBAC dependencies
│   │   ├── middleware.py        # request-id, rate limit, security headers
│   │   └── v1/                  # auth, tenant, users, knowledge, documents, chat, search,
│   │                            # analytics, feedback, tools, admin, health
│   └── workers/                 # Celery app + ingestion/retraining tasks
├── alembic/                     # migrations
├── scripts/                     # init_db.py, seed.py
├── tests/                       # unit, security, RAG-eval, hallucination, citation, load
├── deploy/k8s/                  # Kubernetes manifests + HPA
├── Dockerfile · docker-compose.yml · Makefile · requirements.txt
```

## 2. Database schema (high level)

```
tenants ─┬─ tenant_settings (1:1, LLM/embedding/RAG config + encrypted keys)
         ├─ users ─── refresh_tokens (rotation registry) · api_keys · custom_roles
         ├─ knowledge_bases ─── documents ─┬─ document_chunks (mirror of Qdrant)
         │                                  └─ document_versions
         ├─ chat_sessions ─── messages ─── message_citations
         ├─ memories (session / user / tenant scope)
         ├─ tool_definitions (CRM/ERP/HR/… function calling)
         ├─ analytics_events · token_usage (cost ledger)
         ├─ feedback · review_queue (human-in-the-loop)
         └─ audit_logs
```

Every tenant-owned table carries `tenant_id`; the `TenantRepository` base filters
**every** query by it, and Qdrant searches are filtered by `tenant_id` payload —
**no cross-tenant data leakage**.

## 3. Production architecture diagram

```
                        ┌─────────────┐
        Clients ─────▶  │  FastAPI    │  REST + WebSocket (SSE streaming)
   (web / mobile / SDK) │  (api pods) │  JWT + refresh rotation + RBAC + rate limit
                        └─────┬───────┘
              ┌───────────────┼─────────────────────────┐
              ▼               ▼                          ▼
        ┌──────────┐    ┌──────────┐              ┌──────────────┐
        │PostgreSQL│    │  Redis   │              │   Qdrant     │
        │ (state)  │    │cache/rate│              │ vector index │
        └──────────┘    │  /memory │              │ per-tenant   │
                        └────┬─────┘              └──────────────┘
                             │ broker
                        ┌────▼─────┐    ingestion pipeline
                        │  Celery  │───▶ extract→chunk→embed→index→version
                        │ workers  │
                        └────┬─────┘
                             ▼
                  ┌────────────────────┐     ┌──────────────────────────┐
                  │ S3 / MinIO (docs)  │     │ LLM providers            │
                  └────────────────────┘     │ Anthropic / OpenAI/Gemini│
                                             └──────────────────────────┘
   Observability: structlog (JSON) · Prometheus /metrics · OpenTelemetry · Sentry
```

## 4. Quick start

> **Requires Python 3.11 or 3.12 — _not_ 3.13.** The pinned `tokenizers`
> (via `FlagEmbedding` / `sentence-transformers`) has no wheel for 3.13 and falls
> back to a Rust source build whose `pyo3 0.21.2` caps at Python 3.12, so the
> install aborts with _"the configured Python interpreter version (3.13) is newer
> than PyO3's maximum supported version (3.12)"_. See **§11 Troubleshooting**.

```bash
cd backend
cp .env.example .env          # set ANTHROPIC_API_KEY / OPENAI_API_KEY at minimum
docker compose up --build     # api, worker, flower, postgres, redis, qdrant, minio
# api → http://localhost:8000/docs    flower → http://localhost:5555
```

### Local (without Docker) — recommended: **uv** ⚡

[uv](https://docs.astral.sh/uv/) is a drop-in, much faster replacement for
`pip`/`venv`. It also **fetches Python 3.12 for you**, so you never hit the
3.13 / `tokenizers` build wall. Install it once
(`winget install astral-sh.uv` on Windows, or
`curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux), then:

```bash
cd backend
uv venv --python 3.12          # creates .venv, auto-downloads CPython 3.12 if missing
                               # add --clear if a stale .venv already exists (e.g. a 3.13/3.14 one)
uv pip install -r requirements.txt

# scripts/ import the `app` package from the backend root, so put it on PYTHONPATH first:
#   PowerShell:  $env:PYTHONPATH = "."
#   bash/zsh:    export PYTHONPATH=.
# `uv run` executes inside .venv — no activation needed, and works the same on every OS:
uv run python scripts/init_db.py    # needs Postgres up (e.g. `docker compose up postgres redis qdrant`)
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload
```

```bash
# Second terminal — start the Celery worker:
uv run celery -A app.workers.celery_app.celery_app worker -Q ingestion,default --loglevel=info
```

`uv run` resolves commands from `.venv` automatically, so there's no PowerShell
`&&` issue and no "command not recognized" — it works identically in PowerShell,
bash, and zsh.

> **Check the venv's Python:** `uv venv` reuses whatever Python it last resolved.
> If `.venv\Scripts\python.exe --version` reports 3.13/3.14, recreate it with
> `uv venv --python 3.12 --clear` before installing.

### Local (without Docker) — plain `pip` / `venv`

If you'd rather not use uv. **Requires Python 3.11 or 3.12 — not 3.13** (see §11).

macOS / Linux:

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py && python scripts/seed.py
uvicorn app.main:app --reload
# second terminal (activate venv again first):
celery -A app.workers.celery_app.celery_app worker -Q ingestion,default --loglevel=info
```

Windows PowerShell — PowerShell has no `&&` (use `;`), and you must **activate
the venv** so `uvicorn`/`celery` resolve:

```powershell
py -3.12 -m venv venv            # 3.12, NOT 3.13
.\venv\Scripts\Activate.ps1      # prompt should now show (venv)
pip install -r requirements.txt
python scripts/init_db.py ; python scripts/seed.py
python -m uvicorn app.main:app --reload
```

```powershell
# Second terminal — activate again, then start the worker:
.\venv\Scripts\Activate.ps1
python -m celery -A app.workers.celery_app.celery_app worker -Q ingestion,default --loglevel=info
```

Seed credentials: tenant `demo`, `admin@demo.test` / `demo12345` (super_admin).

### Database setup & migrations

FastAPI/SQLAlchemy has no built-in `makemigrations`/`migrate` — this project uses
**[Alembic](https://alembic.sqlalchemy.org/)**, the standard SQLAlchemy migration
tool. Mapping for anyone coming from Django:

| Django                           | Here (Alembic)                                   |
| -------------------------------- | ------------------------------------------------ |
| `manage.py makemigrations`     | `alembic revision --autogenerate -m "message"` |
| `manage.py migrate`            | `alembic upgrade head`                         |
| `manage.py migrate <app> 0001` | `alembic downgrade <revision>`                 |
| show migration state             | `alembic current` / `alembic history`        |

**Prerequisite (do this once):** Postgres must be running, and the role +
database in your `.env` must exist. With the values shipped in `.env`
(`POSTGRES_USER=ChatBot`, `POSTGRES_DB=postgresql`), connect as a superuser
(`psql -h localhost -U postgres`) and run — **the double quotes matter**, they
preserve the capital letters in `ChatBot`:

```sql
CREATE ROLE "ChatBot" WITH LOGIN PASSWORD 'IrfaN@7368';
CREATE DATABASE "postgresql" OWNER "ChatBot";
GRANT ALL PRIVILEGES ON DATABASE "postgresql" TO "ChatBot";
```

> Note: the app connects with the **async** driver (`asyncpg`); Alembic connects
> with the **sync** driver (`psycopg2`). Both URLs are derived automatically from
> the same `POSTGRES_*` settings — you don't configure them separately.

You have **two ways** to create the schema:

**Option A — quick create-all (local dev).** Creates every table in one shot from
the models, with no migration history. Fine for development; not for production.

```bash
uv run python scripts/init_db.py     # create all tables
uv run python scripts/seed.py        # optional: demo tenant + admin
```

**Option B — Alembic migrations (recommended / production).** Run against an
**empty** database so the first revision captures the full schema:

```bash
# 1. makemigrations — generate a revision by diffing models vs. the DB
uv run alembic revision --autogenerate -m "init"
#    → review the new file in alembic/versions/ before applying

# 2. migrate — apply all pending revisions
uv run alembic upgrade head
```

Whenever you change a model afterwards, repeat: `alembic revision --autogenerate -m "describe change"`, review the generated file, then `alembic upgrade head`.
Useful extras: `alembic downgrade -1` (undo last), `alembic current` (show applied
revision), `alembic history` (list all).

> **Don't mix the two on the same DB.** If you already ran `init_db.py`, the tables
> exist but Alembic has no history, so `--autogenerate` would produce an empty
> migration. To adopt Alembic on such a DB, baseline it first with
> `uv run alembic stamp head` after generating the init revision — or just drop and
> recreate the database and use Option B from the start.

## 5. Core API flows (examples)

Register a tenant + admin, then chat with streaming:

```bash
# Register
curl -X POST localhost:8000/api/v1/auth/register -H 'content-type: application/json' -d '{
  "tenant_name":"Acme","tenant_slug":"acme",
  "admin_email":"a@acme.test","admin_password":"password123"
}'

# Login
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"a@acme.test","password":"password123","tenant_slug":"acme"}' | jq -r .access_token)

# Create a knowledge base
curl -X POST localhost:8000/api/v1/knowledge-bases -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"name":"Docs","slug":"docs"}'

# Upload a document (kicks off async ingestion)
curl -X POST localhost:8000/api/v1/documents/upload -H "authorization: Bearer $TOKEN" \
  -F knowledge_base_id=<KB_ID> -F file=@policy.pdf

# Stream a grounded answer (Server-Sent Events)
curl -N -X POST localhost:8000/api/v1/chat/completions -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"message":"What is our refund policy?","use_rag":true,"stream":true}'
```

SSE events: `session` → `citations` → `token`* → (`tool_call`/`tool_result`)* → `done`.
WebSocket equivalent: `ws://localhost:8000/api/v1/chat/ws?token=<JWT>`.

## 6. Feature coverage map

| Spec area                                                                       | Where                                                                                    |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Multi-tenancy + isolation                                                       | `models/*` (`tenant_id`), `repositories/base.py`, Qdrant payload filter            |
| JWT + refresh rotation + RBAC                                                   | `core/security.py`, `services/auth_service.py`, `core/rbac.py`, `api/deps.py`    |
| Chat sessions (rename/archive/pin/search/categories/metadata)                   | `api/v1/chat.py`, `models/chat.py`                                                   |
| Messages (stream/regenerate/edit/retry/reactions/citations/metadata)            | `services/chat_service.py`, `api/v1/chat.py`                                         |
| Conversation memory (short/long/session/user/tenant + summaries)                | `services/memory_service.py`, `models/chat.py`                                       |
| Document ingestion (PDF/DOCX/TXT/CSV/XLSX/HTML/MD/JSON/XML/EML)                 | `rag/extractors.py`                                                                    |
| Pipeline (upload→validate→scan→extract→clean→chunk→embed→index→version) | `services/ingestion_service.py`                                                        |
| Chunking (fixed/recursive/semantic/parent-child/hierarchical/adaptive)          | `rag/chunking.py`                                                                      |
| Embeddings (OpenAI/Google/BGE/E5/Instructor/custom)                             | `rag/embeddings.py`                                                                    |
| Vector DB (collections/metadata/filtering/hybrid/keyword/rerank/dedup)          | `rag/vectorstore.py`, `rag/reranker.py`                                              |
| Retrieval pipeline + citations                                                  | `rag/retrieval.py`, `services/chat_service.py`                                       |
| Enterprise search (semantic/hybrid/metadata/document/chat/global)               | `services/search_service.py`, `api/v1/search.py`                                     |
| Tool calling (CRM/ERP/HR/Medical/custom, function calling)                      | `models/tool.py`, `services/tool_service.py`, `api/v1/tools.py`                    |
| Security (CSRF*/rate limit/injection/poisoning/leakage/encryption/audit)        | `security/guards.py`, `api/middleware.py`, `core/security.py`, `models/audit.py` |
| Observability (logs/tracing/metrics/token/cost/latency)                         | `core/logging.py`, `main.py` (`/metrics`), `services/analytics_service.py`       |
| Analytics + feedback loop + review queue + retraining                           | `api/v1/analytics.py`, `api/v1/feedback.py`, `workers/tasks.py`                    |
| Deployment (Docker/Compose/K8s/CI/HPA)                                          | `Dockerfile`, `docker-compose.yml`, `deploy/k8s`, `.github/workflows`            |

\* CSRF: the API is token-based (Bearer/`X-API-Key`), so it is not cookie-CSRF
susceptible; enable cookie auth + CSRF tokens only if you add a cookie session.

## 7. Implementation roadmap

1. **Foundations** ✅ — config, DB, auth, RBAC, tenancy, migrations.
2. **RAG core** ✅ — ingestion pipeline, chunking, embeddings, Qdrant, retrieval, citations.
3. **Chat** ✅ — streaming (SSE/WS), memory, tool-calling loop, persistence.
4. **Search & analytics** ✅ — hybrid/global search, dashboards, cost ledger.
5. **Feedback loop** ✅ — thumbs/corrections, review queue, retraining hook.
6. **Hardening** — wire real virus scanning (ClamAV), per-tenant rate tiers,
   secrets manager, Alembic autogenerate migration, ≥90% coverage with a
   Postgres-backed integration suite.
7. **Scale** — read replicas, Qdrant sharding, autoscaling workers, blue/green deploys.

## 8. Enterprise best practices applied

- **Strict tenant isolation** at the repository + vector-store layer.
- **Refresh-token rotation with reuse detection** (breach → revoke chain).
- **Field-level encryption** for tenant provider keys (Fernet).
- **Defence-in-depth LLM safety**: input validation, prompt-injection &
  RAG-poisoning detection, output secret-redaction.
- **Provider-agnostic LLM layer** — default `claude-opus-4-8`, adaptive thinking,
  streaming, with a clean tool-calling loop and cost tracking.
- **Async everywhere** (FastAPI + SQLAlchemy async), background ingestion via Celery.
- **Observability-first**: structured JSON logs, Prometheus metrics, OTEL traces,
  per-message token/cost/latency ledger.
- **12-factor config**, non-root containers, health/readiness probes, HPA.

## 9. Testing

```bash
uv run pytest --cov=app    # unit, security-isolation, RAG-eval, hallucination, citation
uv run locust -f tests/locustfile.py --host http://localhost:8000   # load test
# (with an activated venv, drop the `uv run` prefix)
```

Unit tests run with **no external services**. Integration tests that exercise the
DB require Postgres (the models use Postgres-native types: `UUID`, `JSONB`, `ARRAY`).

## 10. Configuration

All settings come from environment / `.env` (see `.env.example`). Per-tenant
overrides (provider, model, keys, chunking, reranking, system prompt) live in
`tenant_settings` and are editable via `PATCH /api/v1/tenant/settings`.

## 11. Troubleshooting

**`Failed building wheel for tokenizers` / `pyo3 ... newer than maximum supported version (3.12)`**
Your interpreter is Python 3.13 (or newer). The pinned `tokenizers` has no 3.13
wheel and falls back to a Rust source build that requires `pyo3 ≤ 3.12`.
Use Python **3.11 or 3.12**. Easiest fix — let uv handle the Python version:

```powershell
Remove-Item -Recurse -Force venv, .venv -ErrorAction SilentlyContinue
uv venv --python 3.12            # auto-downloads CPython 3.12
uv pip install -r requirements.txt
```

Or with plain pip:

```powershell
deactivate                       # if a 3.13 venv is active
Remove-Item -Recurse -Force venv # delete the 3.13 venv
py -3.12 -m venv venv            # recreate with 3.12
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Rust is **not** required once you're on 3.12 — the installer pulls a prebuilt wheel.
(Last-resort escape hatch on 3.13: `setx PYO3_USE_ABI3_FORWARD_COMPATIBILITY 1`,
reopen the shell, reinstall — slower, builds from source, and not recommended.)

**`The token '&&' is not a valid statement separator in this version.`**
Windows PowerShell 5.1 has no `&&`. Chain with `;` (or run the commands on
separate lines):

```powershell
python scripts/init_db.py ; python scripts/seed.py
```

**`uvicorn` / `celery` : The term ... is not recognized`** The venv isn't activated (its `Scripts\` dir isn't on `PATH`), or the install
above failed so the packages were never installed. Activate first, or invoke via
the venv's Python:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
python -m celery -A app.workers.celery_app.celery_app worker -Q ingestion,default --loglevel=info
```

**`Activate.ps1 cannot be loaded because running scripts is disabled`**
Allow signed local scripts for your user (one time):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**`A virtual environment already exists at '.venv'. Do you want to replace it?`**
`uv venv` won't overwrite an existing env unless you confirm — and the prompt
defaults to **no**. Pass `--clear` to replace it non-interactively:

```powershell
uv venv --python 3.12 --clear
```

Also check the env's version — `uv venv` reuses the last Python it resolved, so a
`.venv` can silently be 3.13/3.14. Verify with `.\.venv\Scripts\python.exe --version`
and recreate with `--clear` if it isn't 3.12.

**`ModuleNotFoundError: No module named 'app'`** (running `scripts/init_db.py` etc.)
Running a script by path puts only `scripts/` on `sys.path`, not the backend root,
so `import app...` fails. `scripts/init_db.py` and `scripts/seed.py` now add the
backend root to `sys.path` themselves, so just run them from the `backend/`
directory:

```powershell
uv run python scripts/init_db.py
uv run python scripts/seed.py
```

If you write a new script under `scripts/` that imports `app`, either copy that
`sys.path` bootstrap, run it as a module (`uv run python -m scripts.yourscript`),
or set `$env:PYTHONPATH = "."` (bash/zsh: `export PYTHONPATH=.`) first.
(`uvicorn app.main:app` never needs this — uvicorn adds the cwd itself.)

**`asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "..."`**
(or the same from `psql`). The Postgres role/password in your `.env` doesn't match
the server. Postgres reports this even when the **role simply doesn't exist**, and
it folds unquoted identifiers to lowercase — so `CREATE ROLE ChatBot` becomes
`chatbot`, which won't match the mixed-case name the app connects as. Create the
role and database with quoted identifiers (see **§4 → Database setup &
migrations**), or fix an existing role's password:

```sql
ALTER ROLE "ChatBot" WITH PASSWORD 'IrfaN@7368';
```

Verify the connection before retrying the app:

```powershell
$env:PGPASSWORD = "IrfaN@7368"; psql -h localhost -U ChatBot -d postgresql -c "select 1"
```
