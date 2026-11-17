// Verse link previews: draws each verse's 1200×630 picture with the same code as Share (public/verse-card.js),
// in a real browser (so the Arabic joins exactly as on the site), and sends the ones not made yet to the site, which keeps them
// on the public file host. Run by .github/workflows/cards.yml, one language per run: LANG=en|fr|ar|es|kab.
import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright';
const LANG = process.env.LANG_CODE || 'en', API = process.env.API, KEY = process.env.MAP_OPS_KEY, LIMIT = Number(process.env.LIMIT || 0);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const call = (m, p, body) => fetch(API + p, { method: m, headers: { 'x-ops-key': KEY, ...(body ? { 'content-type': 'image/jpeg' } : {}) }, body });
const have = new Set(((await (await call('GET', `/api/ops/maps/og/have?lang=${LANG}`)).json()).have) || []);
const HOST = String(((await (await call('GET', `/api/ops/maps/og/pages?lang=en&limit=1`)).json()).site) || '').replace(/^https?:\/\//, '');
console.log(LANG, 'already made:', have.size);
const chapters = JSON.parse(fs.readFileSync(path.join(root, 'src/data/chapters.json'), 'utf8'));
const IDX = { en: 4, kab: 5, es: 6, fr: 7 }; const AR_D = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[+d]);
const BASMALA = 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'; // as in public/verse-share.js; not for chapter 9, nor 1:1
const jobs = [];
for (const ch of chapters) { const kv = JSON.parse(fs.readFileSync(path.join(root, `public/kv/${String(ch.n).padStart(3, '0')}.json`), 'utf8'));
  const meaning = (ch.meaning[LANG === 'kab' ? 'fr' : LANG] || ch.meaning.en);
  for (let v = 1; v <= ch.verses; v++) { if (have.has(`${ch.n}-${v}`)) continue; const row = kv[v]; if (!row) continue;
    jobs.push({ c: ch.n, v, o: { kind: 'preview', style: 'paper', basm: ch.n === 9 || (ch.n === 1 && v === 1) ? '' : BASMALA, ar: row[0], vnum: AR_D(v), tr: LANG === 'ar' ? '' : (row[IDX[LANG]] || row[4] || ''), surah: 'سُورَةُ ' + ch.ar,
      ref: LANG === 'ar' ? `${ch.ar} ${AR_D(ch.n)}:${AR_D(v)}` : `${meaning} · ${ch.n}:${v}`, refRtl: LANG === 'ar', link: `${HOST}/koran/${ch.n}/${v}` } }); } }
if (LIMIT) jobs.splice(LIMIT);
console.log('to make:', jobs.length); if (!jobs.length) process.exit(0);
// fonts as data (the page has no web address of its own)
const b64 = (f) => fs.readFileSync(path.join(root, 'public', f)).toString('base64');
const faces = [{ family: 'Hafs', file: 'fonts/hafs.woff2' }, { family: 'HafsBasm', file: 'fonts/hafs-basmala.woff2' }];
for (const line of fs.readFileSync(path.join(root, 'src/styles/fonts.css'), 'utf8').split('\n')) { const m = line.match(/font-family: '(Inter|Fraunces)'; font-style: normal; font-weight: (\d+);.*url\(\/([^)]+)\).*unicode-range: ([^;]+);/); if (m) faces.push({ family: m[1], weight: m[2], file: m[3], range: m[4] }); }
const card = fs.readFileSync(path.join(root, 'public/verse-card.js'), 'utf8').replace(/^export /gm, '');
const b = await chromium.launch(); const p = await b.newPage(); await p.setContent('<canvas id="c"></canvas>');
await p.evaluate(async (faces) => { for (const f of faces) { const ff = new FontFace(f.family, `url(data:font/woff2;base64,${f.data})`, { weight: f.weight || 'normal', ...(f.range ? { unicodeRange: f.range } : {}) }); await ff.load(); document.fonts.add(ff); } }, faces.map((f) => ({ ...f, data: b64(f.file) })));
await p.addScriptTag({ content: card + '\nwindow.__draw = draw; window.__ready = ready;' }); await p.evaluate(() => window.__ready());
let sent = 0, failed = 0; const t0 = Date.now(); const queue = [];
const send = async (j, buf) => { for (let a = 0; a < 3; a++) { try { const r = await call('PUT', `/api/ops/maps/og/${LANG}/${j.c}-${j.v}`, buf); if (r.ok) { sent++; return; } } catch {} await new Promise((ok) => setTimeout(ok, 1500 * (a + 1))); } failed++; console.log('failed', j.c + ':' + j.v); };
for (const j of jobs) {
  const data = await p.evaluate((o) => window.__draw(document.getElementById('c'), o).toDataURL('image/jpeg', 0.86).split(',')[1], j.o);
  queue.push(send(j, Buffer.from(data, 'base64'))); if (queue.length >= 8) await Promise.race(queue.splice(0, 1));
  if ((sent + failed) % 500 === 0 && sent) console.log(sent, 'sent', Math.round((Date.now() - t0) / 1000) + 's');
}
await Promise.all(queue); await b.close();
console.log(LANG, 'sent', sent, 'failed', failed, 'in', Math.round((Date.now() - t0) / 1000) + 's');
