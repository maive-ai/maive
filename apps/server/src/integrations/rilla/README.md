# Rilla API Client

A comprehensive Python client for the Rilla Customer API, providing async methods to export conversations, teams, and users data.

## Features

- ✅ **Full API Coverage**: Support for all Rilla API endpoints
- ✅ **Type Safety**: Complete Pydantic models for request/response validation
- ✅ **Async/Await**: Built on httpx for high-performance async operations
- ✅ **Error Handling**: Comprehensive error handling with custom exceptions
- ✅ **Auto-Pagination**: Automatic pagination support for conversations
- ✅ **Rate Limiting**: Built-in rate limiting and retry logic
- ✅ **Configuration**: Environment variable configuration support
- ✅ **Logging**: Structured logging with sensitive data masking

## Installation

The Rilla client is included in the backend package. Make sure you have the required dependencies:

```bash
cd apps/backend
uv sync
```

## Configuration

Configure the client using environment variables:

```bash
# Required
RILLA_API_KEY=your-rilla-api-key-here

# Optional (with defaults)
RILLA_BASE_URL=https://customer.rillavoice.com
RILLA_TIMEOUT=30
RILLA_MAX_RETRIES=3
RILLA_RETRY_DELAY=1.0
RILLA_MAX_RETRY_DELAY=60.0
RILLA_BACKOFF_FACTOR=2.0
RILLA_REQUESTS_PER_MINUTE=60
RILLA_BURST_LIMIT=10
RILLA_LOG_REQUESTS=false
RILLA_LOG_RESPONSES=false
RILLA_MASK_SENSITIVE_DATA=true
```

## Usage Examples

### Basic Usage

```python
import asyncio
from datetime import datetime
from src.integrations.rilla import RillaClient, ConversationsExportRequest

async def main():
    # Initialize client (uses environment variables)
    async with RillaClient() as client:
        # Create request for date range
        request = ConversationsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1),
            page=1,
            limit=25
        )
        
        # Export conversations
        response = await client.export_conversations(request)
        
        print(f"Found {response.total_conversations} conversations")
        print(f"Page {response.current_page} of {response.total_pages}")
        
        for conversation in response.conversations:
            print(f"- {conversation.title} ({conversation.duration}s)")

# Run the async function
asyncio.run(main())
```

### Custom Configuration

```python
from src.integrations.rilla import RillaClient
from src.integrations.rilla.config import RillaSettings

# Custom settings
settings = RillaSettings(
    api_key="your-api-key",
    timeout=60,
    max_retries=5,
    log_requests=True,
)

async with RillaClient(settings=settings) as client:
    # Use client with custom settings
    pass
```

### Export All Conversations (Auto-Pagination)

```python
from src.integrations.rilla import RillaClient, ConversationsExportRequest

async def export_all_conversations():
    async with RillaClient() as client:
        request = ConversationsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1),
            # page parameter is ignored - all pages fetched automatically
        )
        
        # This will automatically fetch all pages
        all_conversations = await client.get_all_conversations(request)
        
        print(f"Retrieved {len(all_conversations)} total conversations")
        return all_conversations
```

### Filter by Users

```python
# Export conversations for specific users only
request = ConversationsExportRequest(
    from_date=datetime(2024, 3, 1),
    to_date=datetime(2024, 4, 1),
    users=["user1@company.com", "user2@company.com"]
)

response = await client.export_conversations(request)
```

### Export Teams Data

```python
from src.integrations.rilla import TeamsExportRequest

async def export_teams():
    async with RillaClient() as client:
        request = TeamsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1)
        )
        
        response = await client.export_teams(request)
        
        for team in response.teams:
            print(f"Team: {team.name}")
            print(f"  Conversations: {team.conversations_recorded}")
            print(f"  Compliance: {team.recording_compliance:.2%}")
```

### Export Users Data

```python
from src.integrations.rilla import UsersExportRequest

async def export_users():
    async with RillaClient() as client:
        request = UsersExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1),
            users=None  # All users, or specify list of emails
        )
        
        response = await client.export_users(request)
        
        for user in response.users:
            print(f"User: {user.name} ({user.email})")
            print(f"  Role: {user.role}")
            print(f"  Conversations: {user.conversations_recorded}")
            print(f"  Talk Ratio: {user.talk_ratio_average:.2%}")
```

### Error Handling

```python
from src.integrations.rilla import (
    RillaClient,
    RillaAuthenticationError,
    RillaBadRequestError,
    RillaRateLimitError,
    RillaServerError,
    ConversationsExportRequest
)

async def handle_errors():
    try:
        async with RillaClient() as client:
            request = ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1)
            )
            
            response = await client.export_conversations(request)
            
    except RillaAuthenticationError:
        print("Authentication failed - check your API key")
        
    except RillaBadRequestError as e:
        print(f"Bad request: {e.message}")
        print(f"Request data: {e.request_data}")
        
    except RillaRateLimitError as e:
        print(f"Rate limited - retry after {e.retry_after} seconds")
        
    except RillaServerError as e:
        print(f"Server error ({e.status_code}): {e.message}")
```

### Using with FastAPI

```python
from fastapi import FastAPI, Depends, HTTPException
from src.integrations.rilla import RillaClient, ConversationsExportRequest

app = FastAPI()

async def get_rilla_client() -> RillaClient:
    """Dependency to provide Rilla client."""
    client = RillaClient()
    await client._ensure_client()
    try:
        yield client
    finally:
        await client.close()

@app.get("/conversations")
async def get_conversations(
    from_date: datetime,
    to_date: datetime,
    client: RillaClient = Depends(get_rilla_client)
):
    """Get conversations for date range."""
    try:
        request = ConversationsExportRequest(
            from_date=from_date,
            to_date=to_date
        )
        
        response = await client.export_conversations(request)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Logging Configuration

```python
import logging

# Configure logging to see Rilla client logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.integrations.rilla")

# Set to DEBUG for detailed request/response logging
logger.setLevel(logging.DEBUG)
```

## Data Models

### Request Models

- `ConversationsExportRequest`: Parameters for conversations export
- `TeamsExportRequest`: Parameters for teams export  
- `UsersExportRequest`: Parameters for users export

### Response Models

- `ConversationsExportResponse`: Paginated conversations response
- `TeamsExportResponse`: Teams with analytics
- `UsersExportResponse`: Users with analytics

### Data Models

- `Conversation`: Individual conversation data
- `Team`: Team information with analytics
- `UserWithAnalytics`: User information with analytics
- `Checklist`: Conversation checklist data
- `TrackerData`: Individual tracker within checklist

## Error Handling

The client provides specific exception types:

- `RillaAPIError`: Base exception for all API errors
- `RillaAuthenticationError`: Invalid API key (401)
- `RillaBadRequestError`: Malformed request (400)
- `RillaRateLimitError`: Rate limit exceeded (429)
- `RillaServerError`: Server errors (5xx)
- `RillaTimeoutError`: Request timeout
- `RillaConnectionError`: Connection failed

## Rate Limiting

The client includes built-in rate limiting:

- Configurable requests per minute
- Burst limit for short periods
- Automatic retry with exponential backoff
- Respect for `Retry-After` headers

## Best Practices

1. **Use Context Manager**: Always use `async with RillaClient()` to ensure proper cleanup
2. **Handle Specific Errors**: Catch specific exception types for better error handling
3. **Configure Logging**: Enable request/response logging for debugging
4. **Use Auto-Pagination**: Use `get_all_conversations()` for complete data sets
5. **Environment Variables**: Store API keys in environment variables, not code
6. **Connection Reuse**: Create one client instance and reuse it for multiple requests

## Thread Safety

The client is designed for async/await usage and is not thread-safe. Create separate client instances for different threads or use proper async coordination.
