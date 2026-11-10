"""Private immutable snapshots and atomic active pointer. Existing offline ingest owns builds."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from ..models import SourceVersion
from .corpus import ROOT, canonical_hash, load_corpus, normalize_text
from .runtime import LiveRuntime
from .source_authority import AuthorityRegistry
from .source_sync import PII, exclusive, write_json

VERSION = re.compile(r'corpus-[0-9a-f]{64}')
GATES = ('authority', 'completeness', 'publisher_category', 'personal_data', 'provenance',
         'family', 'facts', 'temporal', 'content_use')


def private_path(path: Path):
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT) and not resolved.is_relative_to(ROOT/'data/private'):
        raise ValueError('sync_requires_private_directory')
    return resolved


def active_directory(store: Path) -> Path | None:
    path=store/'active.json'
    if not path.exists(): return None
    pointer=json.loads(path.read_text())
    version=pointer['corpus_version']
    if not VERSION.fullmatch(version): raise ValueError('invalid_active_pointer')
    directory=store/'snapshots'/version
    if directory.resolve()!=directory.absolute(): raise ValueError('snapshot_symlink')
    return directory


def sync_directory(directory):
    descriptor=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def replace_pointer(store, value):
    pointer=store/'active.json'
    previous=pointer.read_bytes() if pointer.exists() else None
    descriptor,path=tempfile.mkstemp(prefix='.active-',dir=store)
    replaced=False
    try:
        with os.fdopen(descriptor,'w') as output:
            output.write(json.dumps(value,sort_keys=True)+'\n')
            output.flush(); os.fsync(output.fileno())
        os.replace(path,pointer)
        replaced=True
        sync_directory(store)
    except OSError:
        # A post-replace durability failure is also a failed publication. Restore
        # the old logical pointer before returning failure; retain both snapshots.
        if replaced:
            if previous is None:
                pointer.unlink(missing_ok=True)
            else:
                restore_fd,restore_path=tempfile.mkstemp(prefix='.restore-',dir=store)
                try:
                    with os.fdopen(restore_fd,'wb') as handle:
                        handle.write(previous); handle.flush(); os.fsync(handle.fileno())
                    os.replace(restore_path,pointer)
                finally:
                    Path(restore_path).unlink(missing_ok=True)
        raise
    finally:
        Path(path).unlink(missing_ok=True)


def validate_extension(old, new):
    incoming={s.version_id:s for s in new}
    if any(incoming.get(s.version_id)!=s for s in old):
        raise ValueError('cannot_drop_or_rewrite_history')
    families={}
    hashes={}
    for source in new:
        prior=families.setdefault(source.source_id,source.family_id)
        if source.family_id!=prior:
            raise ValueError('cannot_split_source_family')
        # Alias/repost with identical text adds no independent evidence. Resolve its
        # canonical source in review instead of indexing it as a second publisher.
        if source.review_status=='approved':
            canonical=hashes.setdefault(source.content_sha256,source.source_id)
            if canonical!=source.source_id:
                raise ValueError('duplicate_canonical_content')



def activate(store: Path, version: str):
    """Explicit rollback uses the same validation/atomic switch as forward publication."""
    store=private_path(store)
    if not VERSION.fullmatch(version): raise ValueError('invalid_corpus_version')
    with exclusive(store,'publish.lock'):
        directory=store/'snapshots'/version
        runtime=LiveRuntime(directory)
        old=active_directory(store)
        previous=old.name if old else None
        replace_pointer(store,{'corpus_version':runtime.retriever.corpus_version,'previous':previous,
                              'activated_at':datetime.now(timezone.utc).isoformat()})
    return version


def publish(store: Path, snapshot: Path, register: Path, *, root=ROOT):
    """Build via existing ingest in staging. Called only after review validation or bootstrap.

    A sync failure before the final replace leaves active.json untouched. An orphan
    complete snapshot is safe and can be reused; snapshots are never removed here.
    """
    from scripts.ingest_sources import ingest
    store=private_path(store)
    with exclusive(store,'publish.lock'):
        old_dir=active_directory(store)
        incoming=[SourceVersion.model_validate(s) for s in json.loads(snapshot.read_text())]
        validate_extension([],incoming)
        if old_dir:
            old,_,_=load_corpus(old_dir)
            validate_extension(old,incoming)
            if old==incoming and json.loads((old_dir/'register.json').read_text())==json.loads(register.read_text()):
                return old_dir.name
        snapshots=store/'snapshots'; snapshots.mkdir(mode=0o700,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.staging-',dir=store) as temporary:
            stage=Path(temporary)
            manifest=ingest(snapshot,register,stage,root=root)
            # Prepare the actual runtime before activation, including its retriever.
            LiveRuntime(stage)
            shutil.copyfile(register,stage/'register.json')
            hashes={name:hashlib.sha256((stage/name).read_bytes()).hexdigest()
                    for name in ('sources.json','chunks.json','manifest.json','register.json')}
            write_json(stage/'publication.json',{'corpus_version':manifest['corpus_version'],'files':hashes})
            for file in stage.iterdir():
                file.chmod(0o600)
                with file.open('rb') as handle: os.fsync(handle.fileno())
            sync_directory(stage)
            target=snapshots/manifest['corpus_version']
            if target.exists():
                for name in hashes:
                    if hashlib.sha256((target/name).read_bytes()).hexdigest()!=hashes[name]:
                        raise ValueError('snapshot_identity_collision')
                LiveRuntime(target)
            else:
                stage.rename(target)
                sync_directory(snapshots)
            replace_pointer(store,dict(corpus_version=target.name,previous=old_dir.name if old_dir else None,
                activated_at=datetime.now(timezone.utc).isoformat()))
            return target.name


def validate_reviews(sources, register, packets, state: Path, registry: AuthorityRegistry, *, root=ROOT):
    from scripts.ingest_sources import checked_file, extract_html, extract_pdf
    by_id={r['version_id']:r for r in register['sources']}
    reviews={r['version_id']:r for r in packets}
    if len(reviews)!=len(packets) or set(reviews)!={s.version_id for s in sources}:
        raise ValueError('review_versions_mismatch')
    for source in sources:
        packet=reviews[source.version_id]
        path=(state/packet['candidate_path']).resolve()
        if not path.is_relative_to((state/'candidates').resolve()): raise ValueError('candidate_path')
        candidate=json.loads((path/'receipt.json').read_text())
        notice=candidate['canonical_url']
        authority=registry.check(notice,'notice',candidate['authority_id'])
        if (source.title!=candidate['title'] or source.review_status!='approved' or source.is_fixture or source.publisher!=authority['publisher']
                or candidate['category'] not in authority['categories']):
            raise ValueError('review_authority')
        if packet.get('candidate_receipt_sha256')!=hashlib.sha256((path/'receipt.json').read_bytes()).hexdigest():
            raise ValueError('review_candidate_hash')
        if PII.search(source.text): raise ValueError('personal_data_not_retained')
        if not source.facts: raise ValueError('reviewed_facts_required')
        reviewer=packet.get('reviewer_identity','').strip()
        if not reviewer or packet.get('reviewer_kind') not in ('agent','human') or source.verified_by!=reviewer:
            raise ValueError('reviewer_identity')
        for gate in GATES:
            row=packet.get('gates',{}).get(gate,{})
            if row.get('passed') is not True or not str(row.get('evidence','')).strip():
                raise ValueError('review_gate_'+gate)
        if packet.get('text_sha256')!=source.content_sha256:
            raise ValueError('review_text_hash')
        entry=by_id[source.version_id]
        if entry['notice_url']!=notice or entry['ingest']['reviewed_by']!=reviewer:
            raise ValueError('review_provenance')
        first_seen=datetime.fromisoformat(candidate['first_seen'])
        if (source.available_basis!='first_seen' or source.available_at!=source.retrieved_at
                or source.retrieved_at<first_seen or source.retrieved_at>datetime.now(timezone.utc)):
            raise ValueError('review_backdated')
        raw=checked_file(root,entry['ingest']['raw'])
        method=entry['ingest']['method']
        if source.canonical_url==notice:
            if (method!='html' or source.content_sha256!=candidate['text_sha256']
                    or extract_html(raw,entry['content_selector'])!=source.text
                    or hashlib.sha256(raw.read_bytes()).hexdigest()!=candidate['sanitized_html_sha256']):
                raise ValueError('review_extraction')
        else:
            links={a['url'] for a in candidate['attachments']}
            if source.parent_url!=notice or source.canonical_url not in links:
                raise ValueError('attachment_parent_provenance')
            if method=='pdf_text':
                text,pages=extract_pdf(raw)
                if text!=source.text or pages!=entry['ingest']['pages']: raise ValueError('review_pdf')
            elif method=='manual_pdf':
                text=normalize_text(checked_file(root,entry['ingest']['manual_text']).read_text()).rstrip('\n')
                if text!=source.text: raise ValueError('review_manual_extract')
                import pymupdf
                with pymupdf.open(raw) as document:
                    if len(document)!=len(entry['ingest']['pages']): raise ValueError('review_pdf_pages')
            else:
                raise ValueError('attachment_requires_reviewed_pdf')
        risky=bool(candidate['review_reasons'] or source.parent_url or source.supersedes_version_id
                   or any(f.field_type in ('payment_amount','payment_requirement') for f in source.facts))
        if risky:
            human=packet.get('human_review',{})
            if (not human.get('identity','').strip() or not human.get('evidence','').strip()
                    or human.get('kind')!='human' or human.get('confirmed') is not True):
                raise ValueError('human_review_required')
        if not candidate['extraction_complete']:
            attachment_review=packet.get('attachment_review',{})
            if (attachment_review.get('complete') is not True or not attachment_review.get('evidence')
                    or not attachment_review.get('reviewed_files')):
                raise ValueError('attachment_review_required')
            for file in attachment_review['reviewed_files']:
                checked_file(root,file)
        relation=packet.get('family_review',{})
        if relation.get('family_id')!=source.family_id or not relation.get('evidence'):
            raise ValueError('family_review_required')
        if source.supersedes_version_id:
            # Existing validate_register/build_corpus also check exact quote, scope and ordering.
            if relation.get('supersedes_version_id')!=source.supersedes_version_id:
                raise ValueError('supersession_review_required')
    return True


def publish_reviewed(store: Path, snapshot: Path, register: Path, reviews: Path,
                     state: Path, registry: AuthorityRegistry, *, root=ROOT):
    sources=[SourceVersion.model_validate(s) for s in json.loads(snapshot.read_text())]
    config=json.loads(register.read_text())
    packets=json.loads(reviews.read_text())
    # Supersession validation needs old versions too. Promotion input must contain the
    # complete union, but only new records need fresh candidate review packets.
    old_dir=active_directory(store)
    old,_,_=load_corpus(old_dir) if old_dir else ([],[],{})
    old_ids={s.version_id for s in old}
    packet_map={packet['version_id']:packet for packet in packets}
    if len(packet_map)!=len(packets): raise ValueError('review_versions_mismatch')
    if old_dir:
        old_entries={row['version_id']:row for row in json.loads((old_dir/'register.json').read_text())['sources']}
        # Replaying the exact same promotion packet is a no-op, not a new review.
        for entry in config['sources']:
            vid=entry['version_id']
            if vid in old_ids and vid in packet_map:
                recorded=old_entries[vid]['ingest'].get('source_sync_review',{})
                if recorded.get('packet')!=packet_map[vid]: raise ValueError('cannot_rewrite_review_history')
                entry['ingest']['source_sync_review']=recorded
    validate_extension(old,sources)
    new=[s for s in sources if s.version_id not in old_ids]
    new_config={'sources':[r for r in config['sources'] if r['version_id'] not in old_ids]}
    # Validate complete register first to resolve old supersession references.
    from scripts.ingest_sources import validate_register
    validate_register(sources,config)
    # Complete relation checks above; gate only the new records below.
    validate_reviews(new,new_config,[p for p in packets if p['version_id'] not in old_ids],state,registry,root=root)
    for source in new:
        previous=[s for s in old if s.source_id==source.source_id]
        if previous and any(f.field_type in ('award_amount','payment_amount','deadline','payment_requirement')
                            for f in source.facts):
            human=packet_map[source.version_id].get('human_review',{})
            if (human.get('kind')!='human' or human.get('confirmed') is not True
                    or not human.get('identity') or not human.get('evidence')):
                raise ValueError('critical_update_human_review_required')
    # Never rewrite review/provenance for a retained version.
    if old_dir:
        old_entries={r['version_id']:r for r in json.loads((old_dir/'register.json').read_text())['sources']}
        if any(r!=old_entries[r['version_id']] for r in config['sources'] if r['version_id'] in old_ids):
            raise ValueError('cannot_rewrite_review_history')
    # Persist the full review evidence inside manifest-bound ingest provenance, and
    # serialize the exact validated values to prevent input-file changes between gates/build.
    for entry in config['sources']:
        if entry['version_id'] in packet_map and entry['version_id'] not in old_ids:
            entry['ingest']['source_sync_review']={
                'packet':packet_map[entry['version_id']],
                'registry_sha256':canonical_hash(registry.authorities)}
    private_store=private_path(store)
    private_store.mkdir(parents=True,mode=0o700,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.reviewed-',dir=private_store) as temporary:
        frozen_snapshot=Path(temporary)/'sources.json'
        frozen_register=Path(temporary)/'register.json'
        write_json(frozen_snapshot,[s.model_dump(mode='json') for s in sources])
        write_json(frozen_register,config)
        return publish(store,frozen_snapshot,frozen_register,root=root)
