"""Deterministic Pydantic/FastAPI OpenAPI export and fixture validation."""
import argparse
import json
from pathlib import Path

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import CONTRACT_MODELS, CheckRecord, ErrorEnvelope, SourceChunk, AssetRecord, CheckCreate

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MODELS = {m.__name__: m for m in CONTRACT_MODELS}
EXAMPLE_MODELS.update(asset_ready=AssetRecord, check_create=CheckCreate, check_result=CheckRecord, error=ErrorEnvelope)


def validate_examples() -> int:
    directory = ROOT / 'contracts/examples'
    chunk = SourceChunk.model_validate_json((directory / 'SourceChunk.json').read_text())
    seen = set()
    for path in sorted(directory.glob('*.json')):
        model = EXAMPLE_MODELS[path.stem]
        model.model_validate_json(path.read_text(), context={'chunks': {chunk.chunk_id: chunk}})
        seen.add(model)
    if seen != set(CONTRACT_MODELS):
        raise ValueError('Missing examples for contract models')
    return len(list(directory.glob('*.json')))


def export_text() -> str:
    app = create_app(Settings(_env_file=None, app_mode='fixture', gemini_api_key=''))
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'contracts/openapi.json')
    args = parser.parse_args()
    count = validate_examples()
    text = export_text()
    if args.check:
        if not args.output.exists() or args.output.read_text() != text:
            raise SystemExit('OpenAPI drift: run python -m scripts.export_contracts')
    else:
        args.output.write_text(text)
    print(f'{count} examples validated; OpenAPI {"matches" if args.check else "exported"}.')


if __name__ == '__main__':
    main()
