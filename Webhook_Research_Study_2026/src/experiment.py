"""Reproducible SQLite pilot; NOT a PostgreSQL performance benchmark."""
import argparse,csv,json,random,sqlite3,statistics,time,platform
from pathlib import Path

def connect():
 c=sqlite3.connect(':memory:')
 c.execute('CREATE TABLE effects (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL)')
 c.execute('CREATE TABLE receipts (event_id TEXT PRIMARY KEY, processed INTEGER NOT NULL DEFAULT 0)')
 return c

def handle(conn,event_id,mode,transient_failures):
 """Return (success, attempts); simulate failures before side effects."""
 attempts=0
 limit=3 if mode=='idempotent_retry' else 1
 while attempts<limit:
  attempts+=1
  if transient_failures.get(event_id,0)>0:
   transient_failures[event_id]-=1
   if attempts<limit: continue
   return False,attempts
  with conn:
   if mode=='baseline':
    conn.execute('INSERT INTO effects(event_id) VALUES (?)',(event_id,))
   else:
    cur=conn.execute('INSERT OR IGNORE INTO receipts(event_id,processed) VALUES (?,1)',(event_id,))
    if cur.rowcount:
     conn.execute('INSERT INTO effects(event_id) VALUES (?)',(event_id,))
  return True,attempts
 return False,attempts

def run(mode,unique=200,duplicate_fraction=.25,failure_fraction=.10,seed=42):
 rng=random.Random(seed)
 ids=[f'event-{i:05d}' for i in range(unique)]
 extra=[rng.choice(ids) for _ in range(round(unique*duplicate_fraction))]
 requests=ids+extra;rng.shuffle(requests)
 failures={i:1 for i in rng.sample(ids,round(unique*failure_fraction))}
 conn=connect();durations=[];success=0;attempts=0
 for event_id in requests:
  t=time.perf_counter_ns()
  ok,n=handle(conn,event_id,mode,failures)
  durations.append((time.perf_counter_ns()-t)/1e6)
  success+=int(ok);attempts+=n
 rows=conn.execute('SELECT event_id,COUNT(*) FROM effects GROUP BY event_id').fetchall()
 distinct=len(rows);effects=sum(n for _,n in rows)
 duplicates=sum(max(0,n-1) for _,n in rows)
 return {'mode':mode,'seed':seed,'unique_events':unique,'requests':len(requests),
         'successful_requests':success,'failed_requests':len(requests)-success,
         'unique_effects':distinct,'total_effects':effects,'duplicate_effects':duplicates,
         'total_attempts':attempts,'mean_latency_ms':round(statistics.mean(durations),5),
         'p95_latency_ms':round(sorted(durations)[max(0,int(.95*len(durations))-1)],5),
         'backend':'SQLite in-memory','failure_model':'one injected pre-effect transient failure per selected event'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--unique',type=int,default=200)
 ap.add_argument('--repeats',type=int,default=5);ap.add_argument('--seed',type=int,default=42)
 ap.add_argument('--out',default='results');args=ap.parse_args()
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 rows=[run(mode,args.unique,seed=args.seed+i) for i in range(args.repeats)
       for mode in ('baseline','idempotent','idempotent_retry')]
 with (out/'raw_results.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 summary=[]
 for mode in ('baseline','idempotent','idempotent_retry'):
  sub=[r for r in rows if r['mode']==mode]
  summary.append({'mode':mode,**{k:round(statistics.mean(r[k] for r in sub),5)
   for k in ('successful_requests','failed_requests','unique_effects','duplicate_effects','mean_latency_ms','p95_latency_ms')}})
 with (out/'summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 (out/'environment.json').write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'unique':args.unique,'repeats':args.repeats,'seed':args.seed,'database':'SQLite in-memory'},indent=2))
 for s in summary:print(s)
if __name__=='__main__':main()
