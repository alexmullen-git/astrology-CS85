# Top-50 asteroids on JPL's Sentry impact-risk list (ranked by cumulative impact probability), with their orbits from MPCORB.
# Sentry: https://ssd-api.jpl.nasa.gov/doc/sentry.html   MPCORB: https://www.minorplanetcenter.net/iau/MPCORB.html
import sys, re, json, datetime as dt, requests, pandas as pd
r = requests.get('https://ssd-api.jpl.nasa.gov/sentry.api', timeout=60); r.raise_for_status()
s = pd.DataFrame(r.json()['data'])
for c in ['ip','ps_cum','ts_max','diameter','h']: s[c] = pd.to_numeric(s[c], errors='coerce')
s = s.sort_values('ip', ascending=False).head(50)
cols = [(166,194),(20,25),(26,35),(37,46),(48,57),(59,68),(70,79),(92,103)]
m = pd.read_fwf('data/MPCORB.DAT.gz', colspecs=cols, names=['name','epoch','M','w','om','i','e','a'], skiprows=43, dtype=str, compression='gzip')
look = {}
for x in m.itertuples():
    k = re.sub(r'^\((\d+)\)\s*', r'\1 ', str(x.name).strip()); look.setdefault(k, x)
    mm = re.match(r'^(\d+)\s+(.*)$', k)
    if mm: look.setdefault(mm.group(1), x); look.setdefault(mm.group(2), x)
def epoch_days(sv):
    y = {'I':1800,'J':1900,'K':2000}[sv[0]] + int(sv[1:3]); return (dt.date(y, int(sv[3],36), int(sv[4],36)) - dt.date(2000,1,1)).days
rows = []
for x in s.itertuples():
    o = look[x.des.strip()]
    rows.append([re.sub(r'^\(([^()]*)\)$', r'\1', x.fullname.strip()), round(float(o.a),4), round(float(o.e),4), round(float(o.i),3), round(float(o.om),3), round(float(o.w),3), round(float(o.M),3), epoch_days(o.epoch),
                 float(x.ip), None if pd.isna(x.diameter) else round(float(x.diameter)*1000, 1), float(x.ps_cum), None if pd.isna(x.ts_max) else float(x.ts_max), str(x.range), str(x.last_obs)])
print(len(rows), 'objects; missing diameters:', sum(1 for q in rows if q[9] is None), '; max Torino in list:', max(q[11] for q in rows if q[11] is not None))
json.dump({'retrieved': dt.date.today().isoformat(), 'total': int(len(r.json()['data'])), 'rows': rows}, open(sys.argv[1], 'w'), separators=(',',':'))
