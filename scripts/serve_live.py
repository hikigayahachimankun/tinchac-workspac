"""Serve local live TinChac using the existing authorized ledger and private secret loader."""
import argparse
from pathlib import Path

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.services.corpus import ROOT
from backend.app.services.corpus_store import private_path
from scripts.preflight import account_mode
from scripts.provider_check import DEFAULT_SECRET, load_key


def live_settings(readiness: Path, secret: Path, store: Path, state: Path) -> Settings:
    settings=Settings(_env_file=None,app_mode='live',database_path=ROOT/'data/private/tinchac-live.sqlite3',
        private_dir=ROOT/'data/private',frontend_dist=ROOT/'frontend/dist',
        source_sync_store=private_path(store),source_sync_state=private_path(state),source_lookup_enabled=True)
    mode=account_mode(readiness,settings.llm_model)
    if mode!='free_tier':
        raise ValueError('fresh_owner_free_tier_readiness_required')
    settings.llm_billing_mode=mode
    settings.gemini_api_key=load_key(secret)
    settings.llm_live_enabled=True
    return settings


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readiness-report',type=Path,required=True)
    parser.add_argument('--secret-file',type=Path,default=DEFAULT_SECRET)
    parser.add_argument('--store',type=Path,default=ROOT/'data/private/live-corpus')
    parser.add_argument('--state',type=Path,default=ROOT/'data/private/source-sync')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args(argv)
    try:
        settings=live_settings(args.readiness_report,args.secret_file,args.store,args.state)
        initialize(settings.database_path)
        import uvicorn
        uvicorn.run(create_app(settings),host='127.0.0.1',port=args.port,workers=1,access_log=False)
    except (OSError,ValueError):
        # Secret/SDK/config exception strings must never be printed.
        print('Local live startup failed; check readiness freshness, private file permissions and corpus status.')
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
