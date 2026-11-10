"""Extraction only; retrieval and factual verdicts are owned by T07/T08."""
from pathlib import Path
import re
from unicodedata import normalize

from ..models import CheckCreate, ExtractionResult, check_quote
from .errors import ServiceError
from .llm import GeminiAdapter
from .normalization import normalize_claim

PROMPT = Path(__file__).resolve().parents[3] / 'prompts/extract.txt'
CONTACTS = re.compile(
    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'
    r'|(?<!\w)(?:\+84|0)(?:[ .-]?\d){8,10}(?!\d)'
    r'|(?i:(?:STK|số tài khoản|tài khoản)\s*[:：]?\s*)\d(?:[ .-]?\d){5,18}'
    r'|(?<!\d)\d{9,19}(?!\d)'
)


def redact(text: str) -> str:
    return CONTACTS.sub('[REDACTED]', normalize('NFC', text))


async def extract_claims(request: CheckCreate, *, llm: GeminiAdapter, corpus_version: str,
                         stage: str = 'dev', public: bool = False) -> ExtractionResult:
    text = redact(request.confirmed_text)
    changed = text != request.confirmed_text

    def validate(result: ExtractionResult):
        for claim in result.claims:
            if changed:
                claim.input_span = None
            elif claim.input_span is not None:
                check_quote(text, claim.input_span, claim.statement)
        result.claims = [normalize_claim(claim) for claim in result.claims]

    result = await llm.generate(prompt=PROMPT.read_text(), text=text, output_type=ExtractionResult,
                                corpus_version=corpus_version, as_of=request.as_of, stage=stage,
                                public=public and not changed, validate=validate)
    if not result.claims:
        raise ServiceError('NO_CHECKABLE_CLAIM', 'Không có phát biểu kiểm chứng được.', status=422)
    return result
