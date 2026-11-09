import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..db import check_ready
from ..models import ErrorEnvelope, HealthResponse

router = APIRouter(prefix='/api/v1')


@router.get('/health', response_model=HealthResponse, responses={503: {'model': ErrorEnvelope}})
def health(request: Request):
    settings = request.app.state.settings
    try:
        check_ready(settings.database_path)
    except (sqlite3.Error, OSError):
        return JSONResponse(status_code=503, content=ErrorEnvelope(
            schema_version='1.0', request_id=request.state.request_id,
            error={'code': 'CORPUS_UNAVAILABLE', 'message': 'Database or FTS5 is not ready.',
                   'retryable': True, 'details': {}},
        ).model_dump(mode='json'))
    return HealthResponse(
        schema_version='1.0', status='ok', corpus_version='fixture-v1' if settings.app_mode == 'fixture' else 'unavailable',
        provider_configured=bool(settings.gemini_api_key.get_secret_value()), run_mode=settings.app_mode,
    )
