"""Application contract 1.0. Runtime evidence checks belong to the pipeline."""
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, get_args
from unicodedata import normalize
from uuid import UUID

from pydantic import (
    AfterValidator, AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field,
    StrictBool, ValidationInfo, field_validator, model_validator,
)


def utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def iso_timestamp(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and 'T' in value:
        parsed = datetime.fromisoformat(value)
    else:
        raise ValueError('timestamp requires ISO datetime with offset')
    if parsed.utcoffset() is None:
        raise ValueError('timestamp requires offset')
    return value


Timestamp = Annotated[AwareDatetime, BeforeValidator(iso_timestamp), AfterValidator(utc)]
Count = Annotated[int, Field(strict=True, ge=0)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Cost = Annotated[Finite, Field(ge=0)]


class FieldType(StrEnum):
    program = 'program'
    award_amount = 'award_amount'
    payment_amount = 'payment_amount'
    deadline = 'deadline'
    application_url = 'application_url'
    eligibility = 'eligibility'
    payment_requirement = 'payment_requirement'
    current_availability = 'current_availability'


class Label(StrEnum):
    supported = 'supported'
    contradicted = 'contradicted'
    insufficient_evidence = 'insufficient_evidence'


class TemporalStatus(StrEnum):
    active = 'active'
    expired = 'expired'
    not_yet_active = 'not_yet_active'
    unknown = 'unknown'
    not_applicable = 'not_applicable'


class CheckStatus(StrEnum):
    queued = 'queued'
    extracting = 'extracting'
    retrieving = 'retrieving'
    verifying = 'verifying'
    completed = 'completed'
    failed = 'failed'


class ReasonCode(StrEnum):
    MATCHED = 'MATCHED'
    VALUE_MISMATCH = 'VALUE_MISMATCH'
    EXPLICIT_NEGATION = 'EXPLICIT_NEGATION'
    DEADLINE_PASSED = 'DEADLINE_PASSED'
    NO_SOURCE = 'NO_SOURCE'
    SOURCE_SILENT = 'SOURCE_SILENT'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'
    SCOPE_UNCLEAR = 'SCOPE_UNCLEAR'
    DATE_AMBIGUOUS = 'DATE_AMBIGUOUS'
    OCR_UNCERTAIN = 'OCR_UNCERTAIN'
    INVALID_CITATION = 'INVALID_CITATION'
    LINK_NOT_CONFIRMED = 'LINK_NOT_CONFIRMED'
    OUT_OF_SCOPE = 'OUT_OF_SCOPE'
    PARTIAL_EVIDENCE = 'PARTIAL_EVIDENCE'


class ErrorCode(StrEnum):
    INVALID_INPUT = 'INVALID_INPUT'
    INPUT_TOO_LARGE = 'INPUT_TOO_LARGE'
    UNSUPPORTED_MEDIA = 'UNSUPPORTED_MEDIA'
    RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND'
    RESOURCE_EXPIRED = 'RESOURCE_EXPIRED'
    ASSET_NOT_READY = 'ASSET_NOT_READY'
    OCR_FAILED = 'OCR_FAILED'
    NO_CHECKABLE_CLAIM = 'NO_CHECKABLE_CLAIM'
    TOO_MANY_CLAIMS = 'TOO_MANY_CLAIMS'
    RATE_LIMITED = 'RATE_LIMITED'
    BUDGET_EXCEEDED = 'BUDGET_EXCEEDED'
    PROVIDER_TIMEOUT = 'PROVIDER_TIMEOUT'
    PROVIDER_BAD_OUTPUT = 'PROVIDER_BAD_OUTPUT'
    CORPUS_UNAVAILABLE = 'CORPUS_UNAVAILABLE'
    JOB_INTERRUPTED = 'JOB_INTERRUPTED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'


class RunMode(StrEnum):
    live = 'live'
    fixture = 'fixture'
    replay = 'replay'


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    @field_validator('*', mode='before')
    @classmethod
    def nullable_string(cls, value, info: ValidationInfo):
        args = get_args(cls.model_fields[info.field_name].annotation)
        if isinstance(value, str) and value == '' and str in args and type(None) in args:
            raise ValueError('use null instead of an empty string')
        return value


class PublicModel(ContractModel):
    schema_version: Literal['1.0']


class TextSpan(ContractModel):
    start: Count
    end: Annotated[int, Field(strict=True, gt=0)]

    @model_validator(mode='after')
    def ordered(self):
        if self.end <= self.start:
            raise ValueError('end must exceed start')
        return self


def check_quote(text: str, span: TextSpan, quote: str) -> None:
    """Offsets use Python Unicode code points, never UTF-8 bytes/UTF-16 units."""
    if text != normalize('NFC', text) or quote != normalize('NFC', quote):
        raise ValueError('text and quote must be NFC')
    if span.end > len(text) or text[span.start:span.end] != quote:
        raise ValueError('quote does not match span')


class MoneyValue(ContractModel):
    amount: Count
    currency: Literal['VND']
    basis: str


Precision = Literal['datetime', 'date', 'unknown']


def check_precision(value: str | None, precision: str) -> None:
    if precision == 'unknown':
        if value is not None:
            raise ValueError('unknown precision requires null value')
    elif value is None:
        raise ValueError('known precision requires value')
    elif precision == 'date':
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError('date must use YYYY-MM-DD')
    else:
        iso_timestamp(value)


class DateValue(ContractModel):
    value: str | None
    precision: Precision
    timezone: Literal['Asia/Ho_Chi_Minh']
    raw: str
    ambiguous: StrictBool

    @model_validator(mode='after')
    def precise(self):
        check_precision(self.value, self.precision)
        return self


class NormalizedValue(ContractModel):
    text: str | None
    money: MoneyValue | None
    date: DateValue | None
    url: str | None

    @model_validator(mode='after')
    def single_branch(self):
        if sum(v is not None for v in (self.text, self.money, self.date, self.url)) > 1:
            raise ValueError('at most one normalized branch')
        return self


class Scope(ContractModel):
    program: str | None
    academic_year: str | None
    cohort: str | None
    audience: str | None
    fee_kind: str | None


class ErrorDetail(ContractModel):
    code: ErrorCode
    message: str
    retryable: StrictBool
    details: dict[str, Any]


class ErrorEnvelope(PublicModel):
    request_id: str
    error: ErrorDetail


class Usage(ContractModel):
    provider: str
    model: str
    input_tokens: Count
    output_tokens: Count
    cost_usd: Cost
    cost_vnd_estimate: Cost
    attempts: Count
    cache_hit: StrictBool
    duration_ms: Count


class OCRResult(ContractModel):
    text: str
    mean_confidence: Annotated[Finite, Field(ge=0, le=100)] | None
    low_quality: StrictBool
    warnings: list[str]
    duration_ms: Count


class AssetRecord(PublicModel):
    asset_id: UUID
    status: Literal['queued', 'ocr', 'ready', 'failed']
    ocr: OCRResult | None
    error: ErrorDetail | None
    created_at: Timestamp
    expires_at: Timestamp

    @model_validator(mode='after')
    def consistent(self):
        if self.expires_at <= self.created_at:
            raise ValueError('expiry must follow creation')
        if self.status == 'ready':
            valid = self.ocr is not None and self.error is None
        elif self.status == 'failed':
            valid = self.error is not None
        else:
            valid = self.ocr is None and self.error is None
        if not valid:
            raise ValueError('asset status/ocr/error mismatch')
        return self


class CheckCreate(PublicModel):
    input_mode: Literal['text', 'image']
    confirmed_text: Annotated[str, Field(min_length=20, max_length=6000)]
    asset_id: UUID | None
    asset_token: str | None
    as_of: Timestamp
    consent_to_process: Literal[True]

    @model_validator(mode='before')
    @classmethod
    def explicit_consent(cls, values):
        if isinstance(values, dict) and values.get('consent_to_process') is not True:
            raise ValueError('explicit consent required')
        return values

    @model_validator(mode='after')
    def valid_input(self):
        if self.input_mode == 'image':
            if self.asset_id is None or not self.asset_token:
                raise ValueError('image requires asset and token; readiness checked at runtime')
        elif self.asset_id is not None or self.asset_token is not None:
            raise ValueError('text requires null asset fields')
        if self.as_of > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('as_of exceeds server time +5 minutes')
        return self


class Claim(ContractModel):
    claim_id: str
    field_type: FieldType
    statement: str
    input_span: TextSpan | None
    raw_value: str
    normalized: NormalizedValue
    scope: Scope
    ambiguities: list[str]


class ExtractionResult(ContractModel):
    claims: Annotated[list[Claim], Field(max_length=8)]
    warnings: list[str]
    usage: Usage

    @model_validator(mode='after')
    def unique_claims(self):
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError('duplicate claim ids')
        return self


class SourceFact(ContractModel):
    field_type: FieldType
    normalized: NormalizedValue
    scope: Scope
    quote: str
    span: TextSpan


class SourceVersion(ContractModel):
    source_id: str
    version_id: str
    family_id: str
    canonical_url: str
    parent_url: str | None
    title: str
    publisher: str
    published_at: str | None
    published_precision: Precision
    retrieved_at: Timestamp
    available_at: Timestamp
    available_basis: Literal['published_verified', 'first_seen', 'fixture']
    effective_from: DateValue | None
    effective_to: DateValue | None
    supersedes_version_id: str | None
    content_sha256: str
    text: str
    scope: Scope
    is_fixture: StrictBool
    review_status: Literal['approved', 'quarantined']
    verified_by: str
    facts: list[SourceFact]
    outbound_links: list[str]

    @model_validator(mode='after')
    def valid_source(self):
        check_precision(self.published_at, self.published_precision)
        for fact in self.facts:
            check_quote(self.text, fact.span, fact.quote)
        return self


class SourceChunk(ContractModel):
    chunk_id: str
    version_id: str
    text: str
    source_span: TextSpan
    section: str | None
    page: Annotated[int, Field(strict=True, ge=1)] | None


class RetrievalHit(ContractModel):
    chunk_id: str
    version_id: str
    rank: Annotated[int, Field(strict=True, ge=1)]
    score: Finite
    retriever: Literal['rrf']
    text: str
    source: SourceVersion


class RetrievalBundle(ContractModel):
    claim_id: str
    query: str
    hits: list[RetrievalHit]
    corpus_version: str
    as_of: Timestamp
    reason: Literal['found', 'no_match', 'no_eligible_source']


class EvidenceRef(ContractModel):
    chunk_id: str
    version_id: str
    quote: str
    quote_span: TextSpan
    relation: Literal['supports', 'contradicts', 'context']

    @model_validator(mode='after')
    def exact_quote(self, info: ValidationInfo):
        # The final evidence service supplies actual chunks, never provider text.
        if info.context is not None and 'chunks' in info.context:
            chunk = info.context['chunks'].get(self.chunk_id)
            if chunk is None or chunk.version_id != self.version_id:
                raise ValueError('citation chunk/version absent from context')
            check_quote(chunk.text, self.quote_span, self.quote)
        return self


class VerdictDraft(ContractModel):
    claim_id: str
    label: Label
    reason_codes: list[ReasonCode]
    explanation: str
    evidence: list[EvidenceRef]
    temporal_status: TemporalStatus


class ClaimVerdict(VerdictDraft):
    field_type: FieldType
    statement: str
    normalized: NormalizedValue
    checks_passed: list[str]

    @model_validator(mode='after')
    def cited(self):
        relation = {Label.supported: 'supports', Label.contradicted: 'contradicts'}.get(self.label)
        if relation and not any(e.relation == relation for e in self.evidence):
            raise ValueError('supported/contradicted requires matching evidence')
        return self


class Summary(ContractModel):
    supported: Count
    contradicted: Count
    insufficient_evidence: Count
    message: str


class SourceSummary(ContractModel):
    version_id: str
    title: str
    canonical_url: str
    published_at: str | None
    retrieved_at: Timestamp
    is_fixture: StrictBool


class SourcePublic(SourceSummary, PublicModel):
    text: str
    chunks: list[SourceChunk]

    @model_validator(mode='after')
    def chunk_spans(self):
        for chunk in self.chunks:
            if chunk.version_id != self.version_id:
                raise ValueError('chunk version mismatch')
            check_quote(self.text, chunk.source_span, chunk.text)
        return self


class CheckResult(PublicModel):
    check_id: UUID
    claims: list[ClaimVerdict]
    summary: Summary
    sources: list[SourceSummary]
    as_of: Timestamp
    corpus_version: str
    corpus_updated_at: Timestamp
    warnings: list[str]
    run_mode: RunMode
    next_steps: list[str]
    usage: Usage

    @model_validator(mode='after')
    def consistent(self):
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError('duplicate claim ids')
        for label in Label:
            if getattr(self.summary, label.value) != sum(c.label == label for c in self.claims):
                raise ValueError('summary does not match labels')
        versions = {s.version_id for s in self.sources}
        if len(versions) != len(self.sources):
            raise ValueError('duplicate source versions')
        if any(e.version_id not in versions for c in self.claims for e in c.evidence):
            raise ValueError('citation version absent from sources')
        return self


class CheckRecord(PublicModel):
    check_id: UUID
    status: CheckStatus
    result: CheckResult | None
    error: ErrorDetail | None
    created_at: Timestamp
    updated_at: Timestamp
    expires_at: Timestamp

    @model_validator(mode='after')
    def consistent(self):
        if not self.created_at <= self.updated_at < self.expires_at:
            raise ValueError('invalid record timestamps')
        if self.status == CheckStatus.completed:
            valid = self.result is not None and self.error is None
        elif self.status == CheckStatus.failed:
            valid = self.result is None and self.error is not None
        else:
            valid = self.result is None and self.error is None
        if not valid:
            raise ValueError('status/result/error mismatch')
        if self.result is not None and self.result.check_id != self.check_id:
            raise ValueError('result check_id mismatch')
        return self


class AssetCreated(PublicModel):
    asset: AssetRecord
    access_token: str


class CheckCreated(PublicModel):
    check: CheckRecord
    access_token: str


class HealthResponse(PublicModel):
    status: Literal['ok']
    corpus_version: str
    provider_configured: StrictBool
    run_mode: RunMode


class TemporalCheckReport(ContractModel):
    claim_id: str
    temporal_status: TemporalStatus
    reason_codes: list[ReasonCode]
    checks_passed: list[str]
    needs_more_evidence: StrictBool


class VerificationOutput(ContractModel):
    drafts: list[VerdictDraft]
    usage: Usage


# Explicit registry shared by example validation and OpenAPI export.
CONTRACT_MODELS = (
    TextSpan, MoneyValue, DateValue, NormalizedValue, Scope, ErrorDetail, Usage,
    OCRResult, AssetRecord, CheckCreate, Claim, ExtractionResult, SourceFact,
    SourceVersion, SourceChunk, RetrievalHit, RetrievalBundle, EvidenceRef,
    VerdictDraft, ClaimVerdict, Summary, SourceSummary, SourcePublic, CheckResult,
    CheckRecord, ErrorEnvelope, AssetCreated, CheckCreated, HealthResponse,
    TemporalCheckReport, VerificationOutput,
)
