"""Conservative field normalization. Never fill scope or a missing year."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from unicodedata import normalize
from urllib.parse import urlsplit, urlunsplit

from ..models import Claim, DateValue, MoneyValue, NormalizedValue, Scope


def folded(text: str) -> str:
    return ' '.join(normalize('NFC', text).casefold().split())


def normalize_url(value: str) -> str | None:
    """Only scheme/host case. Preserve path, query order, fragment and explicit port."""
    try:
        parts = urlsplit(value.strip())
        if (parts.scheme.lower() not in ('https', 'http') or not parts.hostname
                or parts.username is not None or parts.password is not None
                or any(c.isspace() for c in value)):
            return None
        # Validate port without silently changing it.
        _ = parts.port
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, parts.fragment))
    except ValueError:
        return None


def money_from_raw(raw: str) -> MoneyValue | None:
    text = folded(raw)
    matches = list(re.finditer(r'(?<![\w.,])(\d+(?:[.,]\d+)*)\s*(triệu|nghìn|ngàn|k|đồng|vnd|đ)(?!\w)', text))
    bases = [basis for pattern, basis in (
        (r'(?:/\s*suất|mỗi suất|một suất)', 'per_award'),
        (r'(?:/\s*năm|mỗi năm)', 'per_year'),
        (r'(?:/\s*tín chỉ|mỗi tín chỉ)', 'per_credit'),
        (r'(?:/\s*sinh viên|mỗi sinh viên)', 'per_student'),
    ) if re.search(pattern, text)]
    if len(matches) != 1 or len(bases) != 1:
        return None
    if re.search(r'\d', text[:matches[0].start()] + text[matches[0].end():]) or text[:matches[0].start()].rstrip().endswith(('-', '+')):
        return None
    number, unit = matches[0].groups()
    factor = {'triệu': 1000000, 'nghìn': 1000, 'ngàn': 1000, 'k': 1000}.get(unit, 1)
    if factor == 1:
        if not (number.isdigit() or re.fullmatch(r'\d{1,3}(?:\.\d{3})+', number)):
            return None
        number = number.replace('.', '')
    else:
        # Decimal fractions are permitted with magnitude units, never floats.
        if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', number):
            number = number.replace('.', '')
        elif number.count('.') + number.count(',') > 1:
            return None
        number = number.replace(',', '.')
    try:
        amount = Decimal(number) * factor
        if amount != amount.to_integral_value():
            return None
        return MoneyValue(amount=int(amount), currency='VND', basis=bases[0])
    except InvalidOperation:
        return None


def date_from_raw(raw: str) -> DateValue:
    unknown = DateValue(value=None, precision='unknown', timezone='Asia/Ho_Chi_Minh', raw=raw, ambiguous=True)
    # Exactly one complete date/time. Ranges and missing years stay ambiguous.
    text = raw.strip()
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
            return DateValue(value=date.fromisoformat(text).isoformat(), precision='date',
                             timezone='Asia/Ho_Chi_Minh', raw=raw, ambiguous=False)
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})', text):
            return DateValue(value=datetime.fromisoformat(text.replace('Z', '+00:00')).isoformat(),
                             precision='datetime', timezone='Asia/Ho_Chi_Minh', raw=raw, ambiguous=False)
        dates = list(re.finditer(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)', text))
        times = list(re.finditer(r'(?<!\d)(\d{1,2})\s*(?:h|:|giờ)\s*(\d{2})?(?!\d)', text))
        if len(dates) != 1 or len(times) > 1 or len(re.findall(r'\d{1,2}/\d{1,2}', text)) != 1:
            return unknown
        day, month, year = map(int, dates[0].groups())
        value = date(year, month, day).isoformat()
        if times:
            hour, minute = int(times[0][1]), int(times[0][2] or 0)
            value = datetime(year, month, day, hour, minute).isoformat() + '+07:00'
        return DateValue(value=value, precision='datetime' if times else 'date',
                         timezone='Asia/Ho_Chi_Minh', raw=raw, ambiguous=False)
    except ValueError:
        return unknown


def scope_compatible(claim: Scope, fact: Scope) -> bool:
    """A narrower fact cannot prove a broader claim. Null is never a wildcard."""
    if not claim.program and not claim.fee_kind:
        return False
    return all((left is None and right is None) or
               (left is not None and right is not None and folded(left) == folded(right))
               for key in Scope.model_fields
               for left, right in [(getattr(claim, key), getattr(fact, key))])


def normalize_claim(claim: Claim) -> Claim:
    result = claim.model_copy(deep=True)
    value = NormalizedValue(text=None, money=None, date=None, url=None)
    if result.field_type in ('award_amount', 'payment_amount'):
        value.money = money_from_raw(result.raw_value)
        if value.money is None:
            result.ambiguities.append('MONEY_AMBIGUOUS')
    elif result.field_type == 'deadline':
        value.date = date_from_raw(result.raw_value)
        if value.date.ambiguous:
            result.ambiguities.append('DATE_AMBIGUOUS')
    elif result.field_type == 'application_url':
        value.url = normalize_url(result.raw_value)
        if value.url is None:
            result.ambiguities.append('LINK_NOT_CONFIRMED')
    else:
        value.text = result.normalized.text
    if result.field_type in ('payment_amount', 'payment_requirement') and not result.scope.fee_kind:
        result.ambiguities.append('FEE_KIND_MISSING')
    result.normalized = value
    result.ambiguities = list(dict.fromkeys(result.ambiguities))
    return result
