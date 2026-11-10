from types import SimpleNamespace
import json
from PIL import Image
from eval.harness import read_jsonl
from eval.schema import EvalCase
from scripts.ocr_eval import normalized, render, run


def test_render_variants_are_deterministic_and_keep_vietnamese_reference():
    text='Học bổng có giá trị 5.000.000 đồng mỗi suất.'
    assert normalized('Học  bổng\n5.000.000 đồng')=='Học bổng 5.000.000 đồng'
    for variant in ('clear','tilt_2deg','small_18px','jpeg_quality_35'):
        assert render(text,variant).tobytes()==render(text,variant).tobytes()


def test_ocr_pilot_preserves_dev_families_and_never_claims_human_correction(tmp_path,monkeypatch):
    cases=read_jsonl('data/dev/cases.jsonl',EvalCase)
    references={c.case_id:normalized(c.input_text) for c in cases}
    def extract(path):
        text=next(v for k,v in references.items() if path.name.startswith(k+'-'))
        return SimpleNamespace(text=text,duration_ms=1,warnings=[])
    monkeypatch.setattr('scripts.ocr_eval.extract_image',extract)
    report=run(cases,tmp_path/'images')
    assert report['images']==20 and report['families']==5
    assert report['aggregate_cer']==0
    assert report['test_images']==0
    assert report['human_correction'] is None and report['human_correction_seconds'] is None
    assert {r['family_id'] for r in report['results']}=={c.family_id for c in cases}
