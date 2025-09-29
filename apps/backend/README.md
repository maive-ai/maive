# Backend

Python backend services for the Maive application.

## Features

- **Rilla API Client**: Complete async client for Rilla Customer API with auto-pagination, error handling, and type safety

## Development

This project uses `uv` for dependency management and virtual environments.

### Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

### Running

```bash
# Install dependencies
uv sync

# Run with uv
uv run python -m backend

# Or activate venv and run normally  
source .venv/bin/activate
python -m backend
```

### Testing

```bash
uv run pytest
```

### Linting and Formatting

```bash
uv run ruff check
uv run ruff format
```

## Rilla API Client

The backend includes a comprehensive async client for the Rilla Customer API.

### Quick Start

```python
import asyncio
from datetime import datetime, timedelta
from backend.rilla import RillaClient, ConversationsExportRequest

async def main():
    async with RillaClient() as client:  # Uses RILLA_API_KEY env var
        request = ConversationsExportRequest(
            from_date=datetime.now() - timedelta(days=30),
            to_date=datetime.now()
        )
        
        response = await client.export_conversations(request)
        print(f"Found {response.total_conversations} conversations")

asyncio.run(main())
```

### Example Usage

See `example_usage.py` for a complete demonstration:

```bash
RILLA_API_KEY=your-api-key uv run python example_usage.py
```

### Configuration

Configure via environment variables:

```bash
RILLA_API_KEY=your-api-key           # Required
RILLA_BASE_URL=https://...           # Optional
RILLA_TIMEOUT=30                     # Optional  
RILLA_LOG_REQUESTS=true              # Optional
```

### Features

- ✅ **Full API Coverage**: All Rilla endpoints (conversations, teams, users)
- ✅ **Auto-Pagination**: Automatic handling of paginated results
- ✅ **Type Safety**: Complete Pydantic models for all requests/responses  
- ✅ **Error Handling**: Specific exceptions for different error types
- ✅ **Rate Limiting**: Built-in rate limiting and retry logic
- ✅ **Async/Await**: High-performance async operations
- ✅ **Logging**: Structured logging with sensitive data masking

See `src/backend/rilla/README.md` for detailed documentation.
