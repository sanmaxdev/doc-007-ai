"""Aggregates business routers under the /api/v1 prefix.

(Health/readiness live at the root and are wired in `main.py`.)
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Phase 1+: auth, workspaces, members, documents, chat, search, admin
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
