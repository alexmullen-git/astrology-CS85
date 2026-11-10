# pip install requests pandas matplotlib
import io, os, requests, pandas as pd, matplotlib.pyplot as plt

os.makedirs('data', exist_ok=True)
os.makedirs('plots', exist_ok=True)
CSV = 'data/exoplanet_planets.csv'

# NASA Exoplanet Archive TAP: one row per confirmed planet (Planetary Systems Composite table)
if os.path.exists(CSV):                                # cached, so we only download once
    df = pd.read_csv(CSV)
else:
    q = ("select pl_name, pl_rade, pl_orbper, discoverymethod, disc_year from pscomppars "
         "where pl_rade is not null and pl_orbper is not null")
    r = requests.get('https://exoplanetarchive.ipac.caltech.edu/TAP/sync',
                     params={'query': q, 'format': 'csv'}, timeout=120)
    if r.status_code != 200:                           # e.g. 503 when the archive is down for maintenance
        raise SystemExit(f'Download failed: HTTP {r.status_code} from the NASA Exoplanet Archive. '
                         f'Start of reply: {r.text[:200]!r}')
    df = pd.read_csv(io.StringIO(r.text))
    df.to_csv(CSV, index=False)
print(len(df), 'planets with radius and period')

fig, ax = plt.subplots(figsize=(8, 6))
for method, g in df.groupby('discoverymethod'):
    if len(g) >= 10:
        ax.scatter(g.pl_orbper, g.pl_rade, s=4, label=f'{method} ({len(g)})')
ax.axhspan(1.5, 2.0, color='gray', alpha=0.2, label='radius valley (~1.5-2 Earth radii)')
ax.set(xscale='log', yscale='log', xlabel='Orbital period (days)', ylabel='Planet radius (Earth radii)',
       title='Known exoplanets (data: NASA Exoplanet Archive)')
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig('plots/exoplanet_population.png', dpi=150)
print('saved plots/exoplanet_population.png')
