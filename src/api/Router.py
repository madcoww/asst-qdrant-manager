"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import Collection
from src.api.routes import Snapshots


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.core.Orchestrator import Orchestrator
    app.state.orchestrator = Orchestrator()
    app.state.orchestrator.logger.info('Orchestrator initialized')

    yield

    app.state.orchestrator.logger.info('Cleaning up resources')
    try:
        await app.state.orchestrator.cleanup_resources()
        app.state.orchestrator.logger.info('Cleanup completed successfully')
    except Exception as e:
        app.state.orchestrator.logger.info(f"Failed to get collection info: {str(e)}")

app = FastAPI(
    title='Athena-Qdrant-Manager',
    version='1.0.0',
    description='Qdrant Manager Service',
    lifespan=lifespan,
)

app.include_router(Collection.router)
app.include_router(Snapshots.router)
