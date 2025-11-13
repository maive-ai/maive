"""
Main router for scheduled groups API.

Combines sub-routers for group CRUD operations and member management.
"""

from fastapi import APIRouter

from src.db.scheduled_groups.routers import groups, members

router = APIRouter(prefix="/scheduled-groups", tags=["Scheduled Groups"])

# Include sub-routers
router.include_router(groups.router)
router.include_router(members.router)
