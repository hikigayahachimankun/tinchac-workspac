from fastapi import APIRouter, Request

from ..models import ErrorEnvelope, SourcePublic
from ..services.errors import ServiceError

router = APIRouter(prefix='/api/v1/sources', tags=['sources'])


@router.get('/{version_id}', response_model=SourcePublic, responses={404: {'model': ErrorEnvelope}})
def get_source(version_id: str, request: Request):
    if request.app.state.settings.app_mode != 'fixture':
        raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy snapshot.', status=404)
    source = request.app.state.jobs.adapter.public
    if source.version_id != version_id:
        raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy snapshot.', status=404)
    return source
