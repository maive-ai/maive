# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

**Maive** is a full-stack application built with:
- **Frontend**: React + Vite + TanStack Router (apps/web)
- **Backend**: FastAPI + Python (apps/server)
- **Infrastructure**: Pulumi + AWS Lambda (infra/)
- **Monorepo**: pnpm workspaces + Turbo

The codebase follows a **Generated API Client Pattern** where:
1. Backend generates OpenAPI spec from FastAPI schemas
2. TypeScript client is auto-generated from the spec (packages/api)
3. Frontend imports typed client functions for API calls

## Essential Commands

### Development
```bash
pnpm dev                    # Start all apps (web on :3000, server on :8080)
pnpm install                # Install all dependencies
```

### Building & Testing
```bash
pnpm build                  # Build all packages and apps
pnpm typecheck              # Check TypeScript across all packages
pnpm lint                   # Run ESLint across all packages
pnpm lint:fix               # Auto-fix ESLint issues
pnpm format                 # Check Prettier formatting
pnpm format:fix             # Auto-fix Prettier issues
```

### API Client Sync
```bash
pnpm api:sync               # Regenerate API client from backend schemas
```
This command runs whenever backend API changes and:
1. Generates OpenAPI spec from FastAPI (apps/server)
2. Cleans and regenerates TypeScript client (packages/api)
3. Validates frontend still typechecks

### Package-specific Operations
```bash
pnpm --filter=@maive/web dev         # Dev only web app
pnpm --filter=@maive/server test     # Test only server
pnpm --filter=@maive/api build       # Build only API package
```

### Infrastructure (Pulumi)
```bash
cd infra/
pulumi up -y                # Deploy infrastructure changes
pulumi logs --follow        # Follow Lambda logs
pulumi stack output --show-secrets    # Get deployment outputs
```

### Python Server (FastAPI)
```bash
cd apps/server/
uv run fastapi dev --app app src/main.py --port 8080    # Dev server
uv run python -m pytest tests/ -v --cov=src             # Run tests with coverage
uv run ruff check .                                     # Lint Python code
uv run ruff format .                                    # Format Python code
```

## Key Architecture Patterns

### Frontend API Integration
When adding new APIs:
1. Define FastAPI endpoints with proper schemas in apps/server
2. Run `pnpm api:sync` to regenerate client
3. Import generated types and functions in apps/web/src/clients/
4. Create wrapper functions that handle auth tokens via `getIdToken()`

### TanStack Router Configuration
- Uses `routeToken: 'layout'` enabling `layout.tsx` files in directories (NextJS-style)
- Route generation via `tsr generate`

### Authentication Flow
- AWS Cognito for user management
- Frontend uses generated client with automatic token injection
- MFA required for all user accounts

## Development Workflow

### Adding New Features
1. Backend: Define FastAPI endpoints with Pydantic schemas
2. Sync: Run `pnpm api:sync` to update client
3. Frontend: Import and use typed API client functions
4. Always run `pnpm typecheck` and `pnpm lint` before committing

### Infrastructure Changes
1. Modify Pulumi code in infra/
2. For Lambda changes: package functions first (see README pulumi section)
3. Deploy with `pulumi up -y`
4. Update local env files with new outputs if needed

### Package Management
- Uses pnpm workspaces with central catalog in pnpm-workspace.yaml
- Shared tooling configs in tools/ directory
- Internal packages prefixed with @maive/
- We use the 'uv' package manager for python
- We use pnpm for node packages

### Web Development
- We use tailwind css v4 in packages/tailwind-config. Use its styles when coloring things.

## Environment Setup Requirements
- Node.js 22.10.0+ (see .nvmrc)
- pnpm 10.12.3 (exact version required)
- UV for Python dependency management
- AWS CLI configured for infrastructure deployment
- Pulumi CLI for infrastructure management

## Running with Environment Variables
- When executing scripts that require environment variables, prefix the script with `esc run <current pulumi esc env> -- <script>`

## Coding Preferences

### Backend / Server Development
- For FastAPI best practices, please reference .cursor/rules/fastapi.mdc
- For python code quality best practices, please reference .cursor/rules/python.mdc

## Relevant Docs

### OpenAI AgentKit Docs
- We use OpenAI's AgentKit for orchestrating workflows in `apps/server/src/workflows/`
- Here are the docs: https://platform.openai.com/docs/guides/agents
- And the docs for the underlying Agents SDK, which enables agents to be built in Python: https://openai.github.io/openai-agents-python/

### Vapi
- We use Vapi for our Voice AI orchestration platform
- Their docs: https://docs.vapi.ai/quickstart/introduction
- You have an mcp server to manage our platform instance for vapi available called 'vapi-mcp'
- Open source UI components from Vapi are available at https://github.com/cameronking4/VapiBlocks/tree/master with docs at https://www.vapiblocks.com/docs