// AI-sharpened copies of maps (board 429), asked for on the site by members. For each: fetch the original, run sharpen.py
// (optional stain and fold clean-up, then Real-ESRGAN 2x or 4x), send the progress as it goes, then send the result back as a new
// copy of the map in the same post; the map tiles job then cuts it. Needs API and MAP_OPS_KEY.
import fs from 'node:fs'; import path from 'node:path'; import { spawn } from 'node:child_process';
const API = process.env.API, KEY = process.env.MAP_OPS_KEY; if (!API || !KEY) { console.log('API and MAP_OPS_KEY are needed'); process.exit(1); }
const H = { 'x-ops-key': KEY }, W = process.env.SR_WEIGHTS || '/tmp/sr';
const call = async (method, p, body, headers = {}) => { for (let i = 0; i < 5; i++) { try { const r = await fetch(API + p, { method, headers: { ...H, ...headers }, body }); if (r.status < 500) return r; } catch {} await new Promise((ok) => setTimeout(ok, 1500 * (i + 1))); } throw new Error('failed ' + method + ' ' + p); };
const js = async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok || j.ok === false) throw new Error(`${r.status} ${JSON.stringify(j).slice(0, 200)}`); return j; };
const post = (p, o) => call('POST', p, JSON.stringify(o || {}), { 'content-type': 'application/json' }).then(js);
const run = (args, onLine) => new Promise((ok, no) => { const c = spawn('python3', args); let err = '', buf = '';
  c.stdout.on('data', (d) => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { onLine(buf.slice(0, i)); buf = buf.slice(i + 1); } }); c.stderr.on('data', (d) => { err += d; }); c.on('close', (code) => (code ? no(new Error(err.trim().split('\n').pop() || 'code ' + code)) : ok())); });

const { maps = [] } = await js(await call('GET', '/api/ops/maps/sharp')); console.log('AI-sharpened copies asked:', maps.length);
for (const m of maps.slice(0, 3)) { const dir = fs.mkdtempSync('/tmp/shp-'); const src = path.join(dir, 'o'), out = path.join(dir, 'out.jpg'); let nid = null, last = 0; const t0 = Date.now();
  try { const r = await call('GET', `/api/ops/maps/${m.id}/original`); if (!r.ok) throw new Error('original ' + r.status); fs.writeFileSync(src, Buffer.from(await r.arrayBuffer()));
    await post(`/api/ops/maps/${m.id}/sharp/progress`, { step: 'work' });
    await run(['-I', path.join(import.meta.dirname, 'sharpen.py'), src, out, String(m.scale), m.clean ? '1' : '0', W], (line) => { const p = line.split(' ');
      if (p[0] === 'cleaned') post(`/api/ops/maps/${m.id}/sharp/progress`, { step: 'cleaned' }).catch(() => {});
      if (p[0] === 'part' && Date.now() - last > 20000) { last = Date.now(); post(`/api/ops/maps/${m.id}/sharp/progress`, { step: 'part', part: +p[1], of: +p[2] }).catch(() => {}); } });
    const buf = fs.readFileSync(out);
    nid = (await post(`/api/ops/maps/${m.id}/sharp/start`, { size: buf.length })).id;
    const st = await js(await call('POST', `/api/ops/maps/${nid}/original/start`)); const parts = [];
    for (let n = 1, off = 0; off < buf.length; n++, off += st.partSize) parts.push((await js(await call('PUT', `/api/ops/maps/${nid}/original/part?mp=${encodeURIComponent(st.mp)}&n=${n}`, buf.subarray(off, off + st.partSize)))).part);
    await post(`/api/ops/maps/${nid}/original/done`, { mp: st.mp, parts });
    await post(`/api/ops/maps/${nid}/sharp/done`, {});
    console.log(`  ${m.id}: AI copy ${nid}, ${(buf.length / 1048576).toFixed(1)} MB in ${Math.round((Date.now() - t0) / 60000)} min`);
  } catch (e) { console.log('  sharpen FAILED', m.id, String(e).slice(0, 200)); await post(`/api/ops/maps/${m.id}/sharp/progress`, { step: 'failed', why: String(e.message || e).slice(0, 150) }).catch(() => {}); if (nid) await post(`/api/ops/maps/${nid}/sharp/done`, { failed: true }).catch(() => {}); }
  finally { fs.rmSync(dir, { recursive: true, force: true }); } }
