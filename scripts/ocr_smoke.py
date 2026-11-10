"""Synthetic dev fixture, never gold. Generate local Vietnamese OCR samples and CER."""
import json
from pathlib import Path
import textwrap
import unicodedata

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.app.services.ocr import extract_image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/fixtures/ocr'


def distance(a, b):
    row = list(range(len(b)+1))
    for i, char in enumerate(a, 1):
        next_row = [i]
        for j, other in enumerate(b, 1):
            next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(char!=other)))
        row = next_row
    return row[-1]


def main():
    DEST.mkdir(exist_ok=True)
    texts=json.loads((ROOT/'frontend/src/api/fixture-texts.json').read_text())
    reference=texts['original']
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
    image=Image.new('RGB',(1300,240),'white')
    ImageDraw.Draw(image).multiline_text((35,35),'\n'.join(textwrap.wrap(reference,58)),font=font,fill='black',spacing=16)
    image.save(DEST/'vietnamese-clear.png')
    image.filter(ImageFilter.GaussianBlur(10)).save(DEST/'vietnamese-blurred.png')
    Image.new('RGB',(600,240),'white').save(DEST/'blank.png')
    report=[]
    for name in ('vietnamese-clear','vietnamese-blurred'):
        result=extract_image(DEST/(name+'.png'))
        # Normalize NFC and whitespace identically; keep accents, punctuation and case.
        expected=' '.join(unicodedata.normalize('NFC',reference).split())
        actual=' '.join(unicodedata.normalize('NFC',result.text).split())
        edits=distance(actual,expected)
        report.append(dict(sample=name,ocr=result.model_dump(),reference=reference,reference_chars=len(expected),
                           character_edits=edits,cer=edits/len(expected)))
    (DEST/'reference.txt').write_text(reference+'\n')
    (ROOT/'docs/evidence/T06/ocr-smoke.json').write_text(json.dumps(dict(
        family_count=1,sample_count=2,split='synthetic dev only; not benchmark/gold',font='DejaVuSans 36',
        blur_radius=10,normalization='NFC and collapsed whitespace',results=report),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
