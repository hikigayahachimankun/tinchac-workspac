"""T11 eval-local implementation of §4.4; does not extend API components."""
from typing import Literal
from pydantic import Field, StrictBool, model_validator
from backend.app.models import ContractModel, ErrorCode, Usage, VerdictDraft

System = Literal['A', 'B', 'C', 'C_NO_TIME']


class EvalRunRow(ContractModel):
    run_id: str
    case_id: str
    system: System
    model: str
    model_version: str | None
    prompt_hash: str
    corpus_version: str
    config_hash: str
    raw_prediction: VerdictDraft | None
    prediction: VerdictDraft | None
    guard_changes: list[str]
    technical_error: ErrorCode | None
    retrieved_chunk_ids: list[str]
    usage: Usage
    stage_ms: dict[str, float] = Field(default_factory=dict)
    cache_mode: Literal['fresh', 'replay']

    @model_validator(mode='after')
    def outcome(self):
        if (self.prediction is None) != (self.technical_error is not None):
            raise ValueError('Exactly one prediction or technical error required')
        if self.system in ('A', 'B') and self.raw_prediction != self.prediction:
            raise ValueError('A/B prediction must remain unguarded')
        return self


class EvidenceScore(ContractModel):
    run_id: str
    case_id: str
    citation_valid: StrictBool
    evidence_sufficient: StrictBool
    nei_reason_adequate: StrictBool
    reviewer_ids: list[str] = Field(min_length=1)
    comment: str

    @model_validator(mode='after')
    def reviewers(self):
        if any(not r.strip() for r in self.reviewer_ids):
            raise ValueError('Nonempty reviewer IDs required')
        return self
