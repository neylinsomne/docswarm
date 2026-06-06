"""Agrega todos los routers v1 bajo /api/v1."""

from fastapi import APIRouter

from app.api.v1 import (
    auth, catalog, changes, companies, contracts, documents, notifications, search,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(catalog.router)
api_router.include_router(contracts.router)
api_router.include_router(changes.router)
api_router.include_router(documents.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
