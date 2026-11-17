// Link previews for the rest of the site: asks the site what is missing in one language (chapters, prophets, places,
// posts, archive items, each with the facts to draw), draws each 1200×630 picture in a real browser with public/og-card.js
// (so the Arabic joins exactly as on the site) and sends it back; the site keeps it on the public file host. Pictures of maps
// and photos are fetched from the site first. Run by .github/workflows/cards.yml, one language per run.
import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright';
const LANG = process.env.LANG_CODE || 'en', API = process.env.API, KEY = process.env.MAP_OPS_KEY, LIMIT = Number(process.env.LIMIT || 0);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const call = (m, p, body) => fetch(API + p, { method: m, headers: { 'x-ops-key': KEY, ...(body ? { 'content-type': 'image/jpeg' } : {}) }, body });
const res = await (await call('GET', `/api/ops/maps/og/pages?lang=${LANG}${LIMIT ? '&limit=' + LIMIT : ''}`)).json();
if (!res.ok) { console.log('list failed', res); process.exit(1); }
const site = res.site || API, S = res.S, items = res.items;
console.log(LANG, 'pictures:', res.total, 'made:', res.have, 'to make:', items.length); if (!items.length) process.exit(0);

// the verses (chapter's first verse, a place's verse) from the same verse files as Share
const chapters = JSON.parse(fs.readFileSync(path.join(root, 'src/data/chapters.json'), 'utf8'));
const IDX = { en: 4, kab: 5, es: 6, fr: 7 }; const AR_D = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[+d]);
const KV = {}; const kv = (c) => (KV[c] ||= JSON.parse(fs.readFileSync(path.join(root, `public/kv/${String(c).padStart(3, '0')}.json`), 'utf8')));
const trOf = (row) => (LANG === 'ar' ? '' : row?.[IDX[LANG]] || row?.[4] || '');
function verseFor(it) {
  if (it.kind === 'chapter') { const K = kv(it.d.n); const r1 = K[1]; if (!r1) return null; let ar = r1[0], tr = trOf(r1);
    if (ar.replace(/[ً-ٰٟۖ-ۭ\s]/g, '').length < 8 && K[2]) { ar = `${r1[0]} ﴿${AR_D(1)}﴾ ${K[2][0]} ﴿${AR_D(2)}﴾`; tr = [tr, trOf(K[2])].filter(Boolean).join(' '); }
    return { ar, tr }; }
  if (it.kind === 'place' && /^\d{1,3}:\d{1,3}$/.test(it.d.verse || '')) { const [c, v] = it.d.verse.split(':').map(Number); const row = kv(c)?.[v]; if (!row) return null;
    const ch = chapters.find((x) => x.n === c); return { ar: row[0], tr: trOf(row), ref: LANG === 'ar' ? `${ch?.ar || ''} ${AR_D(c)}:${AR_D(v)}` : `${c}:${v}` }; }
  return null;
}
// pictures: fetched here, handed to the page as data
const abs = (u) => (u && u.startsWith('/') ? site + u : u);
async function grab(u) { for (let a = 0; a < 3; a++) { try { const r = await fetch(abs(u)); if (r.ok) { const ct = r.headers.get('content-type') || 'image/webp'; if (!ct.startsWith('image/')) return null; return `data:${ct};base64,${Buffer.from(await r.arrayBuffer()).toString('base64')}`; } if (r.status === 404 || r.status === 403) return null; } catch {} await new Promise((ok) => setTimeout(ok, 800 * (a + 1))); } return null; }

// fonts as data (the page has no web address of its own), as in the verse previews
const b64 = (f) => fs.readFileSync(path.join(root, 'public', f)).toString('base64');
const faces = [{ family: 'Hafs', file: 'fonts/hafs.woff2' }, { family: 'HafsBasm', file: 'fonts/hafs-basmala.woff2' }];
for (const line of fs.readFileSync(path.join(root, 'src/styles/fonts.css'), 'utf8').split('\n')) { const m = line.match(/font-family: '(Inter|Fraunces)'; font-style: (normal|italic); font-weight: (\d+);.*url\(\/([^)]+)\).*unicode-range: ([^;]+);/); if (m) faces.push({ family: m[1], style: m[2], weight: m[3], file: m[4], range: m[5] }); }
const card = fs.readFileSync(path.join(root, 'public/og-card.js'), 'utf8').replace(/^export /gm, '');
const b = await chromium.launch(); const p = await b.newPage(); await p.setContent('<canvas id="c"></canvas>');
await p.evaluate(async (faces) => { for (const f of faces) { try { const ff = new FontFace(f.family, `url(data:font/woff2;base64,${f.data})`, { weight: f.weight || 'normal', style: f.style || 'normal', ...(f.range ? { unicodeRange: f.range } : {}) }); await ff.load(); document.fonts.add(ff); } catch {} } }, faces.map((f) => ({ ...f, data: b64(f.file) })));
await p.addScriptTag({ content: card + '\nwindow.__draw = draw;' });
await p.evaluate(() => Promise.all(['400 80px Hafs', '400 40px HafsBasm', '500 40px Inter', '700 40px Inter', '600 44px Fraunces', '700 30px Fraunces'].map((f) => document.fonts.load(f).catch(() => null))));

let sent = 0, failed = 0, skipped = 0; const t0 = Date.now(); const queue = [];
const send = async (it, buf) => { for (let a = 0; a < 3; a++) { try { const r = await call('PUT', `/api/ops/maps/og/p/${LANG}/${it.key}`, buf); if (r.ok) { sent++; return; } } catch {} await new Promise((ok) => setTimeout(ok, 1500 * (a + 1))); } failed++; console.log('failed', it.key); };
for (const it of items) {
  const o = { kind: it.kind, d: it.d, S, rtl: LANG === 'ar', link: it.link, verse: verseFor(it) };
  let img = null, tiles = null;
  if (it.d.img) { img = await grab(it.d.img); if (!img && it.kind === 'archive') { skipped++; continue; } }
  let imgs = null; if (it.d.imgs?.length > 1) { imgs = (await Promise.all(it.d.imgs.map((u) => grab(u)))).filter(Boolean); if (imgs.length < 2) imgs = null; }
  if (it.d.crop) { tiles = await Promise.all(it.d.crop.tiles.map(async (t) => ({ ...t, src: await grab(t.src) }))); if (tiles.some((t) => !t.src)) { skipped++; continue; } }
  let data;
  try { data = await p.evaluate(async ({ o, img, tiles, imgs }) => {
      const load = (src) => new Promise((ok) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => ok(null); i.src = src; });
      if (img) o.img = await load(img); if (imgs) o.imgs = (await Promise.all(imgs.map((u) => load(u)))).filter(Boolean); if (tiles) o.tiles = await Promise.all(tiles.map(async (t) => ({ ...t, img: await load(t.src) })));
      return window.__draw(document.getElementById('c'), o).toDataURL('image/jpeg', 0.86).split(',')[1]; }, { o, img, tiles, imgs }); }
  catch (e) { failed++; console.log('draw failed', it.key, String(e).slice(0, 200)); continue; }
  queue.push(send(it, Buffer.from(data, 'base64'))); if (queue.length >= 6) await Promise.race(queue.splice(0, 1));
  if ((sent + failed) % 200 === 0 && sent) console.log(sent, 'sent', Math.round((Date.now() - t0) / 1000) + 's');
}
await Promise.all(queue); await b.close();
console.log(LANG, 'sent', sent, 'failed', failed, 'skipped (picture not ready)', skipped, 'in', Math.round((Date.now() - t0) / 1000) + 's');
if (failed > Math.max(5, items.length * 0.05)) process.exit(1);
