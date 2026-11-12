"""
Project 07: build the Sentry Orbit Explorer (an interactive 3D web page).

What this script does, step by step:
  1. Downloads JPL's Sentry list: every known asteroid with a possible future Earth impact.
  2. Downloads JPL's list of objects REMOVED from Sentry (their risk was ruled out).
  3. Downloads the orbits of every near-Earth object from JPL's Small-Body Database.
  4. Matches the lists by designation (an asteroid's catalog name, like "2024 YR4").
  5. For orbits given at an old reference date, asks JPL Horizons for an up-to-date version.
  6. Pastes the matched data into the HTML template, so the page works offline.

Downloads are cached in data/ so they only happen once. Use --refresh to download again.

Run:     python3 project07/build_orbit_explorer.py
Output:  project07/sentry_orbit_explorer.html

Data sources (cite these):
  - NASA/JPL CNEOS Sentry API           https://ssd-api.jpl.nasa.gov/doc/sentry.html
  - NASA/JPL Small-Body Database Query  https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html
  - NASA/JPL Horizons                   https://ssd-api.jpl.nasa.gov/doc/horizons.html
"""
import datetime
import json
import pathlib
import sys

import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA_DIR = HERE.parent / 'data'
TEMPLATE = HERE / 'orbit_explorer_template.html'
OUTPUT = HERE / 'sentry_orbit_explorer.html'
PLACEHOLDER = '/*__DATA__*/null'

SENTRY_API = 'https://ssd-api.jpl.nasa.gov/sentry.api'
SBDB_QUERY_API = 'https://ssd-api.jpl.nasa.gov/sbdb_query.api'

# Orbital elements we need from the Small-Body Database:
#   a = size of the orbit (au), e = how stretched it is, i = tilt (degrees),
#   om, w = which way the orbit is turned (degrees), ma = where the asteroid is on
#   its orbit at the date "epoch" (a Julian Day number), moid = closest distance
#   between this orbit and Earth's orbit (au).
ORBIT_FIELDS = ['pdes', 'full_name', 'a', 'e', 'i', 'om', 'w', 'ma', 'epoch', 'moid']


def cached_json(filename, url, params, refresh):
    """Download JSON once and keep a copy in data/. Returns (data, download_date)."""
    path = DATA_DIR / filename
    if refresh or not path.exists():
        print(f'Downloading {url} ...')
        response = requests.get(url, params=params, timeout=180)
        response.raise_for_status()  # stop with a clear error if the download failed
        DATA_DIR.mkdir(exist_ok=True)
        path.write_text(response.text)
    downloaded = datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()
    return json.loads(path.read_text()), downloaded


HORIZONS_API = 'https://ssd.jpl.nasa.gov/api/horizons.api'


def horizons_elements(des, epoch):
    """Ask JPL Horizons for an asteroid's orbit as it will be on date `epoch` (a Julian Day).

    Why: the Small-Body Database gives each orbit at its own reference date ("epoch").
    For some objects that date is many years ago (Bennu's is 2011). Our web page moves
    asteroids along simple ellipses, which slowly drift from reality because they ignore
    the planets' pull. So we get every orbit at the SAME recent date; Horizons computes
    that with full gravity, and our page only has to cover the short time since then.
    Results are cached in data/horizons_elements/, so each object is only asked for once.
    """
    folder = DATA_DIR / 'horizons_elements'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{des.replace(" ", "_").replace("/", "-")}_{epoch}.txt'
    if not path.exists():
        command = f"'{des};'" if des.isdigit() else f"'DES={des};'"   # numbered vs. provisional names
        response = requests.get(HORIZONS_API, timeout=60, params={
            'format': 'json', 'COMMAND': command, 'EPHEM_TYPE': 'ELEMENTS', 'CENTER': "'500@10'",
            'TLIST': f"'{epoch}'", 'REF_PLANE': 'ECLIPTIC', 'OUT_UNITS': 'AU-D', 'CSV_FORMAT': 'YES',
            'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES'})
        response.raise_for_status()
        result = response.json().get('result', '')
        if '$$SOE' not in result:
            return None                                  # Horizons could not identify the object
        path.write_text(result.split('$$SOE')[1].split('$$EOE')[0].strip())
    # CSV columns: JDTDB, date, EC, QR, IN, OM, W, Tp, N, MA, TA, A, AD, PR
    cols = [c.strip() for c in path.read_text().split(',')]
    return {'epoch': cols[0], 'e': cols[2], 'i': cols[4], 'om': cols[5], 'w': cols[6], 'ma': cols[9], 'a': cols[11]}


def number(text, digits=8):
    """The APIs send numbers as text. Convert to float, rounded to keep the page small."""
    if text in (None, ''):
        return None
    return float(f'{float(text):.{digits}g}')


def pretty_name(full_name):
    """'   433 Eros (A898 PA)' -> '433 Eros (A898 PA)'; '(2010 RF12)' -> '2010 RF12'."""
    name = full_name.strip()
    if name.startswith('(') and name.endswith(')'):
        name = name[1:-1]
    return name


def main():
    refresh = '--refresh' in sys.argv

    sentry, sentry_date = cached_json('sentry_list.json', SENTRY_API, {}, refresh)
    removed, _ = cached_json('sentry_removed.json', SENTRY_API, {'removed': 1}, refresh)
    orbits, _ = cached_json('sbdb_neo_orbits.json', SBDB_QUERY_API,
                            {'fields': ','.join(ORBIT_FIELDS), 'sb-group': 'neo', 'full-prec': 'true'},
                            refresh)

    # Look up each orbit by its designation, e.g. orbit_by_des['2024 YR4'].
    columns = orbits['fields']
    orbit_by_des = {}
    for row in orbits['data']:
        record = dict(zip(columns, row))
        orbit_by_des[record['pdes']] = record

    # Most orbits share one reference date. Move the others to that date with Horizons.
    wanted = {d['des'] for d in sentry['data']} | {d['des'] for d in removed['data']}
    epochs = [o['epoch'] for des, o in orbit_by_des.items() if des in wanted]
    common_epoch = max(set(epochs), key=epochs.count)
    stale = [des for des in sorted(wanted & orbit_by_des.keys())
             if abs(float(orbit_by_des[des]['epoch']) - float(common_epoch)) > 365]
    print(f'{len(stale)} orbits have a reference date more than a year from {common_epoch}; '
          'updating them with JPL Horizons (cached after the first run)...')
    failed = []
    for n, des in enumerate(stale, 1):
        new = horizons_elements(des, common_epoch)
        if new is None:
            failed.append(des)
        else:
            orbit_by_des[des].update(new)
        if n % 100 == 0:
            print(f'  {n}/{len(stale)}')
    if failed:
        print(f'  Horizons could not update {len(failed)} objects; they keep their original orbit:',
              ', '.join(failed[:20]), '...' if len(failed) > 20 else '')

    def orbit_values(o):
        return [pretty_name(o['full_name']),
                number(o['a']), number(o['e']), number(o['i']), number(o['om']),
                number(o['w']), number(o['ma']), number(o['epoch'], 10), number(o['moid'], 4)]

    # Objects currently on the Sentry list.
    listed, missing = [], []
    for obj in sentry['data']:
        o = orbit_by_des.get(obj['des'])
        if o is None:
            missing.append(obj['des'])
            continue
        listed.append([obj['des'], *orbit_values(o),
                       number(obj['ip'], 4), number(obj['ps_cum'], 3), number(obj['diameter'], 3),
                       obj['range'], int(obj['n_imp']), obj['last_obs']])

    # Objects that have been removed from the Sentry list.
    gone = []
    for obj in removed['data']:
        o = orbit_by_des.get(obj['des'])
        if o is not None:
            gone.append([obj['des'], *orbit_values(o), obj['removed'][:10]])

    print(f'Sentry list: {len(listed)} of {len(sentry["data"])} objects matched to an orbit')
    if missing:
        print('  No orbit found for:', ', '.join(missing))
    print(f'Removed list: {len(gone)} of {len(removed["data"])} objects matched to a near-Earth orbit')

    payload = {
        'downloaded': sentry_date,
        'listed_fields': ['des', 'name', 'a', 'e', 'i', 'om', 'w', 'ma', 'epoch', 'moid',
                          'ip', 'ps_cum', 'diameter_km', 'range', 'n_imp', 'last_obs'],
        'removed_fields': ['des', 'name', 'a', 'e', 'i', 'om', 'w', 'ma', 'epoch', 'moid', 'removed'],
        'listed': listed,
        'removed': gone,
        'removed_total': len(removed['data']),
    }

    template = TEMPLATE.read_text()
    assert template.count(PLACEHOLDER) == 1, 'template must contain the data placeholder exactly once'
    OUTPUT.write_text(template.replace(PLACEHOLDER, json.dumps(payload, separators=(',', ':'))))
    print(f'Wrote {OUTPUT.relative_to(HERE.parent)} ({OUTPUT.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
