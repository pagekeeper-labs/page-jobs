#!/usr/bin/env python3
"""Lewis & Short, A Latin Dictionary (1879), Perseus TEI XML (CC BY-SA, Perseus Digital Library, Tufts University,
github.com/PerseusDL/lexica). -> out/ls/<key>.json {"k": key, "e": [{"h": headword, "t": simple html}]} (homographs together)
and out/ls/index-<letter>.json [[key, headword, first meaning], ...] for searching.
Usage: ls.py <lat.ls.perseus-eng1.xml> <out dir>"""
import sys, os, re, json, html, unicodedata, collections
import xml.etree.ElementTree as ET
def plain(s): return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
def text(el):
    out = []
    def walk(e, top=False):
        t = e.tag
        if t in ('cb', 'pb'): pass
        elif t == 'orth': out.append('<b lang="la">' + html.escape(''.join(e.itertext())) + '</b>')
        elif t == 'hi' and (e.get('rend') or '').startswith('ital'): out.append('<i>' + html.escape(''.join(e.itertext())) + '</i>')
        elif t == 'quote': out.append('<q lang="la">' + html.escape(''.join(e.itertext())) + '</q>')
        elif t == 'foreign' and e.get('lang') == 'greek': out.append('<span class="gk">' + html.escape(''.join(e.itertext())) + '</span>')
        elif t == 'bibl': out.append('<small>' + html.escape(''.join(e.itertext())) + '</small>')
        elif t == 'etym': out.append('[<span class="et">' + html.escape(''.join(e.itertext())) + '</span>]')
        else:
            if t == 'sense' and e.get('n'): out.append(' <b>' + html.escape(e.get('n')) + '.</b> ')
            if e.text: out.append(html.escape(e.text))
            for c in e: walk(c)
        if e.tail and not top: out.append(html.escape(e.tail))
    walk(el, True)
    return re.sub(r'\s+([,;:.)])', r'\1', re.sub(r'\s+', ' ', ''.join(out))).strip()
def main(src, out):
    d = os.path.join(out, 'ls'); os.makedirs(d, exist_ok=True)
    groups = collections.OrderedDict(); n = 0
    for _ev, e in ET.iterparse(src):
        if e.tag != 'entryFree': continue
        k = re.sub('[^a-z]', '', plain(e.get('key') or ''))
        if not k: e.clear(); continue
        o = e.find('orth'); h = ''.join(o.itertext()) if o is not None else k
        first = e.find('.//sense//hi')
        g = groups.setdefault(k, {'e': [], 'g': ''})
        g['e'].append({'h': h, 't': text(e)}); n += 1
        if not g['g'] and first is not None: g['g'] = ''.join(first.itertext()).strip(' ,;:.')[:60]
        e.clear()
    idx = collections.defaultdict(list); big = 0
    for k, g in groups.items():
        s = json.dumps({'k': k, 'e': g['e']}, ensure_ascii=False, separators=(',', ':')); big = max(big, len(s.encode()))
        with open(os.path.join(d, k + '.json'), 'w', encoding='utf-8') as fh: fh.write(s)
        idx[k[0]].append([k, g['e'][0]['h'], g['g']])
    for c, rows in idx.items():
        with open(os.path.join(d, 'index-' + c + '.json'), 'w', encoding='utf-8') as fh: json.dump(rows, fh, ensure_ascii=False, separators=(',', ':'))
    print('ls keys', len(groups), 'entries', n, 'largest', big)
if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
