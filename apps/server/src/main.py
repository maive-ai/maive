import tomllib
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.ai.chat.router import router as chat_router
from src.ai.voice_ai.router import router as voice_ai_router
from src.auth.router import router as auth_router
from src.config import get_client_base_url
from src.db.call_list.router import router as call_list_router
from src.integrations.creds.router import router as creds_router
from src.integrations.crm.mcp import get_crm_mcp_server
from src.integrations.crm.router import router as crm_router
from src.workflows.router import router as workflows_router
from src.utils.logger import logger


def get_version():
    """Get version from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


# Initialize MCP server and app first (needed for lifespan)
try:
    crm_mcp = get_crm_mcp_server()
    crm_mcp_app = crm_mcp.http_app(path='')
    logger.info("CRM MCP app created")
except Exception as e:
    logger.warning("Failed to create CRM MCP app", error=str(e))
    crm_mcp_app = None


# Use MCP app's lifespan directly (per FastMCP docs)
app = FastAPI(
    title="Maive API",
    description="API for Maive application",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=crm_mcp_app.lifespan if crm_mcp_app else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_client_base_url()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP server for CRM tools
if crm_mcp_app:
    app.mount("/crm", crm_mcp_app)
    logger.info("CRM MCP server mounted at /crm/mcp")

app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(creds_router, prefix="/api")
app.include_router(crm_router, prefix="/api")
app.include_router(voice_ai_router, prefix="/api")
app.include_router(call_list_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "Maive API is running"}


@app.get("/healthcheck")
async def healthcheck():
    """Health check endpoint."""
    return {"status": "ok", "message": "Maive API is running"}
