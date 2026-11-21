#!/usr/bin/env python3
"""Classical Arabic dictionaries from the OpenITI corpus (mARkdown text; OpenITI licence CC BY-NC-SA 4.0, used here without
any charge or advertising): Ibn Manzur's Lisan al-Arab ("### $ root: ...") and Ibn Faris's Maqayis al-Lugha ("### | (root)").
-> packs of ~150 KB in root order plus a manifest:  <out>/<name>/m.json, <out>/<name>/<i>.json   {root: [{"h": root, "t": html}]}
Root keys: letters only, vowel marks taken off, hamza seats written as alif.  Usage: openiti.py <file> <out dir> <name>"""
import sys, os, re, json, html, shutil, collections
src, outd, name = sys.argv[1], sys.argv[2], sys.argv[3]
HEAD = [re.compile(r'^### \$ ([^:\s]{2,6})\s*:\s*(.*)$'), re.compile(r'^### \|+ \(([^)\s]{2,6})\)\s*(.*)$')]
def key(r):
    r = re.sub('[ً-ْٰـ]', '', r); r = re.sub('[أإآءؤئ]', 'ا', r).replace('ى', 'ي')
    return re.sub('[^ء-ي]', '', r)
def clean(lines):
    out = []
    for ln in lines:
        poem = ln.startswith('# '); ln = re.sub(r'^(~~|# )', '', ln)
        ln = re.sub(r'PageV\d+P\d+|ms\d+|«\d+»|\(\d+\)', '', ln).strip()
        if not ln: continue
        t = html.escape(ln)
        if poem: out.append('<br>' + ('<i>' + t + '</i>' if '...' in ln else t))
        else: out.append(' ' + t)
    return re.sub(r'\s+', ' ', ''.join(out)).strip()
ents = collections.defaultdict(list); cur = None; buf = []
def flush():
    if cur and buf:
        t = clean(buf)
        if len(t) > 5: ents[key(cur)].append({'h': cur, 't': t[:40000]})
for line in open(src, encoding='utf-8'):
    line = line.rstrip('\n')
    if line.startswith('### '):
        flush(); cur, buf = None, []
        for h in HEAD:
            m = h.match(line)
            if m: cur = re.sub('[ً-ْ]', '', m.group(1)); buf = [m.group(2)] if m.group(2).strip() else []; break
        continue
    if cur is not None: buf.append(line)
flush()
d = os.path.join(outd, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
packs, curp, size = [], {}, 0
for k in sorted(ents):
    s = len(json.dumps(ents[k], ensure_ascii=False).encode())
    if curp and size + s > 150_000: packs.append(curp); curp, size = {}, 0
    curp[k] = ents[k]; size += s
if curp: packs.append(curp)
for i, p in enumerate(packs): json.dump(p, open(os.path.join(d, f'{i}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({'n': len(ents), 's': [next(iter(p)) for p in packs]}, open(os.path.join(d, 'm.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(name, 'roots', len(ents), 'packs', len(packs), 'sample', json.dumps(ents.get('كتب', [{}])[0], ensure_ascii=False)[:300])
