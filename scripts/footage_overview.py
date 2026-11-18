# 素材总览：每条素材的分辨率/时长 + 每秒一帧缩略图（保持原比例，横竖都能看）
# 用法：python3 scripts/footage_overview.py materials sheets
import glob, json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
from fonts import font

src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
fnt = font("bold", 20); info = []
for video in sorted(glob.glob(f"{src}/*/*.mp4")):
    model = os.path.basename(os.path.dirname(video)); name = os.path.splitext(os.path.basename(video))[0]
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration",
                                   "-of", "json", video], capture_output=True, text=True).stdout or "{}")
    st = (p.get("streams") or [{}])[0]; w, h = st.get("width", 0), st.get("height", 0)
    rot = abs(int(float(((st.get("side_data_list") or [{}])[0]).get("rotation", 0) or 0)))
    if rot in (90, 270): w, h = h, w
    dur = float(p.get("format", {}).get("duration", 0))
    info.append({"model": model, "clip": name + ".mp4", "w": w, "h": h, "dur": round(dur, 1), "orient": "横" if w > h else "竖"})
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=1,scale=-2:240", f"{tmp}/%03d.jpg"], check=True)
        frames = sorted(glob.glob(f"{tmp}/*.jpg"))
        if not frames: continue
        fw, fh = Image.open(frames[0]).size; cols = min(len(frames), 12 if fw < fh else 6); rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * fw, rows * fh), "white"); d = ImageDraw.Draw(sheet)
        for i, f in enumerate(frames):
            x, y = (i % cols) * fw, (i // cols) * fh
            sheet.paste(Image.open(f).resize((fw, fh)), (x, y))
            d.rectangle([x, y, x + 52, y + 26], fill="black"); d.text((x + 5, y + 2), f"{i}s", font=fnt, fill="yellow")
        os.makedirs(f"{out}/{model}", exist_ok=True); sheet.save(f"{out}/{model}/{name}.jpg", quality=72)
    print(model, name, w, h, dur)
json.dump(info, open(f"{out}/footage.json", "w"), ensure_ascii=False, indent=1)
