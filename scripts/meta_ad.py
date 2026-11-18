# Meta 投流样片：9:16（或 "format": "16:9" 横屏）、冷调高级感调色、首帧折扣大字（第一个镜头结束前淡出）、按鼓点切镜头、黑底白 Logo 结尾
# 用法：python3 scripts/meta_ad.py meta_plans/FF357.json [--materials materials] [--out renders]
import argparse, json, os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--materials", default="materials"); ap.add_argument("--out", default="renders")
ap.add_argument("--work", default="work_meta")
A = ap.parse_args()
P = json.load(open(A.plan))
NAME, MODEL = P["name"], P["model"]
LAND = P.get("format") == "16:9"
W, H, FPS = (1920, 1080, 30) if LAND else (1080, 1920, 30)
WORK = os.path.join(A.work, NAME); os.makedirs(WORK, exist_ok=True); os.makedirs(A.out, exist_ok=True)
FONT = os.path.join(ROOT, "assets/fonts/Inter-Variable.ttf")
LOGO = os.path.join(ROOT, "assets/logo/CYRIL_Logo_white.png")
MUSIC = os.path.join(ROOT, "assets/music", P["music"]["file"])
BJ = MUSIC.rsplit(".", 1)[0] + ".beats.json"
if os.path.exists(BJ): BEATS = json.load(open(BJ))["beats"]
else: BEATS = [P["music"]["start"] + i * 60 / P["music"]["bpm"] for i in range(400)]   # 没有节拍表就按 BPM 匀速

# 冷灰色调：降饱和、暗部偏青亮部微暖、S 曲线、暗角、细颗粒
GRADE = ("eq=contrast=1.10:brightness=-0.025:saturation=0.74,"
         "colorbalance=rs=-0.04:gs=-0.01:bs=0.05:rm=-0.01:bm=0.01:rh=0.03:gh=0.01:bh=-0.02,"
         "curves=all='0/0.035 0.25/0.21 0.5/0.5 0.78/0.82 1/0.96',"
         "vignette=angle=PI/5,unsharp=5:5:0.35,noise=alls=5:allf=t+u")
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "15360"]

def run(cmd): subprocess.run(cmd, check=True)

def font(sz, weight):
    f = ImageFont.truetype(FONT, sz); f.set_variation_by_name(weight); return f

def spaced(d, x, y, text, f, track, fill):
    ws = [d.textlength(c, font=f) for c in text]; x -= (sum(ws) + track * (len(text) - 1)) / 2
    for c, w in zip(text, ws): d.text((x, y), c, font=f, fill=fill, anchor="ls"); x += w + track

def offer_png_land(o):
    # 横屏：折扣字放左半边（第一个镜头的竖画面放右边），左侧压暗渐变
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt); cx = 600
    spaced(d, cx, 395, o.get("kicker", "LIMITED TIME"), font(40, b"SemiBold"), 16, (255, 255, 255, 240))
    d.rectangle([cx - 50, 427, cx + 50, 430], fill=(255, 255, 255, 220))
    title = o.get("title", "20% OFF"); sz = 230
    while sz > 120 and d.textlength(title, font=font(sz, b"Black")) > 1050: sz -= 10
    spaced(d, cx, 665, title, font(sz, b"Black"), -8, (255, 255, 255, 255))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(txt.getchannel("A").point(lambda a: a * 0.55).filter(ImageFilter.GaussianBlur(18)))
    g = Image.new("L", (W, 1))
    for x in range(W): g.putpixel((x, 0), int(150 * max(0, 1 - x / 1300) ** 1.3))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 255)); out.putalpha(g.resize((W, H)))
    out.alpha_composite(sh); out.alpha_composite(txt)
    p = os.path.join(WORK, "offer.png"); out.save(p); return p

def offer_png(o):
    if LAND: return offer_png_land(o)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    spaced(d, W / 2, 500, o.get("kicker", "LIMITED TIME"), font(40, b"SemiBold"), 16, (255, 255, 255, 240))
    d.rectangle([W / 2 - 50, 532, W / 2 + 50, 535], fill=(255, 255, 255, 220))
    title = o.get("title", "20% OFF"); sz = 220
    while sz > 120 and d.textlength(title, font=font(sz, b"Black")) > W - 120: sz -= 10
    spaced(d, W / 2, 770, title, font(sz, b"Black"), -8, (255, 255, 255, 255))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(txt.getchannel("A").point(lambda a: a * 0.55).filter(ImageFilter.GaussianBlur(18)))
    g = Image.new("L", (1, H))
    for y in range(H): g.putpixel((0, y), int(140 * max(0, 1 - y / 1150) ** 1.5))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 255)); out.putalpha(g.resize((W, H)))
    out.alpha_composite(sh); out.alpha_composite(txt)
    p = os.path.join(WORK, "offer.png"); out.save(p); return p

def end_png(e):
    L = Image.open(LOGO).convert("RGBA"); lw = 560 if LAND else 620; L = L.resize((lw, int(L.height * lw / L.width)), Image.LANCZOS)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); im.alpha_composite(L, ((W - lw) // 2, (H - L.height) // 2 - 60))
    spaced(ImageDraw.Draw(im), W / 2, (H + L.height) // 2 + 70, e.get("url", "CYRILHELMETS.COM"), font(34, b"Medium"), 10, (255, 255, 255, 230))
    p = os.path.join(WORK, "end.png"); im.convert("RGB").save(p); return p

# 切点：按曲子的真实鼓点（beats.json），从 music.start 之后的第一拍开始数，换算成整帧
t0 = P["music"]["start"]
rel = [b - t0 for b in BEATS if b >= t0 - 1e-3]
counts = [s["beats"] for s in P["segments"]] + [P["endcard"]["beats"]]
idx = [0]
for c in counts: idx.append(idx[-1] + c)
frames = [round(rel[i] * FPS) for i in idx]
durs = [(frames[i + 1] - frames[i]) / FPS for i in range(len(counts))]
total = frames[-1] / FPS

def is_land(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]; w, h = st["width"], st["height"]
    if abs(int(float(((st.get("side_data_list") or [{}])[0]).get("rotation", 0) or 0))) in (90, 270): w, h = h, w
    return w > h

def land_seg(i, s, du, o, offer):
    """横屏镜头三种版式：
    - 横屏素材：铺满
    - 竖屏素材（默认）：竖画面放中间（pos: left/center/right），背景是同一镜头放大、模糊、压暗
    - "clips": [3 条] 三联屏：三个竖画面并排，各自的 start 见 "starts"
    """
    ins, fc = [], []
    if s.get("clips"):
        pw = W // 3
        for k, (c, st) in enumerate(zip(s["clips"], s["starts"])):
            ins += ["-ss", str(st), "-t", f"{du:.3f}", "-i", os.path.join(A.materials, MODEL, c)]
            fc.append(f"[{k}:v]fps={FPS},scale={pw}:{H}:force_original_aspect_ratio=increase,crop={pw}:{H},setsar=1[p{k}]")
        fc.append(f"[p0][p1][p2]hstack=3,drawbox=x={pw - 2}:y=0:w=4:h={H}:color=black:t=fill,drawbox=x={2 * pw - 2}:y=0:w=4:h={H}:color=black:t=fill,{GRADE}[b]")
    else:
        src = os.path.join(A.materials, MODEL, s["clip"])
        ins += ["-ss", str(s["start"]), "-t", f"{du:.3f}", "-i", src]
        if is_land(src):
            fc.append(f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,{GRADE}[b]")
        else:
            pw = 608; pos = s.get("pos", "right" if offer else "center")
            x = {"left": 300, "center": (W - pw) // 2, "right": W - pw - 300}[pos]
            fc.append(f"[0:v]fps={FPS},split[a][f];"
                      f"[a]scale=384:216:force_original_aspect_ratio=increase,crop=384:216,boxblur=10:2,scale={W}:{H},eq=brightness=-0.13:saturation=0.8,setsar=1[bg];"
                      f"[f]scale={pw}:{H}:force_original_aspect_ratio=increase,crop={pw}:{H},setsar=1[fg];"
                      f"[bg][fg]overlay={x}:0,{GRADE}[b]")
    n = len(ins) // 6
    if offer:
        ins += ["-loop", "1", "-t", f"{du:.3f}", "-i", offer]
        fc.append(f"[{n}:v]format=rgba,fade=out:st={du - 0.35:.3f}:d=0.3:alpha=1[ov];[b][ov]overlay=0:0:shortest=1,format=yuv420p[v]")
    else:
        fc.append("[b]format=yuv420p[v]")
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-an", *ENC, "-t", f"{du:.3f}", o])

segs = []
offer = offer_png(P["offer"]) if P.get("offer") else None
for i, (s, du) in enumerate(zip(P["segments"], durs)):
    src = os.path.join(A.materials, MODEL, s.get("clip", "")); o = os.path.join(WORK, f"seg{i:02d}.mp4"); segs.append(o)
    if LAND:
        land_seg(i, s, du, o, offer if i == 0 else None)
    elif i == 0 and offer:
        base = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},{GRADE}"
        fc = f"[0:v]{base}[b];[1:v]format=rgba,fade=out:st={du - 0.35:.3f}:d=0.3:alpha=1[ov];[b][ov]overlay=0:0:shortest=1,format=yuv420p[v]"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"]), "-t", f"{du:.3f}", "-i", src, "-loop", "1", "-t", f"{du:.3f}", "-i", offer,
             "-filter_complex", fc, "-map", "[v]", "-an", *ENC, "-t", f"{du:.3f}", o])
    else:
        base = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},{GRADE}"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"]), "-t", f"{du:.3f}", "-i", src, "-an", "-vf", base + ",format=yuv420p", *ENC, "-t", f"{du:.3f}", o])
    print(f"镜头 {i + 1}/{len(P['segments'])} {s.get('clip') or '+'.join(s['clips'])} +{du:.2f}s")
end = os.path.join(WORK, "end.mp4"); segs.append(end)
run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{durs[-1]:.3f}", "-i", end_png(P["endcard"]), "-vf", "fps=30,fade=in:0:4,format=yuv420p", *ENC, end])

lst = os.path.join(WORK, "list.txt"); open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in segs))
body = os.path.join(WORK, "body.mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])

# 配乐：压 4dB + 轻压缩 + 限幅（这首母带峰值超 0dB，不限幅会爆音），结尾 1.5 秒淡出；画面不重编码
af = (f"aresample=48000,volume=-4dB,acompressor=threshold=-14dB:ratio=2.5:attack=5:release=80:makeup=2,"
      f"alimiter=limit=0.84:attack=3:release=50:level=false,afade=out:st={total - 1.5:.3f}:d=1.5")
out = os.path.join(A.out, f"{NAME}.mp4")
run(["ffmpeg", "-v", "error", "-y", "-i", body, "-ss", str(t0), "-t", f"{total:.3f}", "-i", MUSIC, "-af", af,
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", f"{total:.3f}", out])
run(["ffmpeg", "-v", "error", "-y", "-ss", "0.1", "-i", out, "-frames:v", "1", os.path.join(A.out, f"{NAME}_cover.jpg")])
print("完成", out, f"{total:.2f}s")
