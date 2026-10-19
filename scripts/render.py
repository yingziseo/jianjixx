# 通用剪辑脚本：读取 plans/<型号>.json，按音乐节拍剪成 30 秒 9:16 竖版，只输出网页版 + 封面图
# 用法：python3 scripts/render.py plans/R18.json [--materials materials] [--out renders]
#
# 剪辑规则（来自 R1-PRO 第1版的反馈，务必遵守）：
#   1. 每组字幕至少 7 拍（124BPM 约 3.4 秒），出现后马上能读到，不要一闪而过
#   2. 每个镜头不少于 3 拍（约 1.5 秒）；头盔快速转动的镜头放慢到 0.7 倍左右
#   3. 字幕只写官网已审核的卖点（只写 DOT FMVSS 218，不写 ECE、专利、尾翼提高稳定性）
#   4. 不用背景杂乱、不符合品牌调性的镜头（如仓库里一堆头盔）
#   5. 只输出网页版（约 9MB），每个镜头只编码一次，不做高清版再转码
#   6. 视频第一帧必须是封面（深色背景 + 白色Logo + 大号型号名，极简，不放人物），开头不能从黑场淡入
import json, os, subprocess, sys, argparse
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from fonts import font

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--materials", default="materials"); ap.add_argument("--out", default="renders")
ap.add_argument("--work", default=".work")
A = ap.parse_args()
P = json.load(open(A.plan, encoding="utf-8"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL, VER = P["model"], P.get("version", "v1")
BEAT = 60 / P["music"]["bpm"]
WORK = os.path.join(A.work, MODEL); os.makedirs(WORK, exist_ok=True); os.makedirs(A.out, exist_ok=True)
OUT = os.path.join(A.out, f"{MODEL}_30s_{VER}.mp4"); COVER = os.path.join(A.out, f"{MODEL}_cover_{VER}.jpg")
LOGO = os.path.join(ROOT, "assets/logo/logo-2.png")
# 网页版编码参数：每个镜头直接按这个编码，拼接时不再转码
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "3500k", "-bufsize", "5000k",
       "-pix_fmt", "yuv420p", "-r", "30", "-g", "60"]
VF = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=contrast=1.05:saturation=1.06,setsar=1"

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(" ".join(cmd[:6]) + "\n" + r.stderr[-1500:])

def clip(name): return os.path.join(A.materials, MODEL, name)

def spaced(d, xy, text, f, fill, track):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill); x += d.textlength(ch, font=f) + track

def wspaced(d, text, f, track): return sum(d.textlength(c, font=f) for c in text) + track * (len(text) - 1)

def shade(h, top_alpha=0, bottom_alpha=150, flip=False):
    g = Image.new("L", (1, h))
    for y in range(h):
        k = (y / (h - 1)) ** 1.6
        g.putpixel((0, h - 1 - y if flip else y), int(top_alpha + (bottom_alpha - top_alpha) * k))
    s = Image.new("RGBA", (1080, h), (0, 0, 0, 255)); s.putalpha(g.resize((1080, h))); return s

def text_png(key):
    small, big = P["texts"][key]
    p = os.path.join(WORK, f"txt_{key}.png")
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); im.alpha_composite(shade(560), (0, 1360))
    d = ImageDraw.Draw(im); x0, maxw = 88, 1080 - 88 * 2
    size = 96 if key == "title" else 76
    while True:                                    # 大字自动缩小，保证不超出画面
        f2 = font("bold", size)
        if wspaced(d, big, f2, 3) <= maxw or size <= 44: break
        size -= 2
    d.rectangle([x0, 1560, x0 + 64, 1565], fill=(255, 255, 255, 255))
    spaced(d, (x0, 1586), small, font("medium", 40), (255, 255, 255, 235), 5)
    spaced(d, (x0, 1640), big, f2, (255, 255, 255, 255), 3)
    im.save(p); return p

def logo(width):
    lg = Image.open(LOGO).convert("RGBA"); return lg.resize((width, int(width * lg.height / lg.width)), Image.LANCZOS)

def end_card():
    im = Image.new("RGB", (1080, 1920), (14, 14, 14)); lg = logo(600)
    im.paste(lg, ((1080 - 600) // 2, 700), lg); d = ImageDraw.Draw(im)
    f2, f1 = font("bold", 54), font("medium", 30); t = P["endcard"]["title"]
    spaced(d, ((1080 - wspaced(d, t, f2, 14)) / 2, 1080), t, f2, (255, 255, 255), 14)
    t = "CYRILHELMETS.COM"; spaced(d, ((1080 - wspaced(d, t, f1, 8)) / 2, 1170), t, f1, (190, 190, 190), 8)
    p = os.path.join(WORK, "endcard.png"); im.save(p); return p

def cover():
    """封面：极简风格，和片尾统一——深色背景 + 白色Logo + 大号型号名 + 品类小字（不放人物画面）"""
    c = P["cover"]
    im = Image.new("RGB", (1080, 1920), (14, 14, 14)); d = ImageDraw.Draw(im)
    lg = logo(360); im.paste(lg, ((1080 - 360) // 2, 610), lg)
    size = 150
    while True:                                          # 型号名自动缩小，保证不超出画面
        f = font("bold", size)
        if wspaced(d, c["title"], f, 10) <= 1080 - 160 or size <= 70: break
        size -= 4
    t = c["title"]; spaced(d, ((1080 - wspaced(d, t, f, 10)) / 2, 960), t, f, (255, 255, 255), 10)
    bottom = 960 + d.textbbox((0, 0), t, font=f)[3]       # 按标题实际高度定位短线和小字
    d.rectangle([(1080 - 64) // 2, bottom + 44, (1080 + 64) // 2, bottom + 48], fill=(255, 255, 255))
    f1 = font("medium", 34); t = c["kicker"]
    spaced(d, ((1080 - wspaced(d, t, f1, 8)) / 2, bottom + 76), t, f1, (190, 190, 190), 8)
    im.save(COVER, quality=92); return COVER

# 0. 封面：单独输出 JPG，同时作为视频开头的静帧（第一帧就是封面）
cover()
cov_dur = P["cover"].get("beats", 2) * BEAT; pc = os.path.join(WORK, "seg00_cover.mp4")
run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", COVER, "-t", f"{cov_dur:.4f}", "-vf", "fps=30,setsar=1", *ENC, pc])

# 1. 每个镜头一次完成：裁切 + 调色 + 变速 + 字幕
segs = P["segments"]; parts = [pc]; t = cov_dur
spans = [s.get("text") for s in segs]
for i, s in enumerate(segs):
    dur = s["beats"] * BEAT; speed = s.get("speed", 1.0); key = s.get("text")
    first = key and (i == 0 or spans[i - 1] != key); last = key and (i == len(segs) - 1 or spans[i + 1] != key)
    out = os.path.join(WORK, f"seg{i:02d}.mp4")
    base = f"[0:v]setpts=PTS/{speed},{VF}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"]), "-t", f"{dur * speed + 0.1:.4f}", "-i", clip(s["clip"])]
    if key:
        fades = ["format=rgba"] + (["fade=t=in:st=0.05:d=0.15:alpha=1"] if first else []) + \
                ([f"fade=t=out:st={dur - 0.25:.3f}:d=0.2:alpha=1"] if last else [])
        cmd += ["-loop", "1", "-t", f"{dur:.4f}", "-i", text_png(key)]
        fc = f"{base}[b];[1:v]{','.join(fades)}[t];[b][t]overlay=0:0[v]"
    else:
        fc = f"{base}[v]"
    run(cmd + ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{dur:.4f}", *ENC, out])
    parts.append(out); t += dur
end_dur = P["endcard"]["beats"] * BEAT; pe = os.path.join(WORK, "seg99_end.mp4")
run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", end_card(), "-t", f"{end_dur:.4f}",
     "-vf", "fps=30,fade=t=in:st=0:d=0.35,setsar=1", *ENC, pe])
parts.append(pe); total = t + end_dur

# 2. 直接拼接 + 合音乐（画面不再转码）
lst = os.path.join(WORK, "list.txt")
with open(lst, "w") as fh:
    for p in parts: fh.write(f"file '{os.path.abspath(p)}'\n")
music = os.path.join(ROOT, P["music"]["file"])
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", str(P["music"]["start"]), "-t", f"{total:.3f}", "-i", music,
     "-filter_complex", f"[1:a]afade=t=in:st=0:d=0.05,afade=t=out:st={total - 1.6:.3f}:d=1.6,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
     "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-t", f"{total:.3f}", OUT])
print(f"完成 {OUT}（{os.path.getsize(OUT) / 1e6:.1f}MB，{total:.1f}秒）\n封面 {COVER}")
