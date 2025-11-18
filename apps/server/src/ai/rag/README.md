# RAG System for Building Codes

This directory contains the Retrieval-Augmented Generation (RAG) system for ingesting and querying building codes from across the United States.

## Architecture

The RAG system supports two providers:

1. **OpenAI**: Uses OpenAI's native vector store and file_search tool
2. **Gemini**: Uses Google Gemini File Search stores

### OpenAI RAG Flow

```
Apify Scraper → Ingestion Service → OpenAI Vector Store
                                            ↓
RoofGPT Chat ←─────────────────── File Search Tool
```

### Gemini RAG Flow

```
Pricebook JSON → Ingestion Script → Gemini File Search Store
                                            ↓
GeminiProvider ←─────────────────── File Search Tool
```

### Components

- **`metadata.py`**: Pydantic models for document metadata (jurisdiction, code type, etc.)
- **`vector_store_service.py`**: Manages OpenAI vector store operations (upload, delete, list)
- **`ingestion_service.py`**: Processes Apify scraping results and uploads to vector store
- **`schemas.py`**: API request/response schemas (not currently exposed via REST)

## How It Works

### 1. Document Ingestion

Building codes are scraped via Apify and ingested into a single nationwide OpenAI vector store:

1. **Scraping**: Apify actor scrapes building code websites
2. **Parsing**: Ingestion service extracts metadata (city, state, code type, etc.)
3. **Embedding**: Documents are embedded with metadata prefix for better retrieval
4. **Storage**: Uploaded to OpenAI vector store with automatic chunking

### 2. Retrieval (RAG)

When a user asks a question:

1. **Query**: User asks about building codes (e.g., "What are Leawood's roofing requirements?")
2. **Search**: OpenAI's `file_search` tool automatically searches the vector store
3. **Context**: Relevant code sections are retrieved and added to the chat context
4. **Response**: RoofGPT responds with cited information from specific jurisdictions

## Usage

### Prerequisites

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-key"

# Set Apify API token (for ingestion)
export APIFY_API_TOKEN="your-token"
```

### Ingesting Documents

The ingestion script is located at `scripts/ingest_building_codes.py`.

#### Option 1: Fetch from Existing Apify Run

```bash
uv run python scripts/ingest_building_codes.py fetch-run --run-id <run_id>
```

#### Option 2: Run Apify Actor and Ingest

```bash
# Run actor with default input
uv run python scripts/ingest_building_codes.py run-actor --actor-id <actor_id>

# Run actor with custom input
uv run python scripts/ingest_building_codes.py run-actor \
    --actor-id <actor_id> \
    --input input.json
```

#### Option 3: Manual Upload

```bash
uv run python scripts/ingest_building_codes.py upload \
    --content "$(cat building_code.txt)" \
    --jurisdiction "Leawood" \
    --level city \
    --state KS \
    --code-type roofing \
    --title "Leawood Roofing Codes 2024"
```

### Check Vector Store Status

```bash
uv run python scripts/ingest_building_codes.py status
```

### Using RAG in Chat

The RAG system is automatically enabled in `RoofingChatService`. No changes needed in the frontend - just use the existing chat endpoint:

```bash
curl -X POST http://localhost:8080/api/chat/roofing \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the roofing requirements in Leawood, Kansas?"}
    ]
  }'
```

RoofGPT will automatically search the vector store and cite specific code sections.

## Metadata Structure

Documents are stored with hierarchical metadata:

```python
{
    "jurisdiction_name": "Leawood, Kansas",
    "jurisdiction_level": "city",  # international, national, state, county, city
    "city": "Leawood",
    "state": "KS",
    "code_type": "roofing",  # roofing, structural, fire, electrical, etc.
    "code_section": "Chapter 15",
    "document_title": "City of Leawood Building Codes",
    "source_url": "https://...",
    "version": "2024",
    "scrape_date": "2025-01-29T..."
}
```

Since OpenAI's vector store doesn't support custom metadata filtering yet, we embed metadata as a structured prefix in each document:

```
# Document Metadata
Jurisdiction: Leawood, Kansas
Level: city
Code Type: roofing
City: Leawood
State: KS
...

---

[Actual document content here]
```

## Code Hierarchy

Building codes follow a hierarchy:
- **International** → **National** → **State** → **County** → **City**

Cities may:
- Adopt international/national codes directly
- Adopt with local amendments
- Have completely custom codes

The ingestion service doesn't make assumptions about these relationships - it stores what's scraped and relies on the LLM to understand relationships during retrieval.

## Cost Estimates

OpenAI vector store pricing (as of Jan 2025):
- **Storage**: ~$0.10/GB/day
- **Search**: Included in response token usage (~$0.03/search)

**Typical usage** for 10-20 cities: $5-20/month

## Gemini File Search (Alternative to OpenAI)

Gemini File Search provides an alternative RAG solution using Google's Gemini API. It's particularly useful for pricebook data ingestion and querying.

### One-Time Ingestion

Upload your pricebook JSON file once to a Gemini File Search store:

```bash
# From apps/server directory
uv run python scripts/ingest_pricebook_gemini.py ingest
```

The script will:
1. Create a File Search store named "pricebook-items" (or use existing)
2. Upload the cleaned pricebook JSON file
3. Poll until indexing is complete
4. Print the **store name** (format: `fileSearchStores/xxxxx`)

**Important**: Copy the store name printed at the end - you'll need it for queries.

### Check Store Status

```bash
uv run python scripts/ingest_pricebook_gemini.py status
```

This shows the store name and confirms it's ready for queries.

### Using File Search in Queries

Pass the store name when calling `GeminiProvider`:

```python
from src.ai.providers.gemini import GeminiProvider

provider = GeminiProvider()

# Generate content with File Search
result = await provider.generate_content(
    prompt="What is the price for item XYZ?",
    file_search_store_names=["fileSearchStores/abc123"]
)

# Generate structured content with File Search
structured_result = await provider.generate_structured_content(
    prompt="Extract pricing information for item XYZ",
    response_schema=PriceInfoSchema,
    file_search_store_names=["fileSearchStores/abc123"]
)
```

### Gemini File Search Pricing

- **Embeddings at indexing**: $0.15 per 1M tokens
- **Storage**: Free of charge
- **Query time embeddings**: Free
- **Retrieved document tokens**: Charged as regular context tokens

### Supported File Types

Gemini File Search supports JSON files (and many other formats). See the [Gemini File Search documentation](https://ai.google.dev/gemini-api/docs/file-search#supported_file_types) for the full list.

### Rate Limits

- **Max file size**: 100 MB per document
- **Storage limits** (by tier):
  - Free: 1 GB
  - Tier 1: 10 GB
  - Tier 2: 100 GB
  - Tier 3: 1 TB
- **Recommendation**: Limit each store to <20 GB for optimal retrieval latency

**Note**: Storage limit is computed based on input size plus embeddings (typically ~3x input size).

## Troubleshooting

### Vector Store Not Found

If you get errors about missing vector store:

```bash
# Check status
uv run python scripts/ingest_building_codes.py status
```

The vector store is created automatically on first use, but you can pre-create it by running any ingestion command.

### Ingestion Failures

Common issues:
- **HTML parsing**: Some websites have complex HTML - check scraped content quality
- **Metadata extraction**: Review `ingestion_service.py` parsing logic for your specific sites
- **File size limits**: OpenAI has file size limits - split large documents if needed

### No Results in Chat

If RoofGPT isn't finding building codes:

1. **Check vector store has files**: Run `status` command
2. **Verify metadata**: Ensure jurisdiction names match user queries
3. **Test with explicit queries**: Try "Search for Leawood Kansas building codes"
4. **Review system prompt**: Make sure `system_prompt.md` mentions file search

## Future Enhancements

Potential improvements:
- [ ] Automatic relationship mapping (track which cities adopt which codes)
- [ ] Incremental updates (only re-sync changed documents)
- [ ] Scheduled background syncing
- [ ] Analytics on most-queried jurisdictions
- [ ] Support for images/diagrams in building codes
- [ ] Version tracking (historical code versions)

## Development

### Running Tests

```bash
cd apps/server
uv run pytest tests/ai/rag/ -v
```

### Adding New Code Types

Edit `metadata.py` and add to the `CodeType` enum:

```python
class CodeType(str, Enum):
    ROOFING = "roofing"
    YOUR_NEW_TYPE = "your_new_type"
```

### Improving Metadata Extraction

Edit `ingestion_service.py` methods:
- `_extract_jurisdiction_info()` - Better location parsing
- `_detect_code_type()` - Better code type detection
- `_extract_version()` - Better version extraction
