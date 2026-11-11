"""Local scheduler process identity and lifecycle. No root or external supervisor."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .corpus import ROOT
from .corpus_store import private_path


def process_identity(pid):
    # Linux /proc start tick plus boot ID prevents an old receipt killing a reused PID.
    try:
        stat=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        if stat[0]=='Z': return None
        return (Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+stat[19])
    except (OSError,IndexError):
        return None


def scheduler_status(state):
    state=private_path(state)
    try: receipt=json.loads((state/'scheduler.json').read_text())
    except (OSError,ValueError): receipt={}
    locked=False
    if (state/'scheduler.lock').exists():
        with (state/'scheduler.lock').open('a') as handle:
            try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: locked=True
    pid=receipt.get('pid')
    alive=(type(pid) is int and pid>1 and process_identity(pid) is not None
        and process_identity(pid)==receipt.get('process_identity') and locked)
    return dict(process_alive=alive,lock_held=locked,receipt=receipt,
        heartbeat_age_seconds=round(max(0,time.time()-receipt['heartbeat_unix']),2)
            if receipt.get('heartbeat_unix') else None)


def start_scheduler(state, store, config, registry):
    state=private_path(state);state.mkdir(parents=True,mode=0o700,exist_ok=True)
    status=scheduler_status(state)
    if status['process_alive'] or status['lock_held']:
        raise ValueError('scheduler_already_running')
    log=state/'scheduler.log'
    descriptor=os.open(log,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
    with os.fdopen(descriptor,'ab') as output:
        child=subprocess.Popen([sys.executable,'-m','scripts.sync_sources','daemon','--mode','live','--enable',
            '--state',str(state),'--store',str(private_path(store)),'--config',str(config.resolve()),
            '--registry',str(registry.resolve())],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=output,stderr=output,start_new_session=True)
    for _ in range(100):
        status=scheduler_status(state)
        if status['process_alive'] and status['receipt'].get('pid')==child.pid:
            return status
        if child.poll() is not None: raise ValueError('scheduler_start_failed')
        time.sleep(.05)
    # Start did not become observable; do not leave an untracked child behind.
    child.terminate();child.wait(timeout=15)
    raise ValueError('scheduler_start_timeout')


def stop_scheduler(state):
    status=scheduler_status(state)
    if not status['process_alive']:
        if status['lock_held']: raise ValueError('scheduler_identity_unavailable')
        return status
    pid=status['receipt']['pid']
    os.kill(pid,signal.SIGTERM)
    for _ in range(300):
        status=scheduler_status(state)
        if not status['process_alive'] and not status['lock_held']: return status
        time.sleep(.05)
    raise ValueError('scheduler_stop_timeout')
