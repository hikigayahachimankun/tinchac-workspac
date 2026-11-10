from copy import deepcopy
from datetime import datetime

import pytest

from backend.app.services.temporal import boundary_status
from backend.app.models import DateValue
from backend.tests.test_verification import CASES, guarded, inputs


def test_expired_deadline_is_supported_but_current_availability_is_not():
    case = deepcopy(CASES[3])
    assert guarded(case).label == 'supported'
    c = case['extraction']['claims'][0]
    c['field_type'], c['raw_value'], c['normalized'] = 'current_availability', 'còn hạn', dict(text='còn hạn',money=None,date=None,url=None)
    case['output']['drafts'][0]['label'] = 'contradicted'
    case['output']['drafts'][0]['evidence'][0]['relation'] = 'contradicts'
    assert guarded(case).label == 'contradicted'
    assert guarded(case).reason_codes == ['DEADLINE_PASSED']


@pytest.mark.parametrize(('stamp','status'), [
    ('2026-11-09T16:59:59Z','active'), ('2026-11-09T17:00:00Z','unknown'),
    ('2026-11-10T16:59:59Z','unknown'), ('2026-11-10T17:00:00Z','expired'),
])
def test_date_only_uses_vietnam_day_without_inventing_closing_time(stamp,status):
    value = DateValue(value='2026-11-10',precision='date',timezone='Asia/Ho_Chi_Minh',raw='10/11/2026',ambiguous=False)
    assert boundary_status(value,datetime.fromisoformat(stamp)) == status


def test_datetime_boundary_inclusive_and_timezone_equivalent():
    value = DateValue(value='2026-11-10T16:00:00+07:00',precision='datetime',timezone='Asia/Ho_Chi_Minh',raw='16h',ambiguous=False)
    assert boundary_status(value,datetime.fromisoformat('2026-11-10T09:00:00Z')) == 'active'
    assert boundary_status(value,datetime.fromisoformat('2026-11-10T09:00:00.000001Z')) == 'expired'


def test_release_not_published_or_effective_deadline():
    case = deepcopy(CASES[3])
    case['bundles'][0]['hits'][0]['source']['available_at'] = '2026-11-13T00:00:00Z'
    assert guarded(case).reason_codes == ['NO_SOURCE']
    case = deepcopy(CASES[3])
    source = case['bundles'][0]['hits'][0]['source']
    source['effective_to'] = dict(value='2026-11-11',precision='date',timezone='Asia/Ho_Chi_Minh',raw='11/11/2026',ambiguous=False)
    assert guarded(case).label == 'supported'
    assert guarded(case).temporal_status == 'expired'


def test_newer_without_reviewed_replacement_is_conflict_and_future_extension_cannot_replace():
    case = deepcopy(CASES[5])
    case['bundles'][0]['hits'][0]['source']['supersedes_version_id'] = None
    assert guarded(case).reason_codes == ['SOURCE_CONFLICT']
    case = deepcopy(CASES[5])
    case['bundles'][0]['hits'][0]['source']['available_at'] = '2026-11-10T00:00:00Z'
    assert guarded(case).label == 'insufficient_evidence'


def test_year_is_never_inferred_from_scope_or_provider_normalization():
    case = deepcopy(CASES[4])
    _,claims,_,reports,_ = inputs(case)
    assert claims[0].scope.academic_year == '2026-2027'
    assert claims[0].normalized.date.value is None
    assert reports[0].needs_more_evidence
