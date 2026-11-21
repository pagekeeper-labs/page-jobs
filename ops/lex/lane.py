#!/usr/bin/env python3
"""Lane, An Arabic-English Lexicon (1863-93): Perseus TEI XML (CC BY-SA, Perseus Digital Library, Tufts University;
corrected files from github.com/laneslexicon/xml) -> one small JSON file per root:
  out/lane/<root as hex code points>.json  {"r": root, "e": [{"h": headword, "t": simple html}]}
Usage: lane.py <xml dir> <out dir>"""
import sys, os, re, json, glob, html
import xml.etree.ElementTree as ET
BW = {"'": 'ء', '|': 'آ', '>': 'أ', '&': 'ؤ', '<': 'إ', '}': 'ئ', 'A': 'ا', 'b': 'ب', 'p': 'ة', 't': 'ت', 'v': 'ث', 'j': 'ج', 'H': 'ح', 'x': 'خ', 'd': 'د', '*': 'ذ', 'r': 'ر', 'z': 'ز', 's': 'س', '$': 'ش', 'S': 'ص', 'D': 'ض', 'T': 'ط', 'Z': 'ظ', 'E': 'ع', 'g': 'غ', 'f': 'ف', 'q': 'ق', 'k': 'ك', 'l': 'ل', 'm': 'م', 'n': 'ن', 'h': 'ه', 'w': 'و', 'Y': 'ى', 'y': 'ي', 'F': 'ً', 'N': 'ٌ', 'K': 'ٍ', 'a': 'َ', 'u': 'ُ', 'i': 'ِ', '~': 'ّ', 'o': 'ْ', '`': 'ٰ', '{': 'ٱ', '_': 'ـ'}
DI = {'A^': 'أ', 'w^': 'ؤ', 'y^': 'ئ', 'Y^': 'ئ', 'A_': 'ٱ', 'A=': 'آ', 'A|': 'آ'}
def ar(s):
    out, i = '', 0
    while i < len(s):
        d = s[i:i + 2]
        if d in DI: out += DI[d]; i += 2; continue
        c = s[i]; out += BW.get(c, '' if c in '^_=' else c); i += 1
    return out
def text(el):
    """the entry as simple html: <i> for the meanings, <b lang=ar> for Arabic, ― between senses"""
    parts = []
    def walk(e):
        tag = e.tag; lang = e.get('lang')
        if tag in ('foreign', 'orth') and lang == 'ar':
            t = ''.join(e.itertext()).strip()
            if t and t != '*': parts.append('<b lang="ar">' + html.escape(ar(t)) + '</b>')
        elif tag == 'hi' and (e.get('rend') or '').startswith('ital'):
            parts.append('<i>' + html.escape(''.join(e.itertext())) + '</i>')
        elif tag in ('itype',):
            pass
        else:
            if e.text: parts.append(html.escape(e.text))
            for ch in e: walk(ch)
        if e.tail: parts.append(html.escape(e.tail))
    if el.text: parts.append(html.escape(el.text))
    for ch in el: walk(ch)
    t = ''.join(parts)
    t = re.sub(r'\s*―?\s*-b\d-\s*', ' ― ', t)
    t = re.sub(r'\s+', ' ', t).strip(' ,;')
    t = re.sub(r"\s+([,;:.)])", r"\1", t)
    return t
def main(src, out):
    os.makedirs(os.path.join(out, 'lane'), exist_ok=True); roots = {}; n = 0
    for f in sorted(glob.glob(os.path.join(src, '*.xml'))):
        tree = ET.parse(f)
        for d in tree.iter('div2'):
            if d.get('type') != 'root': continue
            r = ar(d.get('n') or '').replace('ـ', '')
            r = re.sub(r'[^\u0621-\u064A]', '', r)
            if not r: continue
            es = roots.setdefault(r, [])
            for e in d.iter('entryFree'):
                o = e.find('form/orth'); h = ar(o.text.strip()) if o is not None and o.text else ''
                es.append({'h': h, 't': text(e)}); n += 1
    big = 0
    for r, es in roots.items():
        s = json.dumps({'r': r, 'e': es}, ensure_ascii=False, separators=(',', ':'))
        big = max(big, len(s.encode()))
        with open(os.path.join(out, 'lane', '-'.join('%04x' % ord(c) for c in r) + '.json'), 'w', encoding='utf-8') as fh: fh.write(s)
    print('lane roots', len(roots), 'entries', n, 'largest', big)
if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
