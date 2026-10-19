# 给每条素材生成“每秒一帧”的缩略图总览，方便挑镜头
# 用法：python3 scripts/contact_sheets.py materials sheets
import glob, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
from fonts import font

src, out = sys.argv[1], sys.argv[2]
fnt = font("bold", 22)
for video in sorted(glob.glob(f"{src}/*/*.mp4")):
    model = os.path.basename(os.path.dirname(video)); name = os.path.splitext(os.path.basename(video))[0]
    dest = f"{out}/{model}/sheet__{name}.jpg"
    if os.path.exists(dest): continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=1,scale=216:384", f"{tmp}/%03d.jpg"], check=True)
        frames = sorted(glob.glob(f"{tmp}/*.jpg"))
        if not frames: continue
        cols = min(len(frames), 10); rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 216, rows * 384), "white"); d = ImageDraw.Draw(sheet)
        for i, f in enumerate(frames):
            x, y = (i % cols) * 216, (i // cols) * 384
            sheet.paste(Image.open(f), (x, y))
            d.rectangle([x, y, x + 64, y + 30], fill="black"); d.text((x + 6, y + 2), f"{i}s", font=fnt, fill="yellow")
        sheet.save(dest, quality=80)
    print("缩略图", dest)
