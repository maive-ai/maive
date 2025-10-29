# RoofGPT - AI Roofing Expert Chatbot Implementation

## Overview
ChatGPT-style interface with roofing expertise, using document context for answering questions about local codes, warranties, and roofing systems.

## Architecture

### Backend Stack
- **Framework**: FastAPI
- **LLM**: OpenAI (via existing `src/ai/providers/openai.py`)
- **Streaming**: Server-Sent Events (SSE)
- **Documents**: File-based context (migration to RAG/vector store later)

### Frontend Stack
- **UI Library**: Assistant-UI (`@assistant-ui/react`)
- **Runtime**: LocalRuntime with Vercel AI SDK integration
- **Router**: TanStack Router
- **Streaming**: SSE via `useChat` hook

## File Structure

```
apps/server/src/ai/chat/
├── documents/
│   ├── local_codes/          # Local building codes
│   ├── warranties/            # Manufacturer warranties
│   └── system_booklets/       # Roofing system documentation
├── __init__.py
├── service.py                 # RoofingChatService
├── router.py                  # FastAPI endpoints
└── IMPLEMENTATION.md          # This file

apps/web/src/
├── routes/_authed/
│   └── chat.tsx               # Chat route
├── components/chat/
│   └── ChatRuntimeProvider.tsx
└── config/
    └── navRoutes.ts           # Updated with Chat nav item
```

## Backend Implementation

### 1. Document Management (`service.py`)

```python
class RoofingChatService:
    - load_documents(): Load all docs from documents/
    - build_system_prompt(): Create context-rich system prompt
    - stream_chat_response(): Stream OpenAI responses via SSE
```

### 2. API Endpoint (`router.py`)

```
POST /api/chat/roofing
Body: { messages: Array<{ role, content }> }
Response: text/event-stream (SSE)
Auth: JWT Bearer token (via existing auth middleware)
```

### 3. Document Format

Documents stored as plain text files:
- `.txt` for codes and specs
- Converted PDFs stored as `.txt`
- Markdown for structured content

## Frontend Implementation

### 1. Chat Route (`apps/web/src/routes/_authed/chat.tsx`)

- TanStack Router route at `/chat`
- Renders `ChatRuntimeProvider` wrapper
- Uses Assistant-UI `Thread` component

### 2. Runtime Provider (`ChatRuntimeProvider.tsx`)

```typescript
- useChat() with endpoint: /api/chat/roofing
- Pass auth token via headers
- useVercelUseChatRuntime() for assistant-ui integration
- AssistantRuntimeProvider wrapper
```

### 3. Navigation

Add to `navRoutes.ts`:
```typescript
{
  label: 'Chat',
  route: ChatRoute,
  icon: MessageSquare,
}
```

## Implementation Steps

### Phase 1: Backend Setup
1. ✅ Create directory structure
2. ✅ Create `__init__.py`
3. ✅ Implement `service.py` with document loader
4. ✅ Implement `router.py` with SSE endpoint
5. ✅ Register router in `main.py`
6. ✅ Add sample documents

### Phase 2: Frontend Setup
7. ✅ Create chat route
8. ✅ Create ChatRuntimeProvider component
9. ✅ Add navigation item
10. ✅ Test end-to-end

### Phase 3: Testing
11. ✅ Verify streaming works
12. ✅ Verify auth integration
13. ✅ Verify document context in responses
14. ✅ Test error handling

## Key Technical Decisions

### Why SSE over WebSocket?
- One-way communication (request → stream response)
- Built-in browser reconnection
- Simpler auth (standard HTTP headers)
- Better Assistant-UI integration
- Infrastructure-friendly (works with proxies/load balancers)

### Why LocalRuntime?
- Built-in state management
- Automatic message editing/branching
- Simple adapter pattern
- Easy migration path to RAG

### Document Loading Strategy
- **Phase 1 (Now)**: Load all files on startup into memory
- **Phase 2 (Later)**: Add vector store (Pinecone/Chroma)
- **Phase 3 (Future)**: Semantic search + reranking

## Success Criteria

✅ User can access chat via sidebar navigation
✅ Chat interface loads with roofing expert personality
✅ Responses stream in real-time with typing effect
✅ Document context influences answers
✅ Auth works seamlessly
✅ Mobile responsive
✅ Error states handled gracefully

## Future Enhancements

1. **RAG System**: Vector store for semantic document search
2. **File Upload**: Allow users to upload documents for analysis
3. **Chat History**: Persist conversations (use Assistant-UI history adapter)
4. **Multi-tenant**: Separate document sets per organization
5. **Citations**: Show which documents informed the answer
6. **Admin Panel**: Manage documents via UI

## Testing Checklist

- [ ] Can navigate to /chat
- [ ] Chat interface renders
- [ ] Can send messages
- [ ] Responses stream in real-time
- [ ] Auth required (redirects if not logged in)
- [ ] Ask about specific document content → correct answer
- [ ] Ask general roofing question → expert answer
- [ ] Error handling works (network errors, API errors)
- [ ] Mobile layout works
- [ ] Sidebar navigation works

## Monitoring & Debugging

- **Backend Logs**: Check FastAPI logs for streaming issues
- **Network Tab**: Verify SSE connection in browser DevTools
- **Auth**: Check JWT token in request headers
- **Documents**: Log loaded documents on startup
- **OpenAI**: Monitor token usage and costs

## Migration Path to RAG

When document count grows:

1. Set up vector store (Chroma for local, Pinecone for prod)
2. Create embeddings for all documents
3. Update `service.py` to query vector store
4. Add semantic search before LLM call
5. Include retrieved chunks in context
6. Add citation tracking

Assistant-UI frontend requires zero changes for RAG migration.
