#!/usr/bin/env python3
"""Brown-Driver-Briggs, Hebrew and English Lexicon (1906), abridged XML of the Open Scriptures Hebrew Bible Project
(github.com/openscriptures/HebrewLexicon, CC BY 4.0; the text itself is public domain). Hebrew and Biblical Aramaic parts ->
  out/bdb/<root hex>.json and out/bdb-arc/<root hex>.json   {"r": root, "e": [{"h": headword, "t": simple html}]}
  out/bdb/index.json, out/bdb-arc/index.json                [[root, headword, first meaning], ...]
Usage: bdb.py <BrownDriverBriggs.xml> <out dir>"""
import sys, os, re, json, html
import xml.etree.ElementTree as ET
NS = '{http://openscriptures.github.com/morphhb/namespace}'
FIN = str.maketrans('ךםןףץ', 'כמנפצ')
cons = lambda w: re.sub('[^א-ת]', '', w).translate(FIN)
def tag(e): return e.tag.replace(NS, '')
def text(el):
    out = []
    def walk(e, top=False):
        t = tag(e)
        if t in ('status', 'page'): 
            if e.tail: out.append(html.escape(e.tail))
            return
        if t == 'w': out.append('<b lang="he">' + html.escape(''.join(e.itertext())) + '</b>')
        elif t == 'def': out.append('<i>' + html.escape(''.join(e.itertext())) + '</i>')
        elif t == 'stem': out.append('<b>' + html.escape(''.join(e.itertext())) + '</b>')
        else:
            if t == 'sense' and e.get('n'): out.append(' <b>' + e.get('n') + '.</b> ')
            elif t == 'sense' and not top: out.append(' ― ')
            if e.text: out.append(html.escape(e.text))
            for c in e: walk(c)
        if e.tail and not top: out.append(html.escape(e.tail))
    walk(el, True)
    return re.sub(r'\s+([,;:.)])', r'\1', re.sub(r'\s+', ' ', ''.join(out))).strip()
def main(src, out):
    root = ET.parse(src).getroot()
    for part_lang, name in (('heb', 'bdb'), ('arc', 'bdb-arc')):
        d = os.path.join(out, name); os.makedirs(d, exist_ok=True); groups = {}; index = []
        for part in root.iter(NS + 'part'):
            if part.get('{http://www.w3.org/XML/1998/namespace}lang') != part_lang: continue
            for sec in part.iter(NS + 'section'):
                ents = [e for e in sec if tag(e) == 'entry']
                if not ents: continue
                w0 = ents[0].find(NS + 'w'); key = cons(''.join(w0.itertext())) if w0 is not None else ''
                if not key: continue
                g = groups.setdefault(key, [])
                for e in ents:
                    w = e.find(NS + 'w'); h = ''.join(w.itertext()) if w is not None else ''
                    t = text(e)
                    if len(t) < 3: continue
                    g.append({'h': h, 't': t})
                    df = e.find(NS + 'def'); index.append([key, h, ''.join(df.itertext()) if df is not None else ''])
        for k, es in groups.items():
            with open(os.path.join(d, '-'.join('%04x' % ord(c) for c in k) + '.json'), 'w', encoding='utf-8') as fh: json.dump({'r': k, 'e': es}, fh, ensure_ascii=False, separators=(',', ':'))
        with open(os.path.join(d, 'index.json'), 'w', encoding='utf-8') as fh: json.dump(index, fh, ensure_ascii=False, separators=(',', ':'))
        print(name, 'roots', len(groups), 'entries', len(index))
if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
