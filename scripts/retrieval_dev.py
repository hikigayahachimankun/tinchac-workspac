"""Compare fixed FTS-only/hybrid on ten public T02 seed probes, with actual top-k."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time

from backend.app.models import Claim
from backend.app.services.corpus import ROOT, canonical_hash, load_corpus
from backend.app.services.retrieve import Retriever


def compare(corpus: Path, probes: Path) -> dict:
    sources, chunks, manifest = load_corpus(corpus)
    rows = json.loads(probes.read_text())['cases']
    by_id = {s.version_id:s for s in sources}
    result = {'corpus_version':manifest['corpus_version'], 'probe_hash':canonical_hash(rows),
              'config':manifest['retrieval'], 'results':[], 'summary':{}}
    for method in ('fts5_only','fts5_tfidf_rrf'):
        retriever = Retriever(sources,chunks,manifest,method=method)
        top1 = recall = 0
        durations = []
        for row in rows:
            claim = Claim.model_validate(row['claim'])
            expected = row['expected']
            source = by_id[expected['version_id']]
            start,end = expected['span']['start'],expected['span']['end']
            if source.text[start:end] != expected['quote'] or source.family_id != row['family_id']:
                raise ValueError('Probe quote/span/family differs from source')
            relevant = {c.chunk_id for c in chunks if c.version_id == source.version_id
                        and c.source_span.start <= start and c.source_span.end >= end}
            if not relevant:
                raise ValueError('Expected reviewed quote is not contained in a chunk')
            started = time.perf_counter()
            bundle = retriever.retrieve_claim(claim,manifest['corpus_version'],datetime.fromisoformat(row['as_of'].replace('Z','+00:00')))
            elapsed = (time.perf_counter()-started)*1000
            durations.append(elapsed)
            ids = [h.chunk_id for h in bundle.hits]
            rank = next((i for i,c in enumerate(ids,1) if c in relevant),None)
            recall += rank is not None
            top1 += rank == 1
            result['results'].append({'method':method,'case_id':row['case_id'],'query':bundle.query,
                'expected':expected | {'chunk_ids':sorted(relevant)},'top_k':ids,'expected_rank':rank,
                'duration_ms':round(elapsed,3),'scores':[h.score for h in bundle.hits]})
        result['summary'][method] = {'cases':len(rows),'recall_at_5':recall/len(rows),
            'top1':top1/len(rows),'mean_ms':round(sum(durations)/len(durations),3)}
    result['selected'] = 'fts5_tfidf_rrf'
    result['rationale'] = ('Keep §3.9 default: FTS10 + char_wb(3,5)10, RRF60, top5, positive cosine only. '
        'Seed-only pilot, 10 probes from 5 approved families, no thresholds tuned or general quality claim. '
        'The amount of seed data cannot establish a hybrid advantage; freeze needs T09 family split and D03 resolution.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,default=ROOT/'data/corpus')
    parser.add_argument('--probes',type=Path,default=ROOT/'data/dev/retrieval_seed.json')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evidence/T07/retrieval-dev.json')
    args = parser.parse_args()
    result = compare(args.corpus,args.probes)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'corpus_version':result['corpus_version'],'summary':result['summary'],'selected':result['selected']},ensure_ascii=False))


if __name__ == '__main__':
    main()
