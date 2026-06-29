"""Aggregates business routers under the /api/v1 prefix.

(Health/readiness live at the root and are wired in `main.py`.)
"""

from __future__ import annotations

from fastapi import APIRouter

from doc007.api.v1.routers import auth, documents, workspaces

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(
    documents.router,
    prefix="/workspaces/{workspace_id}/documents",
    tags=["documents"],
)

# Phase 3+: chat, search, admin
