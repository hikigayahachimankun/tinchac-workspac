"""Reproducible OCR-only dev pilot from public input text; no verdict gold or human correction."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import textwrap
import unicodedata

from PIL import Image, ImageDraw, ImageFont
import pytesseract

from backend.app.services.ocr import extract_image
from eval.harness import read_jsonl
from eval.schema import EvalCase
from scripts.ocr_smoke import distance

FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
VARIANTS = ('clear','tilt_2deg','small_18px','jpeg_quality_35')
FIELDS = re.compile(r'https?://\S+|\d{1,2}/\d{1,2}/\d{4}|\d{1,3}(?:\.\d{3})+\s*đồng')


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC',text).split())


def render(text, variant, *, font=FONT):
    size = 18 if variant == 'small_18px' else 32
    lines = textwrap.wrap(text,width=70 if size == 18 else 58)
    image = Image.new('RGB',(1200,max(200,70+len(lines)*(size+15))),'white')
    ImageDraw.Draw(image).multiline_text((25,25),'\n'.join(lines),font=ImageFont.truetype(str(font),size),fill='black',spacing=12)
    if variant == 'tilt_2deg':
        image = image.rotate(2,expand=True,fillcolor='white',resample=Image.Resampling.BICUBIC)
    elif variant == 'jpeg_quality_35':
        buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=35)
        buffer.seek(0);image=Image.open(buffer).copy()
    elif variant not in ('clear','small_18px'):
        raise ValueError('Unknown OCR variant')
    return image


def run(cases, output: Path):
    # One source-derived public dev input per family; keep family/split identity.
    selected={}
    for case in sorted(cases,key=lambda c:c.case_id):
        if case.split == 'dev' and case.origin == 'source_derived':
            selected.setdefault(case.family_id,case)
    if not selected:
        raise ValueError('No source-derived dev cases')
    output.mkdir(mode=0o700)
    results=[]
    for family,case in sorted(selected.items()):
        reference=normalized(case.input_text)
        for variant in VARIANTS:
            path=output/f'{case.case_id}-{variant}.png'
            render(case.input_text,variant).save(path)
            ocr=extract_image(path)
            actual=normalized(ocr.text)
            fields=FIELDS.findall(reference)
            results.append(dict(case_id=case.case_id,family_id=family,split='dev',variant=variant,
                image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
                reference_chars=len(reference),character_edits=distance(actual,reference),
                cer=distance(actual,reference)/len(reference),
                literal_field_matches=sum(f in actual for f in fields),literal_field_total=len(fields),
                ocr_status=ocr.status if hasattr(ocr,'status') else 'returned',
                duration_ms=ocr.duration_ms,warnings=ocr.warnings))
    report=dict(status='OCR_only_dev_pilot_NOT_benchmark',images=len(results),families=len(selected),
        split='dev_only',seed=42,variants=list(VARIANTS),font=str(FONT),font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),
        tesseract_version=str(pytesseract.get_tesseract_version()),languages='vie+eng',
        normalization='NFC and collapsed whitespace; accents/case/punctuation retained',
        aggregate_cer=sum(r['character_edits'] for r in results)/sum(r['reference_chars'] for r in results),
        human_correction=None,human_correction_seconds=None,test_images=0,results=results,
        limitation='Rendered public dev inputs are reference text, not human verdict gold. Repeated variants are not independent families. Literal substring field check is OCR recall only, not extraction precision or pipeline accuracy. Human correction and heldout OCR are unmeasured.')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',default='data/dev/cases.jsonl')
    p.add_argument('--output',type=Path,required=True,help='New local directory')
    args=p.parse_args()
    report=run(read_jsonl(args.cases,EvalCase),args.output)
    print(json.dumps({k:report[k] for k in ('status','images','families','aggregate_cer','test_images')}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
