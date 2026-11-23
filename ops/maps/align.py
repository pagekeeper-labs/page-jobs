# Lines up two pictures of the same map (an older copy and a sharper scan): SIFT points, matched both ways, then a
# similarity transform (move, turn, scale) found with RANSAC. Prints JSON: m maps a point on the first picture, as fractions
# of its width and height, to the same point on the second, as fractions of the second's size; inl is how many points agree.
import sys, json
import cv2, numpy as np

def load(p):
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if im is None: raise SystemExit(json.dumps({"m": None, "inl": 0, "why": "unreadable"}))
    s = 1600 / max(im.shape)
    if s < 1: im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(im)

a, b = load(sys.argv[1]), load(sys.argv[2])
sift = cv2.SIFT_create(nfeatures=6000)
ka, da = sift.detectAndCompute(a, None); kb, db = sift.detectAndCompute(b, None)
if da is None or db is None or len(ka) < 10 or len(kb) < 10: print(json.dumps({"m": None, "inl": 0, "why": "few points"})); sys.exit()
mt = cv2.BFMatcher(cv2.NORM_L2)
good = [m for m, n in (p for p in mt.knnMatch(da, db, k=2) if len(p) == 2) if m.distance < 0.75 * n.distance]
if len(good) < 12: print(json.dumps({"m": None, "inl": len(good), "why": "few matches"})); sys.exit()
pa = np.float32([ka[m.queryIdx].pt for m in good]); pb = np.float32([kb[m.trainIdx].pt for m in good])
M, mask = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=5000, confidence=0.995)
inl = int(mask.sum()) if mask is not None else 0
if M is None: print(json.dumps({"m": None, "inl": inl, "why": "no fit"})); sys.exit()
ha, wa = a.shape; hb, wb = b.shape
(p, q, tx), (r, s, ty) = M.tolist()
m = [p * wa / wb, q * ha / wb, tx / wb, r * wa / hb, s * ha / hb, ty / hb]
print(json.dumps({"m": [round(v, 7) for v in m], "inl": inl, "of": len(good)}))
