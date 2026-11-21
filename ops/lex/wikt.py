#!/usr/bin/env python3
"""Words in many languages from Wiktionary (CC BY-SA 4.0), as extracted by Wiktextract (kaikki.org, Tatu Ylonen).
Reads the raw JSONL on stdin and keeps the languages below. For each word: part of speech, a few meanings, the etymology,
the words it comes from or is related to, the dictionary word an inflected form belongs to, and an Arabic root if given.
Writes packs of ~150 KB in key order plus a manifest, like pack.py:  <out>/wikt/m.json, <out>/wikt/<i>.json
Key: '<language code>:<word>' with accents, vowel marks and points taken off, lower case, and Arabic alif/ya/ta marbuta
unified (the same rule as the site's search).  Usage: zcat raw.jsonl.gz | wikt.py <out dir>"""
import sys, os, json, re, unicodedata, shutil, collections
LANGS = {'en', 'fr', 'es', 'la', 'ar', 'he', 'arc', 'phn', 'xpu', 'egy', 'syc', 'akk', 'grc', 'ang', 'enm', 'fro', 'sem-pro', 'afa-pro'}
KEEP_FORMS = {'la', 'fr', 'es', 'ar', 'he', 'en'}
def key(lang, w):
    s = unicodedata.normalize('NFD', w)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = s.replace('ـ', '').replace('ى', 'ي').replace('ة', 'ه').replace('ٱ', 'ا')
    return lang + ':' + s.strip()
LINKS = {'der', 'inh', 'bor', 'lbor', 'cog', 'm', 'l', 'noncog', 'calque', 'slbor', 'der+', 'inh+', 'bor+'}
words = collections.defaultdict(list); n = 0
for line in sys.stdin:
    try: j = json.loads(line)
    except Exception: continue
    lc = j.get('lang_code'); w = j.get('word')
    if lc not in LANGS or not w or len(w) > 60: continue
    senses = j.get('senses') or []
    gl, form, exs = [], '', []
    for s in senses:
        fo = s.get('form_of') or s.get('alt_of')
        if fo and not form: form = (fo[0] or {}).get('word', '')
        g = (s.get('glosses') or [''])[-1]
        if g and not fo and len(gl) < 4:
            gl.append(g[:220]); ex = ''
            for x in s.get('examples') or []:
                t = (x.get('text') or '').strip()
                if t and len(t) <= 220: ex = t + (' — ' + x['english'][:160] if x.get('english') else ''); break
            exs.append(ex)
    if not gl and not form: continue
    if not gl and lc not in KEEP_FORMS: continue
    ety = (j.get('etymology_text') or '')[:600]
    xs, root = [], ''
    for t in j.get('etymology_templates') or []:
        nm, a = t.get('name'), t.get('args') or {}
        if nm == 'ar-root': root = ''.join(v for k, v in sorted(a.items()) if k.isdigit())
        if nm in LINKS:
            lang2, w2 = (a.get('1'), a.get('2')) if nm in ('m', 'l', 'cog', 'noncog') else (a.get('2'), a.get('3'))
            if lang2 and w2 and len(xs) < 8 and [lang2, w2] not in xs: xs.append([lang2, w2[:60]])
    e = {'l': lc, 'w': w, 'p': j.get('pos', '')}
    if gl: e['g'] = gl
    if form: e['f'] = form
    if ety and gl: e['e'] = ety
    if xs and gl: e['x'] = xs
    if root: e['r'] = re.sub(r'[\s\-]', '', root)
    if gl and any(exs): e['ex'] = exs
    ipa = []
    for so in j.get('sounds') or []:
        if so.get('ipa') and len(ipa) < 3:
            tg = [t for t in (so.get('tags') or []) if t in ('UK', 'US', 'Received-Pronunciation', 'General-American', 'France', 'Spain', 'Latin-America', 'Classical', 'Ecclesiastical', 'Modern-Standard-Arabic', 'Classical-Arabic', 'Israel', 'Tiberian')]
            ipa.append([so['ipa'][:40], (tg[0] if tg else '').replace('Received-Pronunciation', 'UK').replace('General-American', 'US')])
    if ipa and gl: e['ipa'] = ipa
    rel = []
    for f in ('related', 'derived', 'synonyms'):
        for r in j.get(f) or []:
            w2 = r.get('word')
            if w2 and len(rel) < 8 and w2 not in rel and len(w2) <= 40: rel.append(w2)
    if rel and gl: e['rel'] = rel
    hd = (j.get('head_templates') or [{}])[0].get('expansion', '')
    if hd and gl and hd != w: e['hd'] = hd[:100]
    tr = ''
    for fm in j.get('forms') or []:
        if 'romanization' in (fm.get('tags') or []): tr = fm.get('form', '')[:40]; break
    if tr: e['tr'] = tr
    k = key(lc, w)
    if len(words[k]) < 6: words[k].append(e); n += 1
print('words', len(words), 'entries', n, file=sys.stderr)
for probe in ('en:islam', 'la:scripserunt', 'ar:اسلام', 'egy:htp', 'phn:𐤊𐤕𐤁'):
    print('probe', probe, json.dumps(words.get(probe), ensure_ascii=False)[:400], file=sys.stderr)
out = os.path.join(sys.argv[1], 'wikt'); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
packs, cur, size, LIM = [], {}, 0, 150_000
for k in sorted(words):
    s = len(json.dumps(words[k], ensure_ascii=False).encode()) + len(k) + 6
    if cur and size + s > LIM: packs.append(cur); cur, size = {}, 0
    cur[k] = words[k]; size += s
if cur: packs.append(cur)
for i, p in enumerate(packs):
    with open(os.path.join(out, f'{i}.json'), 'w', encoding='utf-8') as fh: json.dump(p, fh, ensure_ascii=False, separators=(',', ':'))
json.dump({'n': len(words), 's': [next(iter(p)) for p in packs]}, open(os.path.join(out, 'm.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wikt packs', len(packs), file=sys.stderr)
