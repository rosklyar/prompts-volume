# Prompts Volume - E-Commerce Prompt Generation Service

AI-powered service that generates conversational, e-commerce product search prompts based on keyword analysis, semantic clustering, and LLM transformation.

---

## Prompt Generation Algorithm

### Overview

The service implements a **9-step ML pipeline** that transforms a company website URL and target country into natural, conversational product search prompts in the local language (e.g., Ukrainian, English).

**Input**: `company_url` + `iso_country_code`
**Output**: Structured prompts organized by business topics and keyword clusters

**Pipeline**: URL → Keywords → Embeddings → Clusters → Topics → Prompts

---

## Detailed Algorithm Steps

### Step 1: URL Validation & Domain Extraction

**Purpose**: Validate and normalize the input URL

**Process**:
1. Validate URL format and accessibility
2. Extract bare domain (remove `www.`, protocol, paths)
3. Example: `https://www.moyo.ua/shop/` → `moyo.ua`

**Implementation**: `src/utils/url_validator.py`

---

### Step 2: Country & Language Lookup

**Purpose**: Determine target location and language for keyword fetching

**Process**:
1. Map ISO country code (e.g., `UA`) to country name (`Ukraine`)
2. Get preferred language(s) for the country (`Ukrainian`)
3. Supports 94 countries with language mappings

**Implementation**: `src/config/countries.py`

**Example**:
```
UA → Ukraine, Ukrainian
US → United States, English
```

---

### Step 3: Keyword Fetching (DataForSEO API)

**Purpose**: Fetch all keywords where the domain currently ranks in Google

**Process** (Paginated):
1. Call DataForSEO Ranked Keywords API with `offset` and `limit`
2. **Batch size**: 1,000 keywords per request
3. **Maximum total**: 10,000 keywords
4. Loop until:
   - Batch size < 1,000 (last page), OR
   - Total keywords ≥ 10,000 (limit reached), OR
   - Empty batch (no more keywords)

**Implementation**: `src/prompts/data_for_seo_service.py` → `get_all_keywords_for_site()`

**Example pagination**:
```
offset=0, limit=1000 → 1,000 keywords
offset=1000, limit=1000 → 1,000 keywords
offset=2000, limit=1000 → 734 keywords (stop)
Total: 2,734 keywords
```

---

### Step 4: Company Metadata Retrieval

**Purpose**: Get business topics and brand name variations

**Current Implementation** (Hardcoded for MVP):
- **Topics**: 10 e-commerce categories
  - `["Apple", "Смартфони і телефони", "Ноутбуки", "Планшети", "Персональні комп'ютери", "Телевізори", "Аудіотехніка", "Техніка для дому", "Техніка для кухні", "Ігрові консолі"]`
- **Brand variations**: `["moyo", "мойо"]` (for filtering)

**Implementation**: `src/prompts/company_meta_info_service.py`

**TODO**: Replace with database/API lookup based on domain analysis

---

### Step 5: Keyword Filtering (3-Stage Filter)

**Purpose**: Clean and reduce keyword set to high-quality candidates

**Filter Chain**:

#### Filter 1: Word Count ≥ 3
- Keep only keywords with 3+ words
- Removes single-word queries (too generic)
- Example: `"tv"` → ❌, `"smart tv 4k"` → ✅

#### Filter 2: Brand Exclusion
- Remove keywords containing brand name variations (case-insensitive)
- Prevents brand-focused queries (not useful for product search)
- Example: `"moyo київ"` → ❌, `"телефон samsung"` → ✅

#### Filter 3: Deduplication
- Remove exact duplicates (case-sensitive)
- Preserve first occurrence, maintain order
- Example: `["laptop", "phone", "laptop"]` → `["laptop", "phone"]`

**Implementation**: `src/utils/keyword_filters.py`

**Typical reduction**: 10,000 → ~6,500 keywords

---

### Step 6: Embedding Generation

**Purpose**: Convert keywords to semantic vector representations

**Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensions**: 384
- **Languages**: 50+ (including Ukrainian, Russian, English)
- **Training**: Paraphrase detection, multilingual

**Process**:
1. Batch keywords (64 per batch)
2. Generate embeddings via sentence transformer
3. Output: `keyword → 384-dimensional vector`

**Implementation**: `src/embeddings/embeddings_service.py`

**Why embeddings?**
- Captures semantic meaning (not just word matching)
- Enables clustering of similar concepts
- Multilingual support for Ukrainian/Russian keywords

---

### Step 7: Clustering (HDBSCAN)

**Purpose**: Group semantically similar keywords into clusters

**Algorithm**: HDBSCAN (Hierarchical Density-Based Spatial Clustering)
- **Density-based**: Finds clusters of varying shapes/sizes
- **Hierarchical**: Builds cluster hierarchy
- **Noise handling**: Labels outliers as noise (-1)

**Parameters**:
- `min_cluster_size=5`: Minimum keywords per cluster
- `min_samples=5`: Minimum core points for density
- `cluster_selection_epsilon=0.0`: Cluster merging threshold

**Subclustering** (for large clusters):
- If cluster size > 25 keywords (5× min_cluster_size)
- Recursively apply HDBSCAN to split
- Prevents oversized, heterogeneous clusters

**Implementation**: `src/embeddings/clustering_service.py`

**Output**:
```python
{
  0: ["смартфон samsung", "телефон galaxy", ...],  # 15 keywords
  1: ["ноутбук lenovo", "laptop dell", ...],      # 12 keywords
  -1: ["irrelevant query", ...]                    # noise
}
```

**Typical results**: 60-80 clusters, ~5% noise

---

### Step 8: Topic Relevance Filtering

**Purpose**: Match clusters to business topics and filter by relevance

**Algorithm**:

1. **Generate topic embeddings**
   - Embed each topic name (e.g., `"Смартфони і телефони"`)
   - Output: 10 topic vectors (384-dim each)

2. **For each cluster**:
   - Calculate **cosine similarity** between:
     - All keyword embeddings in cluster (N keywords)
     - All topic embeddings (10 topics)
   - Matrix: `N keywords × 10 topics`

3. **Relevance scoring**:
   - For each keyword: `max_similarity_to_any_topic`
   - Count keywords with `max_similarity ≥ 0.7` (threshold)
   - Calculate `relevance_score = relevant_count / total_keywords`

4. **Filtering**:
   - Keep cluster if `relevance_score ≥ 0.5` (50% keywords relevant)
   - Assign cluster to **topic with highest average similarity**

5. **Organization**:
   - Group clusters by best-matching topic
   - Output: `{topic_name: [ClusterWithRelevance, ...]}`

**Implementation**: `src/embeddings/topic_relevance_filter_service.py`

**Parameters**:
- `similarity_threshold=0.7`: Cosine similarity cutoff for relevance
- `min_relevant_ratio=0.5`: Minimum 50% of keywords must be relevant

**Example**:
```python
Cluster 42: ["смартфон samsung", "телефон galaxy", "phone iphone"]
  → Similarity to "Смартфони і телефони": [0.82, 0.79, 0.75]
  → Relevance: 3/3 = 100% (all above 0.7)
  → Assigned to topic: "Смартфони і телефони"
```

**Typical reduction**: 67 clusters → 45 relevant clusters across 8 topics

---

### Step 9: Prompt Generation (OpenAI GPT-4o-mini)

**Purpose**: Transform keyword clusters into natural, conversational e-commerce prompts

**Process**:

#### 9.1 Language Detection
- Sample first 10 keywords from cluster
- Count Cyrillic (`\u0400-\u04FF`) vs Latin (`a-z`) characters
- Detect Ukrainian vs Russian (Ukrainian-specific: `і, ї, є, ґ`)
- Output: `"Ukrainian"`, `"Russian"`, or `"English"`

#### 9.2 Prompt Density Calculation
- `num_prompts = len(keywords) // 5`
- Generate **1 prompt per 5 keywords**
- Example: 23 keywords → 4 prompts

#### 9.3 LLM System Prompt Construction

**Key instructions to GPT-4o-mini**:

1. **Language**: Generate prompts in detected language (e.g., Ukrainian)
2. **Style**: SHORT (5-15 words), casual, conversational
3. **Examples** (Ukrainian e-commerce patterns):
   ```
   "Який телевізор краще купити до 10 000 грн?"
   "OLED чи QLED – що вибрати?"
   "Найкращий смартфон до 15 000 грн."
   "iPhone чи Samsung – що краще у 2025?"
   ```

4. **Intent transformation**:
   - **Direct searches** (`"лучший телефон"`)
     → `"Найкращий телефон до 10 000?"`

   - **How-to/tutorials** (`"як підключити джойстик до телефону"`)
     → `"Який телефон найкращий для ігор з джойстиком?"`

   - **Informational** (`"топ ноутбуків 2025"`)
     → `"Топ-5 ноутбуків 2025?"`

5. **Focus**: Product comparison, recommendations, budget constraints

#### 9.4 LLM Call & Response Parsing
- Call OpenAI API with `response_format={"type": "json_object"}`
- Parse JSON: `{"prompts": ["prompt1", "prompt2", ...]}`
- Validate: Correct count, non-empty strings

**Implementation**: `src/prompts/prompts_generator_service.py`

**Example transformation**:
```python
Keywords: ["інтересні ігри на телефон", "круті ігри на телефон",
           "найкращі ігри без інтернету", "безкоштовні ігри андроїд"]

Prompts: [
  "Найкращий телефон для ігор до 15 000 грн?",
  "Які безкоштовні ігри найкращі без інтернету?",
  "Топ-5 мобільних ігор 2025?"
]
```

---

## Complete Flow Example

```
INPUT:
  company_url: moyo.ua
  iso_country_code: UA

STEP 1: Domain Extraction
  → moyo.ua

STEP 2: Country Lookup
  → Ukraine, Ukrainian

STEP 3: Keyword Fetching (DataForSEO)
  Pagination:
    offset=0    → 1,000 keywords
    offset=1000 → 1,000 keywords
    offset=2000 → 1,000 keywords
    ...
    offset=9000 → 1,000 keywords
  → Total: 10,000 keywords

STEP 4: Metadata Retrieval
  → Topics: 10 categories
  → Brand: ["moyo", "мойо"]

STEP 5: Keyword Filtering
  Filter 1 (word count ≥3):  10,000 → 8,234
  Filter 2 (brand exclusion): 8,234 → 6,892
  Filter 3 (deduplication):   6,892 → 6,521
  → 6,521 keywords

STEP 6: Embedding Generation
  → 6,521 × 384-dimensional vectors

STEP 7: Clustering (HDBSCAN)
  → 67 clusters (189 noise keywords)
  → Subclustering: 3 large clusters split
  → Final: 72 clusters

STEP 8: Topic Relevance Filtering
  67 clusters evaluated:
    - 45 clusters match topics (≥50% relevance)
    - 22 clusters filtered out
  → 8 topics with clusters:
      Смартфони і телефони: 12 clusters
      Ноутбуки: 5 clusters
      Телевізори: 7 clusters
      ...

STEP 9: Prompt Generation (OpenAI)
  45 clusters → 234 prompts
  Language: Ukrainian (auto-detected)

  Example cluster:
    Cluster 114 (15 keywords about mobile games)
    → 3 prompts:
      1. "Найкращий телефон для ігор до 15 000 грн?"
      2. "Які безкоштовні ігри найкращі без інтернету?"
      3. "Топ-5 мобільних ігор 2025?"

OUTPUT:
{
  "topics": [
    {
      "topic": "Смартфони і телефони",
      "clusters": [
        {
          "cluster_id": 114,
          "keywords": ["інтересні ігри на телефон", ...],
          "prompts": ["Найкращий телефон для ігор...", ...]
        },
        ...
      ]
    },
    ...
  ]
}
```

---

## API Endpoint

### Request

```http
GET /prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA
```

**Parameters**:
- `company_url` (required): Company website URL
- `iso_country_code` (required): ISO 3166-1 alpha-2 country code

### Response

```json
{
  "topics": [
    {
      "topic": "Смартфони і телефони",
      "clusters": [
        {
          "cluster_id": 114,
          "keywords": [
            "інтересні ігри на телефон",
            "круті ігри на телефон",
            "найкращі ігри без інтернету"
          ],
          "prompts": [
            "Найкращий телефон для ігор до 15 000 грн?",
            "Які безкоштовні ігри найкращі без інтернету?"
          ]
        }
      ]
    }
  ]
}
```

---

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Embeddings** | sentence-transformers<br/>`paraphrase-multilingual-MiniLM-L12-v2` | Semantic vector representation (384-dim) |
| **Clustering** | HDBSCAN | Density-based clustering with noise handling |
| **Similarity** | Cosine similarity | Topic relevance scoring |
| **LLM** | OpenAI GPT-4o-mini | Ukrainian prompt generation |
| **Language Detection** | Character analysis | Cyrillic vs Latin, Ukrainian vs Russian |
| **Keyword Source** | DataForSEO API | Ranked keywords (paginated) |

---

## Configuration Parameters

| Parameter | Value | Location | Description |
|-----------|-------|----------|-------------|
| **Max keywords** | 10,000 | DataForSEO | Pagination limit |
| **Batch size** | 1,000 | DataForSEO | Keywords per API call |
| **Min word count** | 3 | Filter | Exclude short keywords |
| **Min cluster size** | 5 | HDBSCAN | Minimum keywords per cluster |
| **Min samples** | 5 | HDBSCAN | Density parameter |
| **Similarity threshold** | 0.7 | Topic filter | Cosine similarity cutoff |
| **Min relevant ratio** | 0.5 | Topic filter | 50% keywords must match |
| **Keywords per prompt** | 5 | OpenAI | Prompt generation density |
| **Embedding batch** | 64 | Embeddings | Processing batch size |

---

## Testing

**End-to-End Test**: `tests/test_generate_prompts.py`

Mocks DataForSEO API with sample data (`samples/moyo_ukr_keyword.json`) and tests complete pipeline.

**Run test**:
```bash
# Remove @pytest.mark.skip decorator first
uv run pytest tests/test_generate_prompts.py::test_prompts_generation -v -s
```

**Generate detailed report**:
```bash
WRITE_REPORT=true uv run pytest tests/test_generate_prompts.py::test_prompts_generation -v -s
```

---

## Tech Stack

- **Python 3.12**
- **FastAPI** - REST API framework
- **uv** - Dependency management and build tool
- **Docker** - Containerization
- **PostgreSQL** - State management (future)
- **sentence-transformers** - Multilingual embeddings
- **HDBSCAN** - Density-based clustering
- **scikit-learn** - Cosine similarity
- **OpenAI GPT-4o-mini** - Prompt generation
- **DataForSEO API** - Keyword research

---

## Project Structure

```
prompts-volume/
├── src/
│   ├── main.py                           # FastAPI app entry point
│   ├── config/
│   │   ├── countries.py                  # ISO → Country/Language mapping (94 countries)
│   │   └── settings.py                   # Environment variables
│   ├── prompts/
│   │   ├── router.py                     # /generate endpoint (main pipeline)
│   │   ├── models.py                     # Response models
│   │   ├── prompts_generator_service.py  # Step 9: OpenAI prompt generation
│   │   ├── data_for_seo_service.py       # Step 3: Keyword fetching
│   │   └── company_meta_info_service.py  # Step 4: Metadata (hardcoded)
│   ├── embeddings/
│   │   ├── embeddings_service.py         # Step 6: Sentence transformers
│   │   ├── clustering_service.py         # Step 7: HDBSCAN clustering
│   │   └── topic_relevance_filter_service.py # Step 8: Topic filtering
│   └── utils/
│       ├── keyword_filters.py            # Step 5: Filtering functions
│       └── url_validator.py              # Step 1: URL validation
├── tests/
│   └── test_generate_prompts.py          # End-to-end API test
├── samples/
│   └── moyo_ukr_keyword.json             # Sample keywords for testing
├── Dockerfile                             # Container configuration
├── .env.example                           # Environment variables template
└── README.md                              # This file
```

---

## Environment Variables

Required in `.env`:

```bash
# DataForSEO API credentials
DATAFORSEO_USERNAME=your_username
DATAFORSEO_PASSWORD=your_password

# OpenAI API key
OPENAI_API_KEY=sk-...

# Optional: OpenAI model (default: gpt-4o-mini)
PG_OPENAI_MODEL=gpt-4o-mini
```

---

## Running Locally

```bash
# 1. Setup environment
cp .env.example .env
# Add your API credentials to .env

# 2. Run application
uv run uvicorn src.main:app --reload

# 3. Test endpoint
curl "http://localhost:8000/prompts/api/v1/generate?company_url=moyo.ua&iso_country_code=UA"

# 4. View API docs
open http://localhost:8000/docs
```

---

## Docker

```bash
# Build image
docker build -t prompts-volume:latest .

# Run container
docker run -p 8000:8000 --env-file .env prompts-volume:latest
```
