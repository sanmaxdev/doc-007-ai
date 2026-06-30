"""Aggregates business routers under the /api/v1 prefix.

(Health/readiness live at the root and are wired in `main.py`.)
"""

from __future__ import annotations

from fastapi import APIRouter

from doc007.api.v1.routers import (
    analytics,
    apikeys,
    auth,
    chat,
    documents,
    invitations,
    search,
    usage,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(
    documents.router,
    prefix="/workspaces/{workspace_id}/documents",
    tags=["documents"],
)
api_router.include_router(
    chat.router,
    prefix="/workspaces/{workspace_id}/chat",
    tags=["chat"],
)
api_router.include_router(
    search.router,
    prefix="/workspaces/{workspace_id}/search",
    tags=["search"],
)
api_router.include_router(
    apikeys.router,
    prefix="/workspaces/{workspace_id}/api-keys",
    tags=["api-keys"],
)
api_router.include_router(
    usage.router,
    prefix="/workspaces/{workspace_id}/usage",
    tags=["usage"],
)
api_router.include_router(
    analytics.router,
    prefix="/workspaces/{workspace_id}/analytics",
    tags=["analytics"],
)
