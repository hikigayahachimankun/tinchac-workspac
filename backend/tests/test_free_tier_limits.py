from datetime import datetime,timezone
import json
import pytest

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.services.budget import Budget
from backend.app.services.errors import ServiceError


@pytest.fixture
def budget(tmp_path):
    settings=Settings(_env_file=None,llm_billing_mode='free_tier',database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    return Budget(settings)


def seed(budget,n,*,input_bound=1,created_at=None):
    with budget.db() as db:
        for i in range(n):
            db.execute('INSERT INTO llm_attempts(id,stage,metadata,reserved_nusd,charged_nusd,state,created_at) VALUES(?,?,?,?,?,?,COALESCE(?,CURRENT_TIMESTAMP))',
                (f'seed-{i}','dev',json.dumps({'billing_mode':'free_tier','input_bound':input_bound}),1,0,'settled',created_at))


def test_free_tier_rpm_prevents_provider_reservation(budget):
    seed(budget,15)
    with pytest.raises(ServiceError) as exc:budget.reserve(1,'dev',{'input_bound':1})
    assert exc.value.detail.code=='RATE_LIMITED'
    with budget.db() as db:assert db.execute('SELECT COUNT(*) FROM llm_attempts').fetchone()[0]==15


def test_free_tier_input_tpm_counts_reserved_bounds(budget):
    seed(budget,2,input_bound=125000)
    with pytest.raises(ServiceError) as exc:budget.reserve(1,'dev',{'input_bound':1})
    assert exc.value.detail.code=='RATE_LIMITED'


def test_free_tier_daily_cap_uses_current_pacific_day(budget):
    from zoneinfo import ZoneInfo
    pacific=datetime.now(ZoneInfo('America/Los_Angeles'))
    midnight=pacific.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    seed(budget,500,created_at=midnight.strftime('%Y-%m-%d %H:%M:%S'))
    with pytest.raises(ServiceError) as exc:budget.reserve(1,'dev',{'input_bound':1})
    assert exc.value.detail.code=='RATE_LIMITED'


def test_free_tier_pacing_reads_shared_ledger_without_creating_attempt(budget):
    seed(budget,1)
    assert 0 < budget.free_tier_delay() <= 5
    with budget.db() as db:assert db.execute('SELECT COUNT(*) FROM llm_attempts').fetchone()[0]==1


@pytest.mark.parametrize('status',[403,404,429])
def test_prior_provider_refusal_blocks_new_run_after_restart(budget,status):
    key=budget.reserve(1,'dev',{'input_bound':1},run_id='old')
    budget.finish(key,outcome=f'http_{status}')
    restarted=Budget(budget.settings)
    with pytest.raises(ServiceError) as exc:
        restarted.reserve(1,'demo',{'input_bound':1},run_id='new')
    assert exc.value.detail.details=={'quota_scope':'prior_provider_refusal','provider_http_status':status}
    with budget.db() as db:assert db.execute('SELECT COUNT(*) FROM llm_attempts').fetchone()[0]==1
