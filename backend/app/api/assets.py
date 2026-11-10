from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Header, Request, Response, UploadFile
from starlette.responses import JSONResponse
from starlette.formparsers import MultiPartException

from ..models import AssetCreated, AssetRecord, ErrorEnvelope

router = APIRouter(prefix='/api/v1/assets', tags=['assets'])
errors = {code: {'model': ErrorEnvelope} for code in (404, 410, 413, 415, 422, 429, 500)}


class UploadBodyLimit:
    """Bound multipart parsing, including fields and headers, before disk spooling."""
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.limit = min(max_bytes, 5242880) + 65536  # multipart envelope allowance

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/v1/assets':
            return await self.app(scope, receive, send)
        total = 0
        exceeded = False
        replied = False

        async def bounded_receive():
            nonlocal total, exceeded
            message = await receive()
            total += len(message.get('body', b''))
            if total > self.limit:
                exceeded = True
                # Starlette closes every multipart temporary file on this exception.
                raise MultiPartException('Upload exceeds byte limit')
            return message

        async def bounded_send(message):
            nonlocal replied
            if exceeded:
                if not replied:
                    replied = True
                    envelope = ErrorEnvelope(schema_version='1.0', request_id=str(uuid4()), error={
                        'code': 'INPUT_TOO_LARGE', 'message': 'Upload vượt giới hạn byte.',
                        'retryable': False, 'details': {}})
                    await JSONResponse(envelope.model_dump(mode='json'), status_code=413)(scope, receive, send)
            else:
                await send(message)

        await self.app(scope, bounded_receive, bounded_send)


@router.post('', status_code=202, response_model=AssetCreated, responses=errors)
def create_asset(file: UploadFile, request: Request, background_tasks: BackgroundTasks):
    try:
        data = file.file.read(min(request.app.state.settings.max_upload_bytes, 5242880) + 1)
        created = request.app.state.assets.create(data, file.content_type)
    finally:
        file.file.close()
    background_tasks.add_task(request.app.state.assets.run, str(created.asset.asset_id))
    return created


@router.get('/{asset_id}', response_model=AssetRecord, responses=errors)
def get_asset(asset_id: str, request: Request, x_resource_token: str = Header(default='')):
    return request.app.state.assets.get(asset_id, x_resource_token)


@router.delete('/{asset_id}', status_code=204, responses=errors)
def delete_asset(asset_id: str, request: Request, x_resource_token: str = Header(default='')):
    request.app.state.assets.delete(asset_id, x_resource_token)
    return Response(status_code=204)
