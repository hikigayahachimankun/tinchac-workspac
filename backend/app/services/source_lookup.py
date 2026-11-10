"""Durable, coalesced product discovery queue. Stores fixed registry IDs only."""
from contextlib import closing, contextmanager
import sqlite3
import time
from pathlib import Path

from .evidence import eligible_hits
from .normalization import scope_compatible
from .source_authority import AuthorityRegistry


def missing_authorities(claims, bundles):
    ids=set()
    for claim,bundle in zip(claims,bundles):
        matching=any(scope_compatible(claim.scope, h.source.scope) or
            any(scope_compatible(claim.scope, f.scope) for f in h.source.facts)
            for h in eligible_hits(bundle))
        if not matching:
            ids.add('dut_finance' if claim.scope.fee_kind or claim.field_type in
                    ('payment_amount','payment_requirement') else 'dut_ctsv')
    return sorted(ids)


class LookupQueue:
    def __init__(self, directory: Path, *, clock=time.time, cooldown=900, capacity=2):
        from .corpus_store import private_path
        self.directory=private_path(directory)
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.clock,self.cooldown,self.capacity=clock,max(60,cooldown),min(2,capacity)
        self.allowed=set(AuthorityRegistry().authorities)
        with self.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS lookup(
                authority TEXT PRIMARY KEY, state TEXT NOT NULL, next_allowed REAL NOT NULL,
                lease_until REAL NOT NULL, requested_at REAL NOT NULL)''')

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.directory/'lookup.sqlite3',timeout=1)) as db,db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA busy_timeout=1000')
            yield db

    def enqueue(self, authority_ids):
        if not set(authority_ids)<=self.allowed: raise ValueError('unknown_authority')
        now=self.clock(); accepted=False
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            occupied=db.execute("SELECT COUNT(*) FROM lookup WHERE state='pending' OR lease_until>?",(now,)).fetchone()[0]
            for aid in sorted(set(authority_ids)):
                row=db.execute('SELECT * FROM lookup WHERE authority=?',(aid,)).fetchone()
                if row and (row['state']=='pending' or row['lease_until']>now or row['next_allowed']>now):
                    continue
                if occupied>=self.capacity: break
                db.execute('INSERT OR REPLACE INTO lookup VALUES(?,?,?,?,?)',
                    (aid,'pending',now+self.cooldown,0,now))
                occupied+=1; accepted=True
        return accepted

    def take(self):
        now=self.clock()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT * FROM lookup WHERE state='pending' OR (state='running' AND lease_until<=?) "
                           'ORDER BY requested_at,authority LIMIT 1',(now,)).fetchone()
            if row is None: return None
            db.execute("UPDATE lookup SET state='running',lease_until=? WHERE authority=?",(now+300,row['authority']))
            return row['authority']

    def finish(self, authority):
        with self.db() as db:
            db.execute("UPDATE lookup SET state='done',lease_until=0,next_allowed=? WHERE authority=?",
                       (self.clock()+self.cooldown,authority))
