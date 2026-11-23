#!/usr/bin/env python3
"""AI-sharpened copy of a map (board 429). Optional first step: the paper's stains, foxing and fold shadows evened out (the
background is estimated with a wide median of the paper and divided out; the ink is left alone). Then Real-ESRGAN (Xintao Wang
et al., BSD-3-Clause), run on the CPU in overlapping tiles, enlarges the picture 2x or 4x and redraws fine detail.
The result is never the original: the site labels it everywhere as AI-sharpened.
Usage: sharpen.py <in> <out.jpg> <scale 2|4> <clean 0|1> <weights dir>   (progress lines: 'part <done> <of>')"""
import sys, math, cv2, numpy as np, torch
from spandrel import ModelLoader

src, dst, scale, clean, wdir = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == '1', sys.argv[5]
cv2.setNumThreads(2); torch.set_num_threads(max(1, torch.get_num_threads()))
im = cv2.imread(src, cv2.IMREAD_COLOR)
if im is None: sys.exit('unreadable')
h, w = im.shape[:2]
MAX_OUT = 14000                                  # longest side of the result, so the file stays workable
scale = 4 if scale >= 4 and max(h, w) * 4 <= MAX_OUT else 2 if max(h, w) * 2 <= MAX_OUT else 1
if scale < 2: sys.exit('already_large')

if clean:
    # paper only: a wide median of a small copy is the paper's tone with its stains and fold shadows, without the ink
    k = 1600 / max(h, w); sm = cv2.resize(im, (max(1, int(w * k)), max(1, int(h * k))), interpolation=cv2.INTER_AREA)
    bg = cv2.medianBlur(cv2.dilate(sm, np.ones((5, 5), np.uint8)), 41)
    bg = cv2.GaussianBlur(bg, (0, 0), 6); bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) + 1
    paper = np.median(bg.reshape(-1, 3), axis=0)  # the paper's usual colour, so the page keeps its warmth
    im = np.clip(im.astype(np.float32) / bg * paper, 0, 255).astype(np.uint8); del bg
    print('cleaned', flush=True)

model = ModelLoader().load_from_file(f'{wdir}/x{scale}.pth').model.eval()
T, P = 192, 16                                     # tile and overlap (input pixels)
out = np.zeros((h * scale, w * scale, 3), np.uint8)
xs, ys = list(range(0, w, T)), list(range(0, h, T)); n, done = len(xs) * len(ys), 0
with torch.inference_mode():
    for y in ys:
        for x in xs:
            x0, y0, x1, y1 = max(0, x - P), max(0, y - P), min(w, x + T + P), min(h, y + T + P)
            t = torch.from_numpy(cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float().div(255).unsqueeze(0)
            r = model(t).clamp(0, 1).squeeze(0).permute(1, 2, 0).mul(255).round().byte().numpy()
            r = cv2.cvtColor(r, cv2.COLOR_RGB2BGR)
            cx, cy, cw, ch = (x - x0) * scale, (y - y0) * scale, min(T, w - x) * scale, min(T, h - y) * scale
            out[y * scale:y * scale + ch, x * scale:x * scale + cw] = r[cy:cy + ch, cx:cx + cw]
            done += 1
            if done % 10 == 0 or done == n: print(f'part {done} {n}', flush=True)
cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, 92])
print(f'done {w * scale} {h * scale}', flush=True)
