#!/usr/bin/env python3
"""Pack one dictionary's per-key files into a few hundred files of about 150 KB, in key order, plus a manifest:
  <out>/<dict>/m.json  {"n": number of keys, "s": [first key of each pack]}     <out>/<dict>/<i>.json  {key: {...}, ...}
A reader finds a key's pack by the last first-key that is <= the key. index*.json files are copied as they are.
Usage: pack.py <dir of key files> <out dir> <dict name>"""
import sys, os, json, glob, shutil
src, out, name = sys.argv[1], sys.argv[2], sys.argv[3]
d = os.path.join(out, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
items = []
for f in glob.glob(os.path.join(src, '*.json')):
    b = os.path.basename(f)
    if b.startswith('index'): shutil.copy(f, os.path.join(d, b)); continue
    j = json.load(open(f, encoding='utf-8')); k = j.get('r') or j.get('k'); items.append((k, j))
items.sort(key=lambda x: x[0])
packs, cur, size, LIM = [], {}, 0, 150_000
for k, j in items:
    s = len(json.dumps(j, ensure_ascii=False).encode())
    if cur and size + s > LIM: packs.append(cur); cur, size = {}, 0
    cur[k] = j['e']; size += s
if cur: packs.append(cur)
for i, p in enumerate(packs):
    with open(os.path.join(d, f'{i}.json'), 'w', encoding='utf-8') as fh: json.dump(p, fh, ensure_ascii=False, separators=(',', ':'))
json.dump({'n': len(items), 's': [next(iter(p)) for p in packs]}, open(os.path.join(d, 'm.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(name, 'keys', len(items), 'packs', len(packs))
