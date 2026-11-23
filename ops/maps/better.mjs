// The map bot (admins only, started on the site). Three steps, each picked up when the site has something waiting:
// 1. find: the same map at a higher resolution in libraries that share full-size scans (Library of Congress, Wikimedia Commons),
//    by the map's title, maker and date; each result's picture is compared with the map's fingerprint; only copies with more
//    pixels than the one on the site are offered. 2. use: the chosen scan is downloaded and sent to the site as a new copy of the
//    map (its tiles are then cut by tile.mjs). 3. line up: once cut, the old and new pictures are matched point by point
//    (align.py) so tags and readings land on the same places. Run before and after tile.mjs. Needs API and MAP_OPS_KEY.
import fs from 'node:fs'; import path from 'node:path'; import { execFileSync } from 'node:child_process';
import sharp from 'sharp';
const API = process.env.API, KEY = process.env.MAP_OPS_KEY; if (!API || !KEY) { console.log('API and MAP_OPS_KEY are needed'); process.exit(1); }
const H = { 'x-ops-key': KEY }; const UA = { 'user-agent': 'PageKeeperMapChecker/1.0' };
sharp.cache(false);
const call = async (method, p, body, headers = {}) => { for (let i = 0; i < 5; i++) { try { const r = await fetch(API + p, { method, headers: { ...H, ...headers }, body }); if (r.status < 500) return r; } catch {} await new Promise((ok) => setTimeout(ok, 1500 * (i + 1))); } throw new Error('failed ' + method + ' ' + p); };
const js = async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok || j.ok === false) throw new Error(`${r.status} ${JSON.stringify(j).slice(0, 200)}`); return j; };
const post = (p, o) => call('POST', p, JSON.stringify(o || {}), { 'content-type': 'application/json' }).then(js);
const get = async (u, as = 'json', ms = 25000) => { try { const r = await fetch(u, { headers: UA, signal: AbortSignal.timeout(ms) }); if (!r.ok) return null; return as === 'json' ? await r.json() : Buffer.from(await r.arrayBuffer()); } catch { return null; } };
const strip = (s) => String(s ?? '').replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9]+;/gi, ' ').replace(/\s+/g, ' ').trim();
const fpOf = async (buf) => { const { data } = await sharp(buf, { limitInputPixels: false }).rotate().greyscale().resize(17, 16, { fit: 'fill' }).raw().toBuffer({ resolveWithObject: true });
  let bits = ''; for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) bits += data[y * 17 + x] > data[y * 17 + x + 1] ? '1' : '0'; return bits; };
const hexBits = (h) => [...h].map((c) => parseInt(c, 16).toString(2).padStart(4, '0')).join('');
const sim = (a, b) => { let d = 0; for (let i = 0; i < 256; i++) if (a[i] !== b[i]) d++; return Math.round((1 - d / 256) * 100); };
const picSim = async (url, fp) => { if (!fp || !url) return 0; const buf = await get(url, 'buf'); if (!buf) return 0; const mine = hexBits(fp);
  try { let best = sim(await fpOf(buf), mine); const t = await sharp(buf).rotate().trim({ threshold: 30 }).toBuffer().catch(() => null); if (t) best = Math.max(best, sim(await fpOf(t), mine)); return best; } catch { return 0; } };
const words = (s, n = 6) => String(s || '').replace(/[^\p{L}\p{N}\s'-]+/gu, ' ').split(/\s+/).filter((w) => w.length > 2 && !/^\d+$/.test(w)).slice(0, n).join(' ');

async function loc(q) {
  const j = await get('https://www.loc.gov/maps/?fo=json&c=8&q=' + encodeURIComponent(q)); if (!j?.results) return [];
  const out = [];
  for (const x of j.results.filter((x) => x.url)) { const imgs = (x.image_url || []).map(String); const iiif = imgs.find((u) => u.includes('/iiif/')); if (!iiif) continue;
    const base = iiif.replace(/\/full\/.*$/, ''); const info = await get(base + '/info.json'); if (!info?.width) continue;
    out.push({ src: 'Library of Congress', lib: 'Library of Congress', title: strip(x.item?.title || x.title), url: x.url.replace(/^http:/, 'https:'), thumb: base + '/full/!600,600/0/default.jpg', scan: base + '/full/full/0/default.jpg', w: info.width, h: info.height, lic: 'Library of Congress: see the catalogue' }); }
  return out;
}
async function commons(q) {
  const j = await get('https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=600&gsrsearch=' + encodeURIComponent(q + ' filetype:bitmap'));
  return Object.values(j?.query?.pages || {}).map((p) => { const ii = p.imageinfo?.[0] || {}; const m = ii.extmetadata || {}; const v = (k) => strip(m[k]?.value);
    return { src: 'Wikimedia Commons', lib: 'Wikimedia Commons', title: /gallica|bnf|biblioth[eè]que nationale/i.test(v('Credit') + v('ImageDescription')) ? 'uploaded from the BnF scan' : v('ObjectName') || strip(p.title).replace(/^File:|\.\w+$/g, ''), url: (ii.descriptionurl || '').replace(/^http:/, 'https:'), thumb: ii.thumburl, scan: ii.url, w: ii.width || 0, h: ii.height || 0, lic: v('LicenseShortName') || 'see the file page' }; }).filter((x) => x.url && x.scan);
}

const { find = [], use = [], align = [] } = await js(await call('GET', '/api/ops/maps/better'));
console.log(`map bot: ${find.length} to search, ${use.length} to download, ${align.length} to line up`);

// 1. find
for (const m of find) { try {
  const qs = [...new Set([words(m.title), words([m.title, m.maker].join(' '), 8), words([m.maker, m.year].join(' '), 5)].filter((q) => q.length > 6))].slice(0, 3);
  const found = new Map(); for (const q of qs) { for (const c of await commons(q)) found.set(c.scan, c); for (const c of await loc(q)) found.set(c.scan, c); }
  const area = (m.w || 1) * (m.h || 1); const bigger = [...found.values()].filter((c) => c.w * c.h > area * 1.15).slice(0, 16);
  for (const c of bigger) c.sim = await picSim(c.thumb, m.fp);
  const keep = bigger.filter((c) => c.sim >= 78).sort((a, b) => b.sim - a.sim || b.w * b.h - a.w * a.h).slice(0, 6);
  await post(`/api/ops/maps/${m.id}/better/found`, { cands: keep, searched: qs.join(' · ') });
  console.log(`  ${m.id}: ${found.size} results, ${bigger.length} bigger, ${keep.length} the same map`);
} catch (e) { console.log('  find FAILED', m.id, String(e).slice(0, 200)); await post(`/api/ops/maps/${m.id}/better/found`, { cands: [] }).catch(() => {}); } }

// 2. use: download, keep a JPEG as it is (no re-compression), anything else becomes a high-quality JPEG
for (const m of use) { let started = false; try {
  let buf = await get(m.cand.scan, 'buf', 600000); if (!buf || buf.length < 2048) throw new Error('download failed');
  const jpg = buf[0] === 0xff && buf[1] === 0xd8; if (!jpg) buf = await sharp(buf, { limitInputPixels: false, unlimited: true }).rotate().jpeg({ quality: 94, chromaSubsampling: '4:4:4' }).toBuffer();
  const meta = await sharp(buf, { limitInputPixels: false }).metadata(); console.log(`  ${m.id}: downloaded ${meta.width} × ${meta.height}, ${(buf.length / 1048576).toFixed(1)} MB`);
  const nid = (await post(`/api/ops/maps/${m.id}/better/start`, { size: buf.length })).id; started = true;
  const st = await js(await call('POST', `/api/ops/maps/${nid}/original/start`)); const parts = [];
  for (let n = 1, off = 0; off < buf.length; n++, off += st.partSize) parts.push((await js(await call('PUT', `/api/ops/maps/${nid}/original/part?mp=${encodeURIComponent(st.mp)}&n=${n}`, buf.subarray(off, off + st.partSize)))).part);
  await post(`/api/ops/maps/${nid}/original/done`, { mp: st.mp, parts });
  await post(`/api/ops/maps/${m.id}/better/done`, {});
} catch (e) { console.log('  use FAILED', m.id, String(e).slice(0, 200)); await post(`/api/ops/maps/${m.id}/better/done`, { failed: String(e).slice(0, 150) || 'failed', started }).catch(() => {}); } }

// 3. line up the old and the new picture (their 1,600 px previews: each the whole picture, so fractions carry over)
for (const m of align) { const dir = fs.mkdtempSync('/tmp/aln-'); try {
  const pa = path.join(dir, 'a.png'), pb = path.join(dir, 'b.png');
  for (const [id, f] of [[m.id, pa], [m.nid, pb]]) { const r = await call('GET', `/api/ops/maps/${id}/preview`); if (!r.ok) throw new Error('preview ' + r.status); await sharp(Buffer.from(await r.arrayBuffer())).png().toFile(f); }
  let res = { m: null, inl: 0 }; try { res = JSON.parse(execFileSync('python3', ['-I', path.join(import.meta.dirname, 'align.py'), pa, pb], { encoding: 'utf8', timeout: 180000 }).trim().split('\n').pop()); } catch (e) { console.log('  align.py', String(e).slice(0, 160)); }
  const j = await post(`/api/ops/maps/${m.id}/better/align`, res);
  console.log(`  ${m.id} → ${m.nid}: ${res.m ? 'lined up' : 'not lined up'} (${res.inl} points agree), readings moved ${j.moved}, outside ${j.kept}`);
} catch (e) { console.log('  align FAILED', m.id, String(e).slice(0, 200)); } finally { fs.rmSync(dir, { recursive: true, force: true }); } }
