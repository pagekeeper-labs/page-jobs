// Downloads the public files the link previews are drawn with (verse files, fonts, the drawing code) from the website itself,
// so this repository holds no copy of them. Run from the repository root: node ops/cards/files.mjs <site>
import fs from 'node:fs'; import path from 'node:path';
const site = (process.argv[2] || process.env.API || '').replace(/\/$/, '');
const need = new Set(['og-card.js', 'verse-card.js', 'fonts/hafs.woff2', 'fonts/hafs-basmala.woff2']);
for (let c = 1; c <= 114; c++) need.add(`kv/${String(c).padStart(3, '0')}.json`);
for (const m of fs.readFileSync('src/styles/fonts.css', 'utf8').matchAll(/font-family: '(?:Inter|Fraunces)';[^\n]*?url\(\/([^)]+)\)/g)) need.add(m[1]);
let ok = 0, bad = 0;
const get = async (f) => { for (let a = 0; a < 4; a++) { try { const r = await fetch(site + '/' + f); if (r.ok) { const out = path.join('public', f); fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, Buffer.from(await r.arrayBuffer())); ok++; return; } } catch {} await new Promise((s) => setTimeout(s, 1000 * (a + 1))); } bad++; };
const list = [...need]; for (let i = 0; i < list.length; i += 12) await Promise.all(list.slice(i, i + 12).map(get));
console.log('files', ok, 'missing', bad); if (bad) process.exit(1);
