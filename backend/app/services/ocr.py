"""Local Tesseract only. No image data crosses a provider boundary."""
from pathlib import Path
from time import monotonic
import unicodedata

import pytesseract
from pytesseract import Output

from ..models import OCRResult


def extract_image(path: Path, *, languages: str = 'vie+eng', timeout: int = 20) -> OCRResult:
    started = monotonic()
    data = pytesseract.image_to_data(str(path), lang=languages, timeout=timeout, output_type=Output.DICT)
    lines: list[str] = []
    words: list[str] = []
    confidences: list[float] = []
    previous = None
    for i, word in enumerate(data['text']):
        if not word.strip():
            continue
        line = tuple(data[key][i] for key in ('page_num', 'block_num', 'par_num', 'line_num'))
        if previous is not None and line != previous:
            lines.append(' '.join(words))
            words = []
        words.append(word)
        previous = line
        confidence = float(data['conf'][i])
        if 0 <= confidence <= 100:
            confidences.append(confidence)
    if words:
        lines.append(' '.join(words))
    text = unicodedata.normalize('NFC', '\n'.join(lines))
    mean = sum(confidences) / len(confidences) if confidences else None
    low = not text or mean is None or mean < 70
    warnings = ['Không đọc được chữ; hãy nhập tay.'] if not text else (
        ['OCR có độ tin cậy thấp; kiểm tra kỹ số tiền và ngày.'] if low else [])
    return OCRResult(text=text, mean_confidence=mean, low_quality=low, warnings=warnings,
                     duration_ms=int((monotonic() - started) * 1000))
