# Kirkwood gaps: histogram of asteroid orbit sizes with Jupiter resonances marked.
# Data: Minor Planet Center MPCORB (https://www.minorplanetcenter.net/iau/MPCORB.html), cached by starters/10_mpc_orbits.py
import numpy as np, pandas as pd, matplotlib.pyplot as plt

A_JUPITER = 5.2026                                     # Jupiter's orbit size in au
# An asteroid in an "n:m" resonance orbits n times while Jupiter orbits m times.
# Kepler's third law (period^2 ~ a^3) turns that period ratio into an orbit size.
resonances = {'4:1': (4, 1), '3:1': (3, 1), '5:2': (5, 2), '7:3': (7, 3), '2:1': (2, 1)}
res_a = {k: A_JUPITER * (m / n) ** (2 / 3) for k, (n, m) in resonances.items()}

df = pd.read_fwf('data/MPCORB.DAT.gz', colspecs=[(92, 103)], names=['a'], skiprows=43,
                 dtype=str, compression='gzip')
a = pd.to_numeric(df['a'], errors='coerce').dropna()
a = a[(a > 1.8) & (a < 3.6)]                          # the main belt region
print(f'{len(a):,} asteroids between 1.8 and 3.6 au')

fig, ax = plt.subplots(figsize=(10, 6))
counts, _, _ = ax.hist(a, bins=np.arange(1.8, 3.6, 0.01), color='0.45')
for name, x in res_a.items():
    if 1.8 < x < 3.6:
        ax.axvline(x, color='tab:red', ls='--', lw=1)
        ax.text(x, counts.max() * 1.02, f'{name}\n{x:.2f}', color='tab:red', ha='center', va='bottom', fontsize=9, bbox=dict(fc='white', ec='none', pad=1))
        print(f'{name} resonance at a = {x:.3f} au')
ax.set_ylim(0, counts.max() * 1.15)
ax.set(xlabel='Semi-major axis a (au)', ylabel='Number of asteroids per 0.01 au',
       title='Kirkwood gaps: where Jupiter\'s gravity has cleared the asteroid belt')
plt.tight_layout(); plt.savefig('plots/kirkwood_gaps.png', dpi=150)
