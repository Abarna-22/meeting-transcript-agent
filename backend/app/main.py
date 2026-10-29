import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routes import auth, meetings, query
from .services.embedder import get_embedder
from .services.llm import get_llm

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_embedder()  # load the model once at startup, not on the first upload
    get_llm()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Meeting Transcript Intelligence", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(meetings.router)
    app.include_router(query.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "embedder": get_embedder().name, "llm_mode": get_llm().mode}

    return app


app = create_app()
