# 字体查找：GitHub 云端（apt 安装 fonts-noto-cjk）和本地服务器路径不同
import glob
from PIL import ImageFont

CANDIDATES = {
    "bold": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "medium": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Medium.ttc",
               "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}

def font(weight, size):
    for p in CANDIDATES[weight] + glob.glob("/usr/share/fonts/**/*.tt[fc]", recursive=True):
        try: return ImageFont.truetype(p, size)
        except OSError: continue
    return ImageFont.load_default()
