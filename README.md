# Prompts Volume

AI-powered prompts suggestion service for e-commerce businesses.

---

## 1. Service Purpose

**What it does:**
- Provides conversational search prompts for AI assistants
- Helps businesses understand customer search intent
- Supports multilingual prompts (Ukrainian, Russian, English)

**Two sources of prompts:**

1. **DB-first (fast, ~50ms)**: Retrieve pre-seeded, topic-specific prompts from PostgreSQL
2. **Generation (on-demand, ~30-60s)**: Create custom prompts from search engine ranking data when DB has no data for needed topics

**Key Features:**
- Pre-seeded prompts for common e-commerce topics (phones, laptops, etc.)
- Custom prompt generation based on real search engine data
- Semantic clustering and topic matching with ML
- Vector similarity search with pgvector (384-dimensional embeddings)

---

## 2. Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────┐
│              FastAPI App                          │ ← REST API layer
└────────┬─────────────────────────┬────────────────┘
         │                         │
    ┌────▼────┐              ┌─────▼─────────┐
    │   DB    │              │  External     │
    │  Layer  │              │    APIs       │
    └────┬────┘              └─────┬─────────┘
         │                         │
         │                         ├─ DataForSEO (keywords)
         │                         └─ OpenAI (prompt generation)
         │
         │                   ┌─────────────────────┐
         │                   │  Local ML Models    │
         │                   │  (in-process)       │
         │                   └─────┬───────────────┘
         │                         │
         │                         └─ sentence-transformers
         │                            (embeddings, 384-dim)
         │                            HuggingFace model
         │                            ~450MB cached locally
         │
┌────────▼───────────────────┐
│  PostgreSQL + pgvector     │
│  - Topics                  │
│  - Prompts + embeddings    │
│  - Countries/domains       │
└────────────────────────────┘
```

### Core Components

**1. Database Layer** (PostgreSQL + pgvector)
- Stores pre-seeded prompts with 384-dim embeddings
- Topics organized by country and business domain
- Vector similarity search support (HNSW index)

**2. Service Layer**
- `PromptService`: DB CRUD operations for prompts
- `TopicService`: Topic management and matching
- `DataForSEOService`: Keyword fetching from search engines (external API)
- `PromptsGeneratorService`: OpenAI-based prompt generation (external API)
- `EmbeddingsService`: Local multilingual text embeddings (HuggingFace model, no API calls)

**3. ML Pipeline** (when generating)
- **Embeddings**: sentence-transformers (local model, multilingual, 384-dim, runs in-process)
- **Clustering**: HDBSCAN (local algorithm, semantic grouping with noise handling)
- **Topic Matching**: Cosine similarity filtering (local computation, 0.7 threshold)
- **Generation**: GPT-4o-mini (external API, conversational prompts in detected language)

### Data Flow

**Path 1 - DB Retrieval** (fast, ~50ms):
```
Request → Topic IDs → DB lookup → Return prompts
```

**Path 2 - Generation** (slow, ~30-60s):
```
URL → Keywords (DataForSEO API call)
    → Filter (local: word count, brand exclusion, dedupe)
    → Embeddings (local: sentence-transformers model)
    → Clustering (local: HDBSCAN algorithm)
    → Topic filtering (local: cosine similarity)
    → Prompt generation (OpenAI API call)
    → Response
```

---

## 3. API Endpoints

**Base URL**: `http://localhost:8000`

### 3.1 Health Check

```http
GET /health
```

**Purpose**: Service health status

**Response**:
```json
{"status": "UP"}
```

---

### 3.2 Get Company Meta-Info

```http
GET /prompts/api/v1/meta-info
```

**Purpose**: Retrieve business domain and suggested topics for a company

**Parameters**:
- `company_url` (required): Company website URL (e.g., `moyo.ua`)
- `iso_country_code` (required): ISO 3166-1 alpha-2 country code (e.g., `UA`)

**Example**:
```bash
curl "http://localhost:8000/prompts/api/v1/meta-info?company_url=moyo.ua&iso_country_code=UA"
```

**Response**:
```json
{
  "business_domain": "e-comm",
  "topics": {
    "matched_topics": [
      {"id": 1, "title": "Смартфони і телефони", "description": "..."},
      {"id": 2, "title": "Ноутбуки та персональні комп'ютери", "description": "..."}
    ],
    "unmatched_topics": []
  },
  "brand_variations": ["moyo", "мойо"]
}
```

**Use Case**: First step in client flow - discover available topics for the business

---

### 3.3 Get Prompts from Database

```http
GET /prompts/api/v1/prompts
```

**Purpose**: Retrieve pre-seeded prompts for specified topics (fast, DB-first approach)

**Parameters**:
- `topic_ids` (required, multi): List of topic IDs to retrieve prompts for

**Example**:
```bash
curl "http://localhost:8000/prompts/api/v1/prompts?topic_ids=1&topic_ids=2"
```

**Response**:
```json
{
  "topics": [
    {
      "topic_id": 1,
      "prompts": [
        {"id": 1, "prompt_text": "Купити смартфон в Україні з швидкою доставкою"},
        {"id": 2, "prompt_text": "Найкращий смартфон до 15 000 грн"}
      ]
    },
    {
      "topic_id": 2,
      "prompts": [
        {"id": 51, "prompt_text": "Де купити ноутбук"},
        {"id": 52, "prompt_text": "Кращі ноутбуки з екраном 15-16 дюймів"}
      ]
    }
  ]
}
```

**Use Case**: Retrieve prompts from DB for known topics

---

### 3.4 Generate Prompts

```http
GET /prompts/api/v1/generate
```

**Purpose**: Generate custom prompts based on search engine data (fallback when DB has no data)

**Parameters**:
- `company_url` (required): Company website URL
- `iso_country_code` (required): ISO 3166-1 alpha-2 country code
- `topics` (required, multi): List of topic names from meta-info
- `brand_variations` (required, multi): List of brand variations from meta-info

**Example**:
```bash
curl "http://localhost:8000/prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA&topics=Смартфони+і+телефони&topics=Ноутбуки&brand_variations=moyo&brand_variations=мойо"
```

**Response**:
```json
{
  "topics": [
    {
      "topic": "Смартфони і телефони",
      "clusters": [
        {
          "cluster_id": 42,
          "keywords": ["смартфон samsung", "телефон galaxy", "phone iphone"],
          "prompts": [
            "Найкращий смартфон до 15 000 грн?",
            "Samsung Galaxy чи iPhone – що вибрати?"
          ]
        }
      ]
    }
  ]
}
```
**Use Case**: if DB has no similar topic - we try to generate prompts using search engines data from dataforseo

**Performance**: ~30-60 seconds (full ML pipeline + OpenAI)

**Pipeline Steps**:
1. Fetch keywords from DataForSEO (up to 10k)
2. Filter keywords (word count ≥3, direct brand name exclusion, dedupe)
3. Generate embeddings (sentence-transformers, 384-dim)
4. Cluster keywords (HDBSCAN, min_cluster_size=5)
5. Filter by topic relevance (cosine similarity ≥0.7)
6. Generate prompts (OpenAI GPT-4o-mini, ~5 keywords per prompt)

---

### 3.5 Complete Client Flow

**Recommended Integration Pattern (Hybrid Approach):**

The client flow uses a **parallel hybrid approach** to provide complete coverage:
- **Matched topics** → Fast DB retrieval via `/prompts` (~50ms)
- **Unmatched topics** → AI generation via `/generate` (~30-60s)

This gives clients the complete picture: known data (DB) + intelligent guesses (AI generation).

```
┌────────────────────────────────────────────────────────────┐
│ Step 1: Get Meta-Info                                      │
│ GET /meta-info?company_url=X&iso_country_code=Y           │
│ → Returns: matched_topics, unmatched_topics, brands       │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
            ┌───────────┴────────────┐
            │   Split by Match       │
            │   Status               │
            └───────┬───────┬────────┘
                    │       │
        ┌───────────┘       └───────────┐
        │                                │
        ▼                                ▼
┌────────────────────┐          ┌────────────────────┐
│ Step 2a: DB        │          │ Step 2b: Generate  │
│ Retrieval (Fast)   │          │ (Slow)             │
│                    │          │                    │
│ GET /prompts       │          │ GET /generate      │
│ ?topic_ids=1,2     │          │ ?topics=X,Y&...    │
│                    │          │                    │
│ • Matched topics   │          │ • Unmatched topics │
│ • ~50ms response   │          │ • ~30-60s ML       │
│ • Pre-seeded       │          │ • Search data      │
└─────────┬──────────┘          └──────────┬─────────┘
          │                                │
          │    Can run in parallel        │
          │                                │
          └──────────┬─────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Combine Results │
            │ • DB prompts    │
            │ • Generated     │
            │   prompts       │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Select prompts  │
            │ for tracking    |
            | in AI assitants |
            │ responses       |
            └─────────────────┘
```
So, while client selects prompts that returned instantly from DB - service has a time to prepare for him more or less relevant prompts generated based on search engines keywords. 

**Example Client Code** (Python):

```python
import asyncio
import httpx

async def get_prompts_for_business(company_url: str, iso_country_code: str):
    """
    Complete hybrid client flow for getting prompts.

    Returns both DB prompts (matched topics) and generated prompts (unmatched topics)
    for complete coverage.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Get meta-info (discover matched and unmatched topics)
        meta_response = await client.get(
            "http://localhost:8000/prompts/api/v1/meta-info",
            params={"company_url": company_url, "iso_country_code": iso_country_code}
        )
        meta = meta_response.json()

        matched_topics = meta["topics"]["matched_topics"]
        unmatched_topics = meta["topics"]["unmatched_topics"]
        brand_variations = meta["brand_variations"]

        results = {
            "db_prompts": None,
            "generated_prompts": None
        }

        # Step 2a: Get DB prompts for matched topics (if any)
        if matched_topics:
            matched_ids = [t["id"] for t in matched_topics]
            db_response = await client.get(
                "http://localhost:8000/prompts/api/v1/prompts",
                params={"topic_ids": matched_ids}
            )
            results["db_prompts"] = db_response.json()

        # Step 2b: Generate prompts for unmatched topics (if any)
        if unmatched_topics:
            unmatched_names = [t["title"] for t in unmatched_topics]
            gen_response = await client.get(
                "http://localhost:8000/prompts/api/v1/generate",
                params={
                    "company_url": company_url,
                    "iso_country_code": iso_country_code,
                    "topics": unmatched_names,
                    "brand_variations": brand_variations
                },
                timeout=120.0  # Generation takes 30-60s
            )
            results["generated_prompts"] = gen_response.json()

        return results

# Usage
results = await get_prompts_for_business("moyo.ua", "UA")
# results["db_prompts"] → Fast pre-seeded prompts from DB (matched topics)
# results["generated_prompts"] → AI-generated prompts (unmatched topics)
```

**Performance Comparison:**

| Scenario | Endpoint | Topics | Response Time | Cost |
|----------|----------|--------|---------------|------|
| **Matched topics** | `/prompts` | IDs from meta-info | ~50ms | Free |
| **Unmatched topics** | `/generate` | Names from meta-info | ~30-60s | ~$1.01-1.05 (DataForSEO + OpenAI) |
| **Hybrid (both)** | Both endpoints | Split by match status | ~30-60s (parallel) | ~$1.01-1.05 |

**Key Benefits**:
- **Complete coverage**: Combines known data (DB) with intelligent guesses (AI)
- **Optimal performance**: Fast DB lookup for matched, generation only for unmatched
- **Parallel execution**: Both calls can run concurrently for faster total time
- **Cost-effective**: Only pay for generation when necessary

---

## 4. Technologies

### Stack Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.121+ | Async REST API with OpenAPI docs |
| **Database** | PostgreSQL 16 + pgvector | Vector storage & similarity search |
| **Language** | Python 3.12 | Modern async/await support |
| **Container** | Docker + docker-compose | Isolated deployment |
| **Dependencies** | uv | Fast Python package manager |

### ML & AI

| Component | Technology | Details |
|-----------|-----------|---------|
| **Text Embeddings** | sentence-transformers<br/>`paraphrase-multilingual-MiniLM-L12-v2` | 384-dim vectors<br/>50+ languages incl. Ukrainian |
| **Clustering** | HDBSCAN 0.8+ | Density-based semantic grouping<br/>Handles noise automatically |
| **Similarity** | scikit-learn<br/>cosine_similarity | Topic relevance scoring (0.7 threshold) |
| **LLM Generation** | OpenAI GPT family | Conversational prompt creation<br/>Language auto-detection |

### External APIs

- **DataForSEO API**: Keyword ranking data (paginated, up to 10k keywords, ~$1.00 per request)
- **OpenAI API**: Prompt generation (JSON mode, ~$0.01-0.05 per request)

**Total cost per generation request**: ~$1.01-1.05 (DataForSEO + OpenAI)

---

## 5. Quick Start with Docker Compose

### Prerequisites

- Docker & Docker Compose installed
- API credentials:
  - **DataForSEO**: https://app.dataforseo.com/
  - **OpenAI**: https://platform.openai.com/api-keys

### Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd prompts-volume

# 2. Configure environment
cp .env.example .env

# 3. Edit .env and add your API keys:
#    DATAFORSEO_USERNAME=your_username
#    DATAFORSEO_PASSWORD=your_password
#    OPENAI_API_KEY=sk-...

# 4. Build and start services
docker-compose up -d

# 5. Check health
curl http://localhost:8000/health
# {"status": "UP"}

# 6. View API documentation
open http://localhost:8000/docs
```

### Services

- **app**: FastAPI service (port 8000)
- **postgres**: PostgreSQL 16 + pgvector (port 5432)

### Database Auto-Initialization

On first startup, the service automatically:
- Creates all database tables (topics, prompts, countries, etc.)
- Enables pgvector extension
- Creates HNSW vector index for similarity search
- Seeds countries (Ukraine + others), business domains (e-comm)
- Seeds topics (2 topics: "Смартфони і телефони", "Ноутбуки та персональні комп'ютери")
- Loads sample prompts from CSV files (50 phone prompts + 59 laptop prompts)

**Ready for requests in ~5 seconds**

### Example API Calls

```bash
# Complete client flow

# 1. Get meta-info
curl "http://localhost:8000/prompts/api/v1/meta-info?company_url=moyo.ua&iso_country_code=UA"

# 2. Get prompts from DB (fast, ~50ms)
curl "http://localhost:8000/prompts/api/v1/prompts?topic_ids=1&topic_ids=2"

# 3. Generate prompts if needed (slow, ~30-60s, requires OpenAI API key)
curl "http://localhost:8000/prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA&topics=Смартфони+і+телефони&brand_variations=moyo"
```

### Stopping

```bash
docker-compose down          # Stop services
docker-compose down -v       # Stop + delete data volumes
```

---

## Project Structure

```
prompts-volume/
├── src/
│   ├── main.py                      # FastAPI app + lifespan (DB init)
│   ├── database/                    # SQLAlchemy models, init, seeding
│   │   ├── models.py                # Topic, Prompt, Country models
│   │   ├── init.py                  # Seeding logic
│   │   └── session.py               # DB connection, vector index
│   ├── prompts/
│   │   ├── router.py                # API endpoints
│   │   ├── models/                  # Request/response models
│   │   └── services/                # Business logic
│   ├── embeddings/                  # ML pipeline
│   │   ├── embeddings_service.py    # sentence-transformers
│   │   ├── clustering_service.py    # HDBSCAN
│   │   └── topic_relevance_filter_service.py
│   ├── data/                        # CSV files
│   │   ├── prompts_phones.csv       # 50 phone prompts
│   │   └── prompts_laptops.csv      # 59 laptop prompts
│   └── utils/                       # Helpers
├── tests/                           # Integration tests
├── docker-compose.yml               # Multi-container setup
├── Dockerfile                       # App container
└── README.md                        # This file
```

---

## Development

```bash
# Local development (without Docker)
cp .env.example .env
# Add DATABASE_URL to .env:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/prompts

# Run PostgreSQL manually
docker run -d -p 5432:5432 -e POSTGRES_DB=prompts -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16

# Start application
uv run uvicorn src.main:app --reload

# Run tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_prompts_endpoint.py -v
```
