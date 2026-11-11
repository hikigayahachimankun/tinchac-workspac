"""Operate local DUT discovery and reviewed snapshot publication; never invoke a model."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import time

from backend.app.services.corpus import ROOT
from backend.app.services.corpus_store import activate, active_directory, private_path, publish, publish_reviewed
from backend.app.services.source_authority import AuthorityRegistry
from backend.app.services.source_fetch import SafeFetcher
from backend.app.services.source_lookup import LookupQueue
from backend.app.services.source_sync import exclusive, sync, write_json
from backend.app.services.source_sync import safe_reason
from backend.app.services.errors import ServiceError


def run_once(state, registry, config, *, dry_run=False, authority_ids=None):
    f=SafeFetcher(registry,max_requests=config['max_requests'],max_seconds=config['max_seconds'])
    try:
        receipt=sync(registry,state,f,dry_run=dry_run,max_pages=config['max_pages'],
                    max_notices=config['max_notices'],authority_ids=authority_ids)
    finally:
        f.close()
    if not dry_run and config.get('review_policy_path'):
        from backend.app.services.source_review import review_candidates
        try:
            policy_path=private_path(Path(config['review_policy_path']))
            policy=json.loads(policy_path.read_text()) if policy_path.exists() else {}
            receipt['review']=review_candidates(state,Path(config.get('store',ROOT/'data/private/live-corpus')),registry,policy)
        except (OSError,ValueError,ServiceError) as exc:
            receipt['review']={'status':'failed','reason':safe_reason(exc)}
        write_json(state/'runs'/(receipt['run_id']+'.json'),receipt)
    return receipt


def daemon(state, registry, config, *, dry_run=False):
    queue=LookupQueue(state)
    interval=config['interval_seconds']; poll=config['poll_seconds']
    if not 60<=interval<=7*86400 or not 1<=poll<=60: raise ValueError('schedule_interval')
    with exclusive(state,'scheduler.lock'):
        schedule_file=state/'schedule.json'
        # Restore the previous successful attempt cadence; restarting is not a rate-limit bypass.
        next_run=json.loads(schedule_file.read_text()).get('next_run',0) if schedule_file.exists() else 0
        from backend.app.services.source_scheduler import process_identity
        previous=json.loads((state/'scheduler.json').read_text()) if (state/'scheduler.json').exists() else {}
        heartbeat=dict(status='running',pid=os.getpid(),process_identity=process_identity(os.getpid()),
            started_at=datetime.now(timezone.utc).isoformat(),restart_count=previous.get('restart_count',-1)+1,
            previous_started_at=previous.get('started_at'),interval_seconds=interval,dry_run=dry_run,mode='live',
            cycle_count=previous.get('cycle_count',0),heartbeat_unix=time.time())
        heartbeat.update({key:value for key,value in previous.items() if key.startswith('last_')})
        write_json(state/'scheduler.json',heartbeat)
        try:
            while True:
                due=time.time()>=next_run
                aid=None if due else queue.take()
                if due or aid:
                    # Record before network so a crash does not immediately rerun scheduled discovery.
                    if due:
                        next_run=time.time()+interval
                        write_json(schedule_file,{'next_run':next_run})
                    finished_attempt=False
                    try:
                        receipt=run_once(state,registry,config,dry_run=dry_run,authority_ids=[aid] if aid else None)
                        print(json.dumps({k:receipt[k] for k in ('run_id','status','request_count')},sort_keys=True),flush=True)
                        heartbeat.update(last_run_id=receipt['run_id'],last_run_status=receipt['status'],
                            last_request_count=receipt['request_count'],last_authority_ids=[aid] if aid else sorted(registry.authorities))
                        heartbeat['last_review_status']=receipt.get('review',{}).get('status','checked' if 'review' in receipt else 'not_configured')
                        finished_attempt=True
                    except (OSError,ValueError):
                        print(json.dumps({'status':'failed','reason':'sync_failed'}),flush=True)
                        heartbeat.update(last_run_status='failed')
                        finished_attempt=True
                    finally:
                        # Interrupted network work is recoverable after its lease;
                        # do not mark it done merely because the process is stopping.
                        if aid and finished_attempt: queue.finish(aid)
                        heartbeat['cycle_count']+=1
                heartbeat.update(heartbeat_unix=time.time(),next_run=next_run)
                write_json(state/'scheduler.json',heartbeat)
                time.sleep(poll)
        finally:
            heartbeat.update(status='stopped',heartbeat_unix=time.time(),stopped_at=datetime.now(timezone.utc).isoformat())
            write_json(state/'scheduler.json',heartbeat)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['collect','daemon','start','stop','review','bootstrap','publish','rollback','status'],nargs='?',default='collect')
    parser.add_argument('--state',type=Path,default=ROOT/'data/private/source-sync')
    parser.add_argument('--store',type=Path,default=ROOT/'data/private/live-corpus')
    parser.add_argument('--config',type=Path,default=ROOT/'config/source_sync.json')
    parser.add_argument('--registry',type=Path,default=ROOT/'config/source_authorities.json')
    parser.add_argument('--mode',choices=['fixture','replay','live'],default='fixture')
    parser.add_argument('--enable',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--snapshot',type=Path)
    parser.add_argument('--register',type=Path)
    parser.add_argument('--reviews',type=Path)
    parser.add_argument('--version')
    args=parser.parse_args(argv)
    state,store=private_path(args.state),private_path(args.store)
    if args.action=='status':
        from backend.app.services.source_scheduler import scheduler_status
        directory=active_directory(store)
        print(json.dumps({'active':directory.name if directory else None,
            'scheduler':scheduler_status(state)}))
        return 0
    if args.action=='stop':
        from backend.app.services.source_scheduler import stop_scheduler
        print(json.dumps(stop_scheduler(state)))
        return 0
    if args.action=='bootstrap':
        if active_directory(store): raise ValueError('already_bootstrapped')
        version=publish(store,ROOT/'data/corpus/sources.json',ROOT/'config/sources.yaml')
        print(json.dumps({'corpus_version':version,'network_requests':0}))
        return 0
    if args.action=='rollback':
        if not args.version: parser.error('--version is required')
        print(json.dumps({'corpus_version':activate(store,args.version)}))
        return 0
    if args.action=='publish':
        if not all((args.snapshot,args.register,args.reviews)): parser.error('--snapshot --register --reviews required')
        if args.dry_run: parser.error('publish has no dry-run; use offline validation and a private staging store')
        version=publish_reviewed(store,args.snapshot,args.register,args.reviews,state,AuthorityRegistry(args.registry))
        print(json.dumps({'corpus_version':version,'network_requests':0}))
        return 0
    config=json.loads(args.config.read_text())
    config['store']=str(store)
    if args.action=='review':
        from backend.app.services.source_review import review_candidates
        policy_path=private_path(Path(config['review_policy_path']))
        policy=json.loads(policy_path.read_text()) if policy_path.exists() else {}
        print(json.dumps(review_candidates(state,store,AuthorityRegistry(args.registry),policy)))
        return 0
    if args.mode!='live' or not (args.enable or config['enabled']):
        parser.error('network discovery requires --mode live and enabled config or --enable; fixture/replay never fetch')
    registry=AuthorityRegistry(args.registry)
    if args.action=='start':
        if args.dry_run: parser.error('use foreground daemon for dry-run; start operates live')
        from backend.app.services.source_scheduler import start_scheduler
        print(json.dumps(start_scheduler(state,store,args.config,args.registry)))
    elif args.action=='daemon':
        def stop(signum,frame): raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,stop)
        try: daemon(state,registry,config,dry_run=args.dry_run)
        except KeyboardInterrupt: pass
    else:
        receipt=run_once(state,registry,config,dry_run=args.dry_run)
        print(json.dumps(receipt,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
