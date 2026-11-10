# Discoveries per half-month, 2024-2026, from asteroid designations in MPCORB.
# Data: Minor Planet Center MPCORB (https://www.minorplanetcenter.net/iau/MPCORB.html), cached by starters/10_mpc_orbits.py
# A provisional designation like "2026 KB12" encodes the date of the first reported observation:
#   year = 2026; first letter = half-month (A = Jan 1-15, B = Jan 16-31, C = Feb 1-15, ... Y = Dec 16-31, no letter I).
import re, pandas as pd, matplotlib.pyplot as plt

HALF = 'ABCDEFGHJKLMNOPQRSTUVWXY'                       # 24 letters, one per half-month
names = pd.read_fwf('data/MPCORB.DAT.gz', colspecs=[(166, 194)], names=['name'], skiprows=43,
                    dtype=str, compression='gzip')['name'].dropna()
# Works for "2026 KB12" and for numbered objects like "(826853) 2025 AQ10"; skips survey codes like "2025 T-3"
pat = re.compile(r'(\d{4}) ([A-HJ-Y])[A-HJ-Z]\d*$')
rows = []
for s in names:
    m = pat.search(s)
    if m and 2024 <= int(m.group(1)) <= 2026:
        i = HALF.index(m.group(2))
        rows.append(pd.Timestamp(int(m.group(1)), i // 2 + 1, 1 if i % 2 == 0 else 16))
counts = pd.Series(rows).value_counts().sort_index()
print(f'{len(rows):,} objects designated 2024-2026'); print(counts.groupby(counts.index.year).sum())

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.bar(counts.index, counts.values, width=12, color='tab:blue')
ax.set(ylabel='New designations per half-month', xlabel='Date of first observation (from designation)',
       title='Asteroid discoveries per half-month, 2024-2026 (data: Minor Planet Center)')
plt.tight_layout(); plt.savefig('plots/discoveries_per_half_month.png', dpi=150)
