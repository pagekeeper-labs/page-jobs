#!/usr/bin/env python3
"""Send one packed dictionary to the site: every file in <dir>, then 'done'. Retries each file; stops if many fail.
Usage: send.py <packed dir> <dict name>   (env API, KEY)"""
import os, sys, json, time, urllib.request, concurrent.futures as cf
API, KEY = os.environ['API'].rstrip('/'), os.environ['KEY']; d, name = sys.argv[1], sys.argv[2]
def call(method, path, body=None, ctype='application/json'):
    r = urllib.request.Request(API + path, data=body, method=method, headers={'x-ops-key': KEY, 'content-type': ctype, 'user-agent': 'page-jobs'})
    with urllib.request.urlopen(r, timeout=60) as res: return res.status
def send(f):
    body = open(os.path.join(d, f), 'rb').read()
    for a in range(4):
        try:
            if call('PUT', f'/api/ops/maps/lex/{name}/{f}', body) == 200: return True
        except Exception as e: err = e
        time.sleep(2 * (a + 1))
    print('failed', f); return False
files = sorted(f for f in os.listdir(d) if f.endswith('.json') and f != 'm.json')
with cf.ThreadPoolExecutor(6) as ex: ok = sum(ex.map(send, files))
print(name, 'sent', ok, 'of', len(files))
if ok != len(files): sys.exit(1)
# the manifest last, so readers never see packs that are not there yet
if not send('m.json'): sys.exit(1)
m = json.load(open(os.path.join(d, 'm.json')))
call('POST', f'/api/ops/maps/lex/{name}/done', json.dumps({'keys': m['n'], 'packs': len(m['s'])}).encode())
print(name, 'done')
