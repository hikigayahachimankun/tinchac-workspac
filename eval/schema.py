"""Evaluation schema 1.0; the solo-pilot gold extension is local to eval."""
from typing import Literal
from pydantic import Field, StrictBool, model_validator
from backend.app.models import ContractModel, FieldType, Label, ReasonCode, TemporalStatus, Timestamp, TextSpan


class EvalCase(ContractModel):
    case_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    split: Literal['dev', 'test']
    origin: Literal['source_derived', 'synthetic_modified', 'user_contributed']
    domain: Literal['scholarship', 'payment']
    input_text: str = Field(min_length=1)
    target_claim_id: str = Field(min_length=1)
    target_statement: str = Field(min_length=1)
    field_type: FieldType
    as_of: Timestamp
    modification_type: str | None
    input_image_path: str | None

    @model_validator(mode='after')
    def origin_metadata(self):
        if self.origin == 'synthetic_modified' and not (self.modification_type or '').strip():
            raise ValueError('Synthetic case needs modification_type')
        if self.origin != 'synthetic_modified' and self.modification_type is not None:
            raise ValueError('Only synthetic_modified carries modification_type')
        if not self.input_text.strip() or not self.target_statement.strip():
            raise ValueError('Empty claim')
        return self


class QuoteSpan(ContractModel):
    chunk_id: str
    quote: str = Field(min_length=1)
    span: TextSpan


class GoldRecord(ContractModel):
    case_id: str
    label: Label
    reason_codes: list[ReasonCode] = Field(min_length=1)
    acceptable_evidence_sets: list[list[str]]
    reference_quotes: list[str]
    temporal_status: TemporalStatus
    rationale: str = Field(min_length=1)
    annotator_1: str = Field(min_length=1)
    annotator_2: str | None
    agreement_before_adjudication: StrictBool | None
    adjudication_note: str | None
    # Eval-only audit extension: exact offsets relative to NFC chunk text.
    quote_spans: list[QuoteSpan]

    @model_validator(mode='after')
    def evidence_and_annotators(self):
        if not self.rationale.strip() or not self.annotator_1.strip():
            raise ValueError('Human rationale and annotator required')
        if self.annotator_2 is None:
            if self.agreement_before_adjudication is not None:
                raise ValueError('Single annotator has no inter-annotator agreement')
        elif not self.annotator_2.strip() or self.annotator_2 == self.annotator_1 or self.agreement_before_adjudication is None:
            raise ValueError('Independent distinct second annotator and agreement required')
        if self.label != Label.insufficient_evidence:
            if not self.acceptable_evidence_sets or not self.reference_quotes or not self.quote_spans:
                raise ValueError('S/C requires sufficient evidence and quotes')
        if any(not s or len(s) != len(set(s)) for s in self.acceptable_evidence_sets):
            raise ValueError('Empty or duplicate evidence set')
        if self.reference_quotes != [q.quote for q in self.quote_spans]:
            raise ValueError('reference_quotes must match quote_spans in order')
        return self
