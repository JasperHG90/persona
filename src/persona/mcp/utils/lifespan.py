import os
import pathlib as plb
from contextlib import asynccontextmanager, contextmanager
from typing import Generator, cast
from typing import AsyncIterator

import yaml
from fastmcp import FastMCP, Context
from mcp.shared.context import RequestContext

from persona.config import parse_persona_config, PersonaConfig
from persona.storage import (
    get_file_store_backend,
    get_meta_store_backend,
    BaseMetaStoreSession,
    BaseFileStore,
)
from persona.embedder import get_embedding_model, FastEmbedder
from persona.mcp.models import AppContext
from persona.api import PersonaAPI
from .lib import library_skills


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Lifespan context manager for the the persona MCP server. Loads storage backend, configuration
    and index.
    """
    persona_config_path = (
        plb.Path.home() / '.persona.config.yaml'
        if not os.environ.get('PERSONA_CONFIG_PATH', None)
        else plb.Path(os.environ['PERSONA_CONFIG_PATH'])
    )
    if persona_config_path.exists():
        with persona_config_path.open('r') as f:
            config_raw = yaml.safe_load(f) or {}
        config_validated = PersonaConfig.model_validate(config_raw).model_dump()
        config = parse_persona_config(config_validated)
    else:
        config = parse_persona_config({})  # Will be read from env vars
    file_store = get_file_store_backend(config.file_store)
    # NB: read_only prevents changes from being persisted
    meta_store_engine = (
        get_meta_store_backend(config.meta_store, read_only=True).connect().bootstrap()
    )
    embedding_model = get_embedding_model()

    app_context = AppContext(config=config)
    app_context._file_store = file_store
    app_context._meta_store_engine = meta_store_engine
    app_context._embedding_model = embedding_model

    # Initialize API once for the lifetime of the server
    app_context._api = PersonaAPI(
        config=config,
        file_store=file_store,
        meta_store=meta_store_engine,
        embedder=embedding_model,
        library_skills=library_skills,
    )

    yield app_context
    meta_store_engine.close()


@contextmanager
def get_meta_store_session(ctx: Context) -> Generator[BaseMetaStoreSession, None, None]:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    meta_store = app_context._meta_store_engine
    with meta_store.read_session() as session:
        yield session


def get_api(ctx: Context) -> PersonaAPI:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context._api


def get_file_store(ctx: Context) -> BaseFileStore:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context._file_store


def get_embedder(ctx: Context) -> FastEmbedder:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context._embedding_model


def get_config(ctx: Context) -> PersonaConfig:
    app_context: AppContext = cast(RequestContext, ctx.request_context).lifespan_context
    return app_context.config
