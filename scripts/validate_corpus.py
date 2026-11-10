"""Validate schema 1.0, exact hashes/spans, manifest and approved provenance offline."""
import argparse
import json
from pathlib import Path

from backend.app.services.corpus import ROOT, load_corpus
from scripts.ingest_sources import validate_register


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=ROOT / 'data/corpus')
    parser.add_argument('--register', type=Path, default=ROOT / 'config/sources.yaml')
    args = parser.parse_args()
    sources, chunks, manifest = load_corpus(args.corpus)
    if validate_register(sources, json.loads(args.register.read_text())) != manifest['provenance']:
        raise ValueError('Register provenance differs from manifest')
    print(f"{manifest['corpus_version']}: {len(sources)} sources, {len(chunks)} exact chunks; valid")


if __name__ == '__main__':
    main()
