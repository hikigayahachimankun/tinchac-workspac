import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic.json_schema import models_json_schema
from starlette.exceptions import HTTPException

from .api.health import router
from .api.checks import router as checks_router
from .api.sources import router as sources_router
from .api.assets import router as assets_router, UploadBodyLimit
from .services.intake import Assets
from .services.jobs import Jobs
from .services.errors import ServiceError
from .config import Settings
from .models import CONTRACT_MODELS, ErrorEnvelope


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        jobs = app.state.jobs
        if app.state.settings.database_path.exists():
            await asyncio.to_thread(jobs.initialize)
            await asyncio.to_thread(app.state.assets.initialize)

        async def cleanup():
            while True:
                await asyncio.sleep(60)
                if app.state.settings.database_path.exists():
                    def purge():
                        with jobs.db() as db:
                            jobs.purge(db)
                            app.state.assets.purge(db)
                    await asyncio.to_thread(purge)

        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title='TinChắc', version='1.0', openapi_url='/api/v1/openapi.json', lifespan=lifespan)
    app.state.settings = settings if settings is not None else Settings()
    app.state.jobs = Jobs(app.state.settings)
    app.state.assets = Assets(app.state.jobs)
    app.state.jobs.assets = app.state.assets
    app.add_middleware(UploadBodyLimit, max_bytes=app.state.settings.max_upload_bytes)
    app.include_router(router)
    app.include_router(checks_router)
    app.include_router(sources_router)
    app.include_router(assets_router)

    @app.middleware('http')
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        return await call_next(request)

    def error_response(request: Request, status: int, code: str, message: str, details: dict):
        body = ErrorEnvelope(schema_version='1.0', request_id=request.state.request_id,
                             error={'code': code, 'message': message, 'retryable': False, 'details': details})
        return JSONResponse(status_code=status, content=body.model_dump(mode='json'))

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        body = ErrorEnvelope(schema_version='1.0', request_id=request.state.request_id, error=exc.detail)
        return JSONResponse(status_code=exc.status, content=body.model_dump(mode='json'))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Exclude raw input and ctx: they may contain private text or exception objects.
        errors = [{'loc': list(e['loc']), 'type': e['type']} for e in exc.errors()]
        return error_response(request, 422, 'INVALID_INPUT', 'Invalid request.', {'errors': errors})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = 'RESOURCE_NOT_FOUND' if exc.status_code == 404 else 'INVALID_INPUT'
        return error_response(request, exc.status_code, code, 'Request could not be handled.', {})

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return error_response(request, 500, 'INTERNAL_ERROR', 'Internal error.', {})

    original_openapi = app.openapi

    def contract_openapi():
        if app.openapi_schema is None:
            schema = original_openapi()
            _, definitions = models_json_schema(
                [(model, 'validation') for model in CONTRACT_MODELS],
                ref_template='#/components/schemas/{model}',
            )
            schema.setdefault('components', {}).setdefault('schemas', {}).update(definitions['$defs'])
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = contract_openapi

    if app.state.settings.frontend_dist is not None:
        dist = app.state.settings.frontend_dist.resolve()

        @app.api_route('/{path:path}', methods=['GET', 'HEAD'], include_in_schema=False)
        def frontend(path: str):
            # Serve only this build. API, dotfiles and repository/private paths
            # never become a successful SPA response, including missing assets.
            parts = Path(path).parts
            if parts and (parts[0] in ('api', 'data', 'backend', 'contracts', 'config')
                          or any(p.startswith('.') for p in parts)):
                raise HTTPException(404)
            target = (dist / path).resolve()
            if not target.is_relative_to(dist):
                raise HTTPException(404)
            allowed = {'.html', '.js', '.css', '.svg', '.ico', '.png', '.jpg', '.jpeg', '.webp', '.woff', '.woff2'}
            if target.is_file() and target.suffix in allowed:
                return FileResponse(target)
            if parts and parts[0] == 'assets':
                raise HTTPException(404)
            index = (dist / 'index.html').resolve()
            if not Path(path).suffix and index.is_relative_to(dist) and index.is_file():
                return FileResponse(index)
            raise HTTPException(404)
    return app


app = create_app()
