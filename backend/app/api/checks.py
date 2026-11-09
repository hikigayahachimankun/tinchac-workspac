from fastapi import APIRouter, BackgroundTasks, Header, Request, Response

from ..models import CheckCreate, CheckCreated, CheckRecord, ErrorEnvelope

router = APIRouter(prefix='/api/v1/checks', tags=['checks'])
errors = {code: {'model': ErrorEnvelope} for code in (404, 409, 410, 413, 422, 429, 500, 503)}


@router.post('', status_code=202, response_model=CheckCreated, responses=errors)
def create_check(body: CheckCreate, request: Request, background_tasks: BackgroundTasks):
    created = request.app.state.jobs.create(body)
    background_tasks.add_task(request.app.state.jobs.run, str(created.check.check_id))
    return created


@router.get('/{check_id}', response_model=CheckRecord, responses=errors)
def get_check(check_id: str, request: Request, x_resource_token: str = Header(default='')):
    return request.app.state.jobs.get(check_id, x_resource_token)


@router.delete('/{check_id}', status_code=204, responses=errors)
def delete_check(check_id: str, request: Request, x_resource_token: str = Header(default='')):
    request.app.state.jobs.delete(check_id, x_resource_token)
    return Response(status_code=204)
