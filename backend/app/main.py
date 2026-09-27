"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers import admin, auth, plan, progress

# Imported for their side effect: registering the tables on Base.metadata.
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates any missing tables at startup. Alembic remains the tool for
    # changing tables that already exist.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Learning Tracker API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(progress.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
