# Pull a seeded random sample of asteroid orbits (with real orbital elements) out of MPCORB for the viewer.
import sys, json, datetime as dt, numpy as np, pandas as pd
cols = [(166,194),(20,25),(26,35),(37,46),(48,57),(59,68),(70,79),(92,103),(161,165)]
names = ['name','epoch','M','w','om','i','e','a','flags']
df = pd.read_fwf('data/MPCORB.DAT.gz', colspecs=cols, names=names, skiprows=43, dtype=str, compression='gzip')
for c in ['M','w','om','i','e','a']: df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna(subset=['M','w','om','i','e','a','epoch','name'])
df = df[(df.e < 0.99) & (df.a > 0.3) & (df.a < 6.0)]

def epoch_days(s):                                   # packed epoch like 'K26AB' -> days since 2000-01-01
    cent = {'I':1800,'J':1900,'K':2000}[s[0]]
    y = cent + int(s[1:3]); m = int(s[3], 36); d = int(s[4], 36)
    return (dt.date(y, m, d) - dt.date(2000, 1, 1)).days
df['ep'] = df.epoch.map(epoch_days)
df['neo'] = df['flags'].fillna('0').apply(int, base=16) & 0x0800 > 0
df['new'] = df.name.str.contains(r'(?:^|\) )2026 ', na=False)
rng = np.random.default_rng(42)
groups = [(0, df[~df.neo & ~df.new], 4000), (1, df[df.neo], 1200), (2, df[df.new & ~df.neo], 1500)]
out, counts = [], {}
for g, sub, n in groups:
    counts[g] = int(len(sub))
    s = sub.sample(min(n, len(sub)), random_state=int(rng.integers(1e9)))
    for r in s.itertuples():
        out.append([r.name.strip(), round(r.a,4), round(r.e,4), round(r.i,3), round(r.om,3), round(r.w,3), round(r.M,3), int(r.ep), g])
print({g: (counts[g], sum(1 for o in out if o[8]==g)) for g in counts}, len(out), 'objects')
json.dump({'rows': out, 'totals': counts}, open(sys.argv[1], 'w'), separators=(',',':'))
