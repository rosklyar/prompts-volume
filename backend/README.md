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

### Authentication Overview

Most endpoints require JWT authentication via `Authorization: Bearer {token}` header:

**Authenticated Endpoints**:
- All prompts endpoints: `/prompts/api/v1/*` (meta-info, prompts, generate, similar)
- Prompt groups endpoints: `/prompt-groups/api/v1/*` (all CRUD operations)
- Evaluation results: `/evaluations/api/v1/results`

**Public Endpoints** (no authentication required):
- Health check: `/health`
- Auth endpoints: `/api/v1/login/access-token`, `/api/v1/signup`
- Evaluation automation: `/evaluations/api/v1/poll`, `/submit`, `/release`, `/priority-prompts`

**How to authenticate**:
```bash
# 1. Login to get access token
curl -X POST "http://localhost:8000/api/v1/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"

# Response: {"access_token": "eyJhbGc...", "token_type": "bearer"}

# 2. Use token in subsequent requests
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompts/api/v1/meta-info?company_url=moyo.ua&iso_country_code=UA"
```

---

### 3.1 Health Check

```http
GET /health
```

**Purpose**: Service health status

**Authentication**: Not required

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

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Parameters**:
- `company_url` (required): Company website URL (e.g., `moyo.ua`)
- `iso_country_code` (required): ISO 3166-1 alpha-2 country code (e.g., `UA`)

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompts/api/v1/meta-info?company_url=moyo.ua&iso_country_code=UA"
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

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Parameters**:
- `topic_ids` (required, multi): List of topic IDs to retrieve prompts for

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompts/api/v1/prompts?topic_ids=1&topic_ids=2"
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

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Parameters**:
- `company_url` (required): Company website URL
- `iso_country_code` (required): ISO 3166-1 alpha-2 country code
- `topics` (required, multi): List of topic names from meta-info
- `brand_variations` (required, multi): List of brand variations from meta-info

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA&topics=Смартфони+і+телефони&topics=Ноутбуки&brand_variations=moyo&brand_variations=мойо"
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

### 3.5 Find Similar Prompts

```http
GET /prompts/api/v1/similar
```

**Purpose**: Find semantically similar prompts from the database using vector similarity search. Designed for autocomplete functionality - as user types, suggest relevant existing prompts.

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Parameters**:
- `text` (required): Input text to find similar prompts for (1-1000 characters)
- `k` (optional, default: 10): Maximum number of results to return (1-100)
- `min_similarity` (optional, default: 0.75): Minimum cosine similarity threshold (must be > 0.7, max 1.0)

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompts/api/v1/similar?text=купити%20смартфон&k=5&min_similarity=0.8"
```

**Response**:
```json
{
  "query_text": "купити смартфон",
  "prompts": [
    {
      "id": 1,
      "prompt_text": "Купити смартфон в Україні з швидкою доставкою",
      "similarity": 0.92
    },
    {
      "id": 3,
      "prompt_text": "Де купити смартфон Україна",
      "similarity": 0.87
    }
  ],
  "total_found": 2
}
```

**Key Features**:
- **pgvector HNSW index**: Fast approximate nearest neighbor search
- **Cosine similarity**: Results sorted by semantic similarity (highest first)
- **Server-side caps**: `k` max 100, `min_similarity` must be > 0.7 (configurable in settings)
- **Empty results = 200 OK**: Returns empty list if no matches found

**Use Case**: Real-time autocomplete as user types a prompt - suggest relevant existing prompts from the database

**Performance**: ~50-100ms (embedding generation + vector search)

**Configuration** (in `.env` or settings):
```bash
SIMILAR_PROMPTS_MAX_K=100                      # Maximum allowed k parameter
SIMILAR_PROMPTS_MIN_SIMILARITY_THRESHOLD=0.7  # Minimum allowed similarity threshold
```

---

### 3.6 Evaluation Endpoints

**Purpose**: Track AI assistant responses to prompts for quality evaluation and analytics

The evaluation system provides atomic polling and submission APIs to:
- Distribute prompts across AI assistants (ChatGPT, Claude, Perplexity, etc.)
- Prevent duplicate evaluation work with database locking
- Handle bot crashes with automatic timeout and retry
- Preserve evaluation history for analytics

**Authentication**:
- **Public endpoints** (for automation bots): `/poll`, `/submit`, `/release`, `/priority-prompts`
- **Authenticated endpoints** (JWT required): `/results`, `/results/enriched`

**Configuration**:
- `EVALUATION_TIMEOUT_HOURS=2` - Stale evaluations become available for retry after 2 hours
- `MIN_DAYS_SINCE_LAST_EVALUATION=1` - Completed prompts unavailable for 1 day per assistant+plan

---

#### 3.6.1 Poll for Evaluation

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

#### 3.6.2 Submit Answer

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

#### 3.6.3 Release Evaluation

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

#### 3.6.4 Get Evaluation Results

```http
GET /evaluations/api/v1/results
```

**Purpose**: Retrieve the latest completed evaluation results for a list of prompts

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Parameters**:
- `assistant_name` (required): AI assistant name (e.g., "ChatGPT", "Claude", "Perplexity")
- `plan_name` (required): Assistant plan/tier (e.g., "Free", "Plus", "Pro")
- `prompt_ids` (required, multi): List of prompt IDs to get results for

**Response**:
```json
{
  "results": [
    {
      "prompt_id": 1,
      "prompt_text": "Найкращий смартфон до 15 000 грн?",
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
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/evaluations/api/v1/results?assistant_name=ChatGPT&plan_name=Plus&prompt_ids=1&prompt_ids=2&prompt_ids=3"
```

**Key Features**:
- Returns only COMPLETED evaluations (not IN_PROGRESS or FAILED)
- Returns the latest evaluation per prompt when multiple exist
- Uses PostgreSQL DISTINCT ON for efficient retrieval
- Case-insensitive assistant/plan lookup

**Use Case**: After evaluating prompts, retrieve the stored results for analysis, display, or comparison across different AI assistants

---

#### 3.6.5 Get Enriched Results

```http
POST /evaluations/api/v1/results/enriched
```

**Purpose**: Retrieve evaluation results enriched with brand mention positions and citation domain leaderboard

**Authentication**: Required (JWT Bearer token)

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Query Parameters**:
- `assistant_name` (required): AI assistant name (e.g., "ChatGPT", "Claude", "Perplexity")
- `plan_name` (required): Assistant plan/tier (e.g., "Free", "Plus", "Pro")
- `prompt_ids` (required, multi): List of prompt IDs to get results for

**Request Body**:
```json
{
  "brands": [
    {"name": "Moyo", "variations": ["Moyo", "Мойо", "moyo.ua"]},
    {"name": "Rozetka", "variations": ["Rozetka", "Розетка", "rozetka.com.ua"]}
  ]
}
```

Or use brands from a prompt group:
```json
{
  "group_id": 2
}
```

**Parameters**:
- `brands` (optional): List of brands to detect in responses (takes priority over group_id)
  - `name`: Brand display name
  - `variations`: List of text variations to search for (case-insensitive, supports Cyrillic)
- `group_id` (optional): Prompt group ID to fetch brands from
  - Used only if `brands` is not provided
  - Group must belong to the authenticated user

**Response**:
```json
{
  "results": [
    {
      "prompt_id": 1,
      "prompt_text": "Де купити смартфон?",
      "evaluation_id": 123,
      "status": "completed",
      "answer": {
        "response": "Магазин Moyo пропонує найкращі ціни...",
        "citations": [
          {"url": "https://moyo.ua/phones/123", "text": "Moyo Phones"}
        ],
        "timestamp": "2025-12-09T10:35:00Z"
      },
      "completed_at": "2025-12-09T10:35:00Z",
      "brand_mentions": [
        {
          "brand_name": "Moyo",
          "mentions": [
            {
              "start": 8,
              "end": 12,
              "matched_text": "Moyo",
              "variation": "Moyo"
            }
          ]
        }
      ]
    }
  ],
  "citation_leaderboard": {
    "items": [
      {"path": "rozetka.com.ua", "count": 5, "is_domain": true},
      {"path": "rozetka.com.ua/ua/mobile-phones", "count": 3, "is_domain": false},
      {"path": "moyo.ua", "count": 2, "is_domain": true}
    ],
    "total_citations": 7
  }
}
```

**Examples**:
```bash
# With explicit brands
curl -X POST "http://localhost:8000/evaluations/api/v1/results/enriched?assistant_name=ChatGPT&plan_name=Plus&prompt_ids=1&prompt_ids=2" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "brands": [
      {"name": "Moyo", "variations": ["Moyo", "Мойо", "moyo.ua"]},
      {"name": "Rozetka", "variations": ["Rozetka", "Розетка"]}
    ]
  }'

# With brands from a prompt group
curl -X POST "http://localhost:8000/evaluations/api/v1/results/enriched?assistant_name=ChatGPT&plan_name=Plus&prompt_ids=1&prompt_ids=2" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"group_id": 2}'
```

**Key Features**:
- **Brand mention detection**: Returns character positions (`start`, `end`) for each brand mention in response text
- **Case-insensitive matching**: Works with both Latin and Cyrillic text
- **Group-based brands**: Use `group_id` to automatically apply brands configured on a prompt group
- **Citation leaderboard**: Aggregates citations by domain and sub-paths with frequency counts
- **Hierarchical path counting**: `/ua/mobile-phones/xyz` counts for both domain and `/ua/mobile-phones`
- **Configurable path depth**: Default 2 levels of sub-path tracking

**Use Cases**:
- Frontend highlighting of brand mentions in AI responses
- Calculating brand visibility scores across prompt groups
- Analyzing which domains are most frequently cited by AI assistants
- Comparing citation patterns across different assistants/plans

---

#### 3.6.6 Complete Evaluation Workflow

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

### 3.7 Prompt Groups Management

**Purpose**: Organize and manage prompts in user-specific collections with authentication

The prompt groups system provides authenticated CRUD operations for organizing prompts into named collections. Each user has:
- **Common group** (auto-created, cannot be deleted): Default collection for frequently used prompts
- **Named groups**: Custom collections created by users

**Key Features**:
- **Brand tracking**: Groups can have brands with variations attached for enriched result analysis
- **Group-based enrichment**: Use `group_id` in enriched results to automatically apply group's brands

All endpoints require JWT authentication via `Authorization: Bearer {token}` header.

---

#### 3.7.1 List All Groups

```http
GET /prompt-groups/api/v1/groups
```

**Purpose**: Get all prompt groups for the authenticated user

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**:
```json
{
  "groups": [
    {
      "id": 1,
      "title": null,
      "is_common": true,
      "prompt_count": 15,
      "brand_count": 0,
      "created_at": "2025-12-01T10:00:00Z",
      "updated_at": "2025-12-09T14:30:00Z"
    },
    {
      "id": 2,
      "title": "My Favorites",
      "is_common": false,
      "prompt_count": 8,
      "brand_count": 2,
      "created_at": "2025-12-05T12:00:00Z",
      "updated_at": "2025-12-08T09:15:00Z"
    }
  ],
  "total": 2
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompt-groups/api/v1/groups"
```

**Key Features**:
- Returns common group (auto-created if missing) plus all named groups
- Includes prompt counts and brand counts for each group
- Sorted by creation date

**Use Case**: Display user's prompt collections in UI

---

#### 3.7.2 Create New Group

```http
POST /prompt-groups/api/v1/groups
```

**Purpose**: Create a new named prompt group with optional brands for tracking

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "title": "My Favorites",
  "brands": [
    {"name": "Moyo", "variations": ["Moyo", "Мойо", "moyo.ua"]},
    {"name": "Rozetka", "variations": ["Rozetka", "Розетка"]}
  ]
}
```

**Parameters**:
- `title` (required): Group title (1-255 characters, non-empty)
- `brands` (optional): List of brands to track
  - `name`: Brand display name (unique within group)
  - `variations`: List of text variations to detect (case-sensitive, supports Cyrillic)

**Response** (201 Created):
```json
{
  "id": 2,
  "title": "My Favorites",
  "is_common": false,
  "prompt_count": 0,
  "brand_count": 2,
  "created_at": "2025-12-09T15:00:00Z",
  "updated_at": "2025-12-09T15:00:00Z"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/prompt-groups/api/v1/groups" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Favorites",
    "brands": [
      {"name": "Moyo", "variations": ["Moyo", "Мойо"]}
    ]
  }'
```

**Use Case**: User creates custom collection for organizing prompts by category or project, with brands configured for enriched analysis

---

#### 3.7.3 Get Group Details

```http
GET /prompt-groups/api/v1/groups/{group_id}
```

**Purpose**: Get detailed information about a group including brands and all prompts

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**:
```json
{
  "id": 2,
  "title": "My Favorites",
  "is_common": false,
  "created_at": "2025-12-05T12:00:00Z",
  "updated_at": "2025-12-09T15:30:00Z",
  "brands": [
    {"name": "Moyo", "variations": ["Moyo", "Мойо", "moyo.ua"]},
    {"name": "Rozetka", "variations": ["Rozetka", "Розетка"]}
  ],
  "prompts": [
    {
      "binding_id": 10,
      "prompt_id": 456,
      "prompt_text": "Найкращий смартфон до 15 000 грн?",
      "added_at": "2025-12-08T09:15:00Z"
    },
    {
      "binding_id": 11,
      "prompt_id": 789,
      "prompt_text": "Де купити ноутбук в Києві?",
      "added_at": "2025-12-09T10:20:00Z"
    }
  ]
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompt-groups/api/v1/groups/2"
```

**Key Features**:
- Returns full group details with brands and all prompts
- Includes configured brands for enriched result analysis
- Each prompt includes binding metadata (when it was added)
- Prompts sorted by `added_at` timestamp

**Use Case**: Display group contents in UI for editing or evaluation selection

---

#### 3.7.4 Update Group

```http
PATCH /prompt-groups/api/v1/groups/{group_id}
```

**Purpose**: Update a group's title and/or brands

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request** (update title only):
```json
{
  "title": "Top Picks"
}
```

**Request** (update brands only):
```json
{
  "brands": [
    {"name": "Moyo", "variations": ["Moyo", "Мойо", "moyo.ua"]},
    {"name": "Citrus", "variations": ["Citrus", "Цитрус"]}
  ]
}
```

**Request** (clear all brands):
```json
{
  "brands": []
}
```

**Parameters**:
- `title` (optional): New group title (1-255 characters, non-empty)
- `brands` (optional): Brands to track
  - `null` or omitted = no change to brands
  - `[]` = clear all brands
  - `[{...}]` = replace with new brands

**Response**:
```json
{
  "id": 2,
  "title": "Top Picks",
  "is_common": false,
  "prompt_count": 8,
  "brand_count": 2,
  "created_at": "2025-12-05T12:00:00Z",
  "updated_at": "2025-12-09T16:00:00Z"
}
```

**Example**:
```bash
curl -X PATCH "http://localhost:8000/prompt-groups/api/v1/groups/2" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"title": "Top Picks", "brands": [{"name": "Moyo", "variations": ["Moyo"]}]}'
```

**Restrictions**:
- Cannot update the common group (returns 400 error)

**Use Case**: Rename group or update tracked brands as user reorganizes collections

---

#### 3.7.5 Delete Group

```http
DELETE /prompt-groups/api/v1/groups/{group_id}
```

**Purpose**: Delete a prompt group

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**: 204 No Content

**Example**:
```bash
curl -X DELETE "http://localhost:8000/prompt-groups/api/v1/groups/2" \
  -H "Authorization: Bearer eyJhbGc..."
```

**Key Features**:
- Cascade deletes all prompt bindings in the group
- Prompts themselves are NOT deleted (only the group membership)

**Restrictions**:
- Cannot delete the common group (returns 400 error)

**Use Case**: Remove unused group from user's collections

---

#### 3.7.6 Add Prompts to Group

```http
POST /prompt-groups/api/v1/groups/{group_id}/prompts
```

**Purpose**: Add prompts to a group

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "prompt_ids": [456, 789, 123]
}
```

**Parameters**:
- `prompt_ids` (required): List of prompt IDs to add (at least 1)

**Response**:
```json
{
  "added_count": 2,
  "skipped_count": 1,
  "bindings": [
    {
      "binding_id": 12,
      "prompt_id": 456,
      "prompt_text": "Найкращий смартфон до 15 000 грн?",
      "added_at": "2025-12-09T16:30:00Z"
    },
    {
      "binding_id": 13,
      "prompt_id": 789,
      "prompt_text": "Де купити ноутбук в Києві?",
      "added_at": "2025-12-09T16:30:00Z"
    }
  ]
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/prompt-groups/api/v1/groups/2/prompts" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"prompt_ids": [456, 789, 123]}'
```

**Key Features**:
- Idempotent: Prompts already in the group are skipped
- Returns count of added vs skipped prompts
- Returns only newly added bindings with full details

**Use Case**: Add prompts from search results to collection for tracking

---

#### 3.7.7 Remove Prompts from Group

```http
DELETE /prompt-groups/api/v1/groups/{group_id}/prompts
```

**Purpose**: Remove prompts from a group

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "prompt_ids": [456, 789]
}
```

**Parameters**:
- `prompt_ids` (required): List of prompt IDs to remove (at least 1)

**Response**:
```json
{
  "removed_count": 2
}
```

**Example**:
```bash
curl -X DELETE "http://localhost:8000/prompt-groups/api/v1/groups/2/prompts" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"prompt_ids": [456, 789]}'
```

**Key Features**:
- Removes prompt-group bindings (prompts remain in database)
- Returns count of actually removed prompts
- Silently ignores prompt IDs not in the group

**Use Case**: Clean up group by removing irrelevant prompts

---

#### 3.7.8 Authentication & Authorization

All prompt group endpoints require JWT authentication:

1. **Login** to get access token:
```bash
curl -X POST "http://localhost:8000/api/v1/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword"
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

2. **Use token** in subsequent requests:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/prompt-groups/api/v1/groups"
```

**Authorization Rules**:
- Users can only access their own groups
- Attempting to access another user's group returns 404 Not Found
- Common group is auto-created on first access

---

#### 3.7.9 Error Handling

**Common Errors**:

**401 Unauthorized** - Missing or invalid token:
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found** - Group doesn't exist or belongs to another user:
```json
{
  "detail": "Group with ID 999 not found"
}
```

**400 Bad Request** - Cannot modify common group:
```json
{
  "detail": "Cannot update the common group"
}
```

**400 Bad Request** - Invalid request data:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character"
    }
  ]
}
```

---

### 3.8 Complete Client Flow for topics/prompts suggesting

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

---

### 3.9 Billing Endpoints

**Purpose**: Pay-as-you-go billing system for consuming evaluation data

The billing system provides:
- **Credit grants** with FIFO expiration (signup credits expire first)
- **Consumption tracking** per evaluation (users pay once per evaluation)
- **Balance management** with transaction history

**Authentication**: All billing endpoints require JWT authentication via `Authorization: Bearer {token}` header.

**Configuration** (in `.env` or settings):
```bash
BILLING_SIGNUP_CREDITS=10.00              # Credits granted on signup
BILLING_SIGNUP_CREDITS_EXPIRY_DAYS=30     # Days until signup credits expire
BILLING_PRICE_PER_EVALUATION=1.00         # Cost per evaluation consumed
```

---

#### 3.9.1 Get Balance

```http
GET /billing/api/v1/balance
```

**Purpose**: Get current user balance and expiration info

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**:
```json
{
  "user_id": "abc123",
  "available_balance": "8.00",
  "expiring_soon_amount": "8.00",
  "expiring_soon_at": "2025-01-25T10:00:00Z"
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/billing/api/v1/balance"
```

**Key Features**:
- Returns total available balance (sum of non-expired credit grants)
- Shows amount expiring within 7 days and earliest expiration date
- Balance is FIFO: oldest expiring credits consumed first

---

#### 3.9.2 Top Up Balance

```http
POST /billing/api/v1/top-up
```

**Purpose**: Add credits to user account (typically from payment webhook)

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "amount": "25.00",
  "source": "payment",
  "expires_at": null
}
```

**Parameters**:
- `amount` (required): Credit amount to add
- `source` (optional): Credit source (default: "payment")
- `expires_at` (optional): Expiration datetime (null = never expires)

**Response**:
```json
{
  "new_balance": "33.00",
  "transaction_id": 456
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/billing/api/v1/top-up" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"amount": "25.00"}'
```

---

#### 3.9.3 Get Transactions

```http
GET /billing/api/v1/transactions
```

**Purpose**: Get transaction history for auditing

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `limit` (optional, default: 50): Max records to return
- `offset` (optional, default: 0): Pagination offset

**Response**:
```json
{
  "transactions": [
    {
      "id": 123,
      "transaction_type": "debit",
      "amount": "2.00",
      "balance_after": "8.00",
      "reason": "Report generation",
      "reference_type": "report",
      "reference_id": "42",
      "created_at": "2025-12-25T14:30:00Z"
    }
  ],
  "total": 15
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/billing/api/v1/transactions?limit=20"
```

---

### 3.10 Reports Endpoints

**Purpose**: Generate and manage prompt group reports with billing integration

The reports system provides:
- **Report preview**: See cost before generating
- **Report generation**: Charges for fresh (unconsumed) evaluations only
- **Historical snapshots**: Track what data was available at report time
- **Comparison**: See what's new since last report

**Key Concepts**:
- **Fresh evaluation**: An evaluation the user hasn't paid for yet
- **Consumed evaluation**: An evaluation already paid for (free to view again)
- **Report snapshot**: Point-in-time record of prompts and their evaluations

**Authentication**: All reports endpoints require JWT authentication.

---

#### 3.10.1 Preview Report

```http
GET /reports/api/v1/groups/{group_id}/preview
```

**Purpose**: Preview what generating a report would cost before committing

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**:
```json
{
  "group_id": 5,
  "total_prompts": 10,
  "prompts_with_data": 8,
  "prompts_awaiting": 2,
  "fresh_evaluations": 5,
  "already_consumed": 3,
  "estimated_cost": "5.00",
  "user_balance": "10.00",
  "affordable_count": 10,
  "needs_top_up": false
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/reports/api/v1/groups/5/preview"
```

**Key Features**:
- Shows how many prompts have evaluation data vs awaiting
- Calculates cost for fresh (uncharged) evaluations only
- Indicates if user has sufficient balance

---

#### 3.10.2 Generate Report

```http
POST /reports/api/v1/groups/{group_id}/generate
```

**Purpose**: Generate a report and charge for fresh evaluations

**Headers**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**Request**:
```json
{
  "title": "December Report",
  "include_previous": true
}
```

**Parameters**:
- `title` (optional): Custom report title
- `include_previous` (optional, default: true): Include previously consumed evaluations

**Response**:
```json
{
  "id": 42,
  "group_id": 5,
  "title": "December Report",
  "created_at": "2025-12-25T15:00:00Z",
  "total_prompts": 10,
  "prompts_with_data": 8,
  "prompts_awaiting": 2,
  "total_evaluations_loaded": 8,
  "total_cost": "5.00",
  "items": [
    {
      "prompt_id": 1,
      "prompt_text": "Best smartphone under $500?",
      "evaluation_id": 123,
      "status": "included",
      "is_fresh": true,
      "amount_charged": "1.00",
      "answer": {
        "response": "Based on current reviews...",
        "citations": [...],
        "timestamp": "2025-12-24T10:00:00Z"
      }
    }
  ]
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/reports/api/v1/groups/5/generate" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"include_previous": true}'
```

**Key Features**:
- Charges only for fresh evaluations (not previously consumed)
- Second report generation for same data is FREE (0.00 cost)
- Creates immutable snapshot of data at generation time
- Marks consumed evaluations so user won't be charged again

---

#### 3.10.3 Compare with Latest Report

```http
GET /reports/api/v1/groups/{group_id}/compare
```

**Purpose**: See what's changed since the last report

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**:
```json
{
  "group_id": 5,
  "last_report_at": "2025-12-20T10:00:00Z",
  "current_prompts_count": 12,
  "current_evaluations_count": 15,
  "new_prompts_added": 2,
  "new_evaluations_available": 4,
  "fresh_data_count": 4,
  "estimated_cost": "4.00",
  "user_balance": "10.00",
  "affordable_count": 10,
  "needs_top_up": false
}
```

**Example**:
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  "http://localhost:8000/reports/api/v1/groups/5/compare"
```

**Use Case**: Show "X fresh answers available" badge in UI

---

#### 3.10.4 List Reports

```http
GET /reports/api/v1/groups/{group_id}/reports
```

**Purpose**: List all reports for a group

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `limit` (optional, default: 20): Max reports to return
- `offset` (optional, default: 0): Pagination offset

**Response**:
```json
{
  "reports": [
    {
      "id": 42,
      "group_id": 5,
      "title": "December Report",
      "created_at": "2025-12-25T15:00:00Z",
      "total_prompts": 10,
      "prompts_with_data": 8,
      "prompts_awaiting": 2,
      "total_cost": "5.00"
    }
  ],
  "total": 3
}
```

---

#### 3.10.5 Get Report Details

```http
GET /reports/api/v1/groups/{group_id}/reports/{report_id}
```

**Purpose**: Get a specific report with all items

**Headers**:
```
Authorization: Bearer {jwt_token}
```

**Response**: Same as generate response (full report with items)

---

#### 3.10.6 Complete Reports Workflow

**Example: User generates reports over time**

```bash
# 1. User signs up (gets 10.00 credits)
# 2. Creates prompt group with 5 prompts
# 3. Evaluations complete for 3 prompts

# Preview report (see cost before generating)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/reports/api/v1/groups/5/preview"
# Response: fresh_evaluations=3, estimated_cost=3.00

# Generate first report (charges 3.00)
curl -X POST "http://localhost:8000/reports/api/v1/groups/5/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_previous": true}'
# Response: total_cost=3.00

# Check balance
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/billing/api/v1/balance"
# Response: available_balance=7.00

# Generate same report again - FREE!
curl -X POST "http://localhost:8000/reports/api/v1/groups/5/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_previous": true}'
# Response: total_cost=0.00 (no fresh data)

# Time passes... 2 more evaluations complete

# Compare with latest report
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/reports/api/v1/groups/5/compare"
# Response: fresh_data_count=2, estimated_cost=2.00

# Generate updated report (charges 2.00 for new data only)
curl -X POST "http://localhost:8000/reports/api/v1/groups/5/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_previous": true}'
# Response: total_cost=2.00

# Final balance: 5.00 (10 - 3 - 2)
```

**Key Billing Rules**:
1. **First report**: Charges for all available evaluations
2. **Same data again**: FREE (already consumed)
3. **New data added**: Charges only for fresh evaluations
4. **Previously consumed**: Always free to include

---

**Example Client Code** (Python):

```python
import asyncio
import httpx

async def get_prompts_for_business(company_url: str, iso_country_code: str, access_token: str):
    """
    Complete hybrid client flow for getting prompts.

    Returns both DB prompts (matched topics) and generated prompts (unmatched topics)
    for complete coverage.

    Args:
        company_url: Company website URL
        iso_country_code: ISO country code
        access_token: JWT access token from login
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        # Step 1: Get meta-info (discover matched and unmatched topics)
        meta_response = await client.get(
            "http://localhost:8000/prompts/api/v1/meta-info",
            params={"company_url": company_url, "iso_country_code": iso_country_code},
            headers=headers
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
                params={"topic_ids": matched_ids},
                headers=headers
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
                headers=headers,
                timeout=120.0  # Generation takes 30-60s
            )
            results["generated_prompts"] = gen_response.json()

        return results

# Usage
# First, login to get access token
login_response = await client.post(
    "http://localhost:8000/api/v1/login/access-token",
    data={"username": "user@example.com", "password": "yourpassword"}
)
access_token = login_response.json()["access_token"]

# Then get prompts with authentication
results = await get_prompts_for_business("moyo.ua", "UA", access_token)
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
# Complete client flow (with authentication)

# 1. Login to get access token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=yourpassword" \
  | jq -r '.access_token')

# 2. Get meta-info (requires authentication)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/prompts/api/v1/meta-info?company_url=moyo.ua&iso_country_code=UA"

# 3. Get prompts from DB (fast, ~50ms, requires authentication)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/prompts/api/v1/prompts?topic_ids=1&topic_ids=2"

# 4. Generate prompts if needed (slow, ~30-60s, requires OpenAI API key and authentication)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA&topics=Смартфони+і+телефони&brand_variations=moyo"
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
│   │   │   ├── similar_prompts.py       # Similar prompts search responses
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
│   ├── prompt_groups/                   # User prompt group management
│   │   ├── router.py                    # API endpoints (CRUD for groups)
│   │   ├── models/
│   │   │   ├── api_models.py            # Request/response models
│   │   │   └── brand_models.py          # Brand variation models
│   │   └── services/
│   │       ├── prompt_group_service.py         # Group CRUD, brand management
│   │       └── prompt_group_binding_service.py # Prompt-group bindings
│   │
│   ├── billing/                         # Pay-as-you-go billing system
│   │   ├── router.py                    # API endpoints (balance, top-up, transactions)
│   │   ├── models/
│   │   │   ├── api_models.py            # Request/response models
│   │   │   └── domain.py                # Domain models (BalanceInfo, ChargeResult)
│   │   └── services/
│   │       ├── balance_service.py       # Credit grants with FIFO expiration
│   │       ├── consumption_service.py   # Tracks consumed evaluations
│   │       ├── charge_service.py        # Orchestrator for charging
│   │       └── pricing.py               # Pricing strategies
│   │
│   ├── reports/                         # Report generation and management
│   │   ├── router.py                    # API endpoints (preview, generate, compare)
│   │   ├── models/
│   │   │   └── api_models.py            # Request/response models
│   │   └── services/
│   │       ├── report_service.py        # Report generation with billing
│   │       └── comparison_service.py    # Fresh data detection
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
