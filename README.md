# Prompts Volume

AI-powered prompts management service
---

## 1. Service Purpose

**What it does:**

Prompts suggesting:
- Provides conversational search prompts for AI assistants
- Helps businesses understand customer search intent
- Supports multilingual prompts (Ukrainian, Russian, English)

Answers mngmt:
- Provides prompts from db for automation bots to evaluate and get answer with citations
- Receives/stores results from ai-assistants bots
- Serves latest answers for requested prompts

**Two sources of prompts for suggestion**

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

**2. Service Layer** (Domain-Driven Organization)
- **businessdomain/services/** - Business domain classification
  - `BusinessDomainService`: DB operations for business domains
  - `BusinessDomainDetectionService`: LLM-based domain classification
  - `CompanyMetaInfoService`: Orchestrates company metadata retrieval
- **geography/services/** - Location & language data
  - `CountryService`: Country DB operations
  - `LanguageService`: Language DB operations
- **topics/services/** - Topic matching & generation
  - `TopicService`: Topic DB operations and matching
  - `TopicsProvider`: LLM-based topic generation with DB matching
  - `TopicRelevanceFilterService`: Cluster filtering by topic relevance
- **prompts/services/** - Prompts generation & retrieval
  - `PromptService`: Prompt DB operations
  - `DataForSEOService`: Keyword fetching from search engines (external API)
  - `PromptsGeneratorService`: LLM-based prompt generation (external API)
- **embeddings/** - ML pipeline (local models)
  - `EmbeddingsService`: Local multilingual text embeddings (HuggingFace model, no API calls)
  - `ClusteringService`: HDBSCAN semantic clustering

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
https://github.com/user-attachments/assets/ec8f09f0-8982-41e2-bbb5-68ae8bb4997b

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
https://github.com/user-attachments/assets/3018bcec-bc0e-40ad-a577-4dfbbb5e1758

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

### 3.5 Evaluation Endpoints

**Purpose**: Track AI assistant responses to prompts for quality evaluation and analytics

The evaluation system provides atomic polling and submission APIs to:
- Distribute prompts across AI assistants (ChatGPT, Claude, Perplexity, etc.)
- Prevent duplicate evaluation work with database locking
- Handle bot crashes with automatic timeout and retry
- Preserve evaluation history for analytics

**Configuration**:
- `EVALUATION_TIMEOUT_HOURS=2` - Stale evaluations become available for retry after 2 hours
- `MIN_DAYS_SINCE_LAST_EVALUATION=1` - Completed prompts unavailable for 1 day per assistant+plan

---

#### 3.5.1 Poll for Evaluation

```http
POST /evaluations/api/v1/poll
```

**Purpose**: Atomically claim a prompt for evaluation by an AI assistant

**Request**:
```json
{
  "assistant_name": "ChatGPT",
  "plan_name": "Plus"
}
```

**Parameters**:
- `assistant_name` (required): AI assistant name (e.g., "ChatGPT", "Claude", "Perplexity")
- `plan_name` (required): Assistant plan/tier (e.g., "Free", "Plus", "Pro")

**Response** (prompt available):
```json
{
  "evaluation_id": 123,
  "prompt_id": 456,
  "prompt_text": "Найкращий смартфон до 15 000 грн?",
  "topic_id": 1,
  "claimed_at": "2025-12-09T10:30:00Z"
}
```

**Response** (no prompts available):
```json
{
  "evaluation_id": null,
  "prompt_id": null,
  "prompt_text": null,
  "topic_id": null,
  "claimed_at": null
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/evaluations/api/v1/poll" \
  -H "Content-Type: application/json" \
  -d '{"assistant_name": "ChatGPT", "plan_name": "Plus"}'
```

**Key Features**:
- **Atomic claiming**: PostgreSQL locking (SELECT FOR UPDATE SKIP LOCKED) prevents duplicate work
- **Concurrent-safe**: Multiple bots can poll simultaneously without conflicts
- **Timeout protection**: Stale evaluations (>2 hours) automatically become available for retry
- **Cooldown period**: Completed evaluations locked for 1 day per assistant+plan combination

**Use Case**: Bot polls for a prompt, evaluates it with the AI assistant, then submits or releases

---

#### 3.5.2 Submit Answer

```http
POST /evaluations/api/v1/submit
```

**Purpose**: Submit evaluation answer and mark as completed

**Request**:
```json
{
  "evaluation_id": 123,
  "answer": {
    "response": "Перш ніж купувати смартфон до 15 000 грн, важливо...",
    "citations": [
      {
        "url": "https://example.com/phones-guide",
        "text": "Best Phones Under 15000"
      }
    ],
    "timestamp": "2025-12-09T10:35:00Z"
  }
}
```

**Parameters**:
- `evaluation_id` (required): Evaluation ID from poll response
- `answer.response` (required): The AI assistant's response text
- `answer.citations` (required): List of citation objects with URL and text
- `answer.timestamp` (required): ISO timestamp when answer was generated

**Response**:
```json
{
  "evaluation_id": 123,
  "prompt_id": 456,
  "status": "completed",
  "completed_at": "2025-12-09T10:35:00Z"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/evaluations/api/v1/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "evaluation_id": 123,
    "answer": {
      "response": "Your AI assistant response here...",
      "citations": [
        {"url": "https://example.com", "text": "Source 1"}
      ],
      "timestamp": "2025-12-09T10:35:00Z"
    }
  }'
```

**Use Case**: After successfully getting answer from AI assistant, submit it to complete evaluation

---

#### 3.5.3 Release Evaluation

```http
POST /evaluations/api/v1/release
```

**Purpose**: Release evaluation on failure (delete or mark as failed)

**Request** (mark as failed - preserves for analytics):
```json
{
  "evaluation_id": 123,
  "mark_as_failed": true,
  "failure_reason": "API timeout after 60 seconds"
}
```

**Request** (delete - makes available immediately):
```json
{
  "evaluation_id": 123,
  "mark_as_failed": false
}
```

**Parameters**:
- `evaluation_id` (required): Evaluation ID from poll response
- `mark_as_failed` (optional, default: false): If true, mark as FAILED; if false, delete record
- `failure_reason` (required if mark_as_failed=true): Reason for failure

**Response**:
```json
{
  "evaluation_id": 123,
  "action": "marked_failed"
}
```
(action can be "marked_failed" or "deleted")

**Examples**:
```bash
# Mark as failed (preserves record for analytics)
curl -X POST "http://localhost:8000/evaluations/api/v1/release" \
  -H "Content-Type: application/json" \
  -d '{
    "evaluation_id": 123,
    "mark_as_failed": true,
    "failure_reason": "ChatGPT API timeout"
  }'

# Delete (makes prompt immediately available)
curl -X POST "http://localhost:8000/evaluations/api/v1/release" \
  -H "Content-Type: application/json" \
  -d '{"evaluation_id": 123, "mark_as_failed": false}'
```

**Use Case**: When bot encounters error (API timeout, rate limit, etc.), release the evaluation

---

#### 3.5.4 Get Evaluation Results

```http
POST /evaluations/api/v1/results
```

**Purpose**: Retrieve the latest completed evaluation results for a list of prompts

**Request**:
```json
{
  "assistant_name": "ChatGPT",
  "plan_name": "Plus",
  "prompt_ids": [1, 2, 3]
}
```

**Parameters**:
- `assistant_name` (required): AI assistant name (e.g., "ChatGPT", "Claude", "Perplexity")
- `plan_name` (required): Assistant plan/tier (e.g., "Free", "Plus", "Pro")
- `prompt_ids` (required): List of prompt IDs to get results for

**Response**:
```json
{
  "results": [
    {
      "prompt_id": 1,
      "evaluation_id": 123,
      "status": "completed",
      "answer": {
        "response": "The best smartphone under 15,000 UAH...",
        "citations": [
          {"url": "https://example.com/guide", "text": "Smartphone Guide"}
        ],
        "timestamp": "2025-12-09T10:35:00Z"
      },
      "completed_at": "2025-12-09T10:35:00Z"
    }
  ]
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/evaluations/api/v1/results" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_name": "ChatGPT",
    "plan_name": "Plus",
    "prompt_ids": [1, 2, 3]
  }'
```

**Key Features**:
- Returns only COMPLETED evaluations (not IN_PROGRESS or FAILED)
- Returns the latest evaluation per prompt when multiple exist
- Uses PostgreSQL DISTINCT ON for efficient retrieval
- Case-insensitive assistant/plan lookup

**Use Case**: After evaluating prompts, retrieve the stored results for analysis, display, or comparison across different AI assistants

---

#### 3.5.5 Complete Evaluation Workflow

**Example: Bot evaluating prompts**

```bash
# Step 1: Poll for a prompt
RESPONSE=$(curl -X POST "http://localhost:8000/evaluations/api/v1/poll" \
  -H "Content-Type: application/json" \
  -d '{"assistant_name": "ChatGPT", "plan_name": "Plus"}')

# Parse response (example uses jq)
EVAL_ID=$(echo $RESPONSE | jq -r '.evaluation_id')
PROMPT_TEXT=$(echo $RESPONSE | jq -r '.prompt_text')

if [ "$EVAL_ID" = "null" ]; then
  echo "No prompts available"
  exit 0
fi

echo "Evaluating prompt: $PROMPT_TEXT"

# Step 2: Get answer from AI assistant (external)
# ... bot queries ChatGPT API with the prompt ...
# ANSWER_TEXT="..."
# CITATIONS=[...]

# Step 3a: Submit successful answer
curl -X POST "http://localhost:8000/evaluations/api/v1/submit" \
  -H "Content-Type: application/json" \
  -d "{
    \"evaluation_id\": $EVAL_ID,
    \"answer\": {
      \"response\": \"$ANSWER_TEXT\",
      \"citations\": $CITATIONS,
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }
  }"

# OR Step 3b: Release on failure
# curl -X POST "http://localhost:8000/evaluations/api/v1/release" \
#   -H "Content-Type: application/json" \
#   -d "{\"evaluation_id\": $EVAL_ID, \"mark_as_failed\": true, \"failure_reason\": \"API timeout\"}"
```

**Timeout & Retry Behavior**:
- **Bot crash scenario**: If bot crashes without submitting/releasing, evaluation times out after 2 hours
- **Automatic retry**: Timed-out prompts become available for any bot to claim
- **Multiple attempts**: Multiple evaluation records tracked for same prompt+assistant+plan (for analytics)
- **Failed prompts**: Status=FAILED evaluations immediately available for retry
- **Completed prompts**: Status=COMPLETED evaluations locked for 1 day per assistant+plan

**Configuration**:
Set in `.env`:
```bash
EVALUATION_TIMEOUT_HOURS=2           # Timeout for stale IN_PROGRESS evaluations
MIN_DAYS_SINCE_LAST_EVALUATION=1     # Cooldown for completed evaluations
```

---

### 3.6 Complete Client Flow for topics/prompts suggesting

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
│   ├── main.py                          # FastAPI app + lifespan (DB init)
│   │
│   ├── businessdomain/                  # Business domain classification
│   │   ├── models/
│   │   │   ├── company_meta_info.py     # CompanyMetaInfo dataclass
│   │   │   └── api_models.py            # API responses (CompanyMetaInfoResponse, etc.)
│   │   └── services/
│   │       ├── business_domain_service.py           # DB operations
│   │       ├── business_domain_detection_service.py # LLM classification
│   │       └── company_meta_info_service.py         # Orchestrator
│   │
│   ├── geography/                       # Location & language data
│   │   └── services/
│   │       ├── country_service.py       # Country DB operations
│   │       └── language_service.py      # Language DB operations
│   │
│   ├── topics/                          # Topic matching & generation
│   │   ├── models/
│   │   │   ├── generated_topic.py       # GeneratedTopic dataclass
│   │   │   └── topic_match_result.py    # TopicMatchResult dataclass
│   │   └── services/
│   │       ├── topic_service.py                    # DB operations
│   │       ├── topics_provider.py                  # LLM generation + matching
│   │       └── topic_relevance_filter_service.py   # Cluster filtering
│   │
│   ├── prompts/                         # Prompts generation & retrieval
│   │   ├── router.py                    # API endpoints
│   │   ├── models/
│   │   │   ├── cluster_prompts.py       # Cluster-based models
│   │   │   ├── prompt_responses.py      # DB retrieval responses
│   │   │   └── generate_request.py      # Request models
│   │   └── services/
│   │       ├── prompt_service.py                # DB operations
│   │       ├── data_for_seo_service.py          # External API (keywords)
│   │       └── prompts_generator_service.py     # LLM generation
│   │
│   ├── evaluations/                     # Prompt evaluation tracking
│   │   ├── router.py                    # API endpoints (poll, submit, release)
│   │   ├── models/
│   │   │   └── api_models.py            # Request/response models
│   │   └── services/
│   │       └── evaluation_service.py    # Atomic polling, timeout logic
│   │
│   ├── embeddings/                      # ML pipeline (local models)
│   │   ├── embeddings_service.py        # sentence-transformers
│   │   └── clustering_service.py        # HDBSCAN
│   │
│   ├── database/                        # Data persistence layer
│   │   ├── models.py                    # SQLAlchemy ORM (Topic, Prompt, Country, etc.)
│   │   ├── init.py                      # Database seeding logic
│   │   └── session.py                   # DB connection, vector index
│   │
│   ├── config/                          # Configuration
│   │   └── settings.py                  # Environment-based settings
│   │
│   ├── utils/                           # Shared utilities
│   │   ├── keyword_filters.py           # Keyword filtering logic
│   │   └── url_validator.py            # URL validation
│   │
│   └── data/                            # Static data files
│       ├── prompts_phones.csv           # 50 phone prompts
│       └── prompts_laptops.csv          # 59 laptop prompts
│
├── tests/                               # Integration tests
├── docker-compose.yml                   # Multi-container setup
├── Dockerfile                           # App container
├── README.md                            # This file
└── CLAUDE.md                            # AI assistant guidance
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
