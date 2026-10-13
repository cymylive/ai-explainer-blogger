# -*- coding: utf-8 -*-
"""生成竖版封面（1080x1920，抖音/小红书通用）。

用法：
  python -X utf8 scripts/make_cover_vertical.py <项目根> [--out 输出.png] [--bg 视频帧.png] [--style cover_style.json]

输入（按优先级）：
  1) <项目根>/title.txt：第1行主标题 / 第2行副标题 / 第3行顶部英文小标
  2) <项目根>/src/config.ts 的 VIDEO.title：主标题取 rest(中文)或 big，kicker 取 en，副标题取 tagline
样式：<项目根>/cover_style.json（可选）覆盖颜色/字体/字号/发光，见 _cover_style.py 字段说明。

输出：<项目根>/renders/<标题>_cover_v.png
便携：字体从 <项目根>/public/fonts 读，不依赖任何绝对路径。
"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _cover_style import load_style, hex_color

FONT_DIR = os.path.join(ROOT, "public", "fonts")
PURPLE = (102, 45, 248)
PURPLE_LIGHT = (161, 117, 241)
WHITE = (255, 255, 255)
GREY = (158, 158, 162)
DOT = (58, 58, 66)
BRAND = "ANYTHING2EXPLAINER"


def load(path, size, bold=False):
    f = ImageFont.truetype(path, size)
    if bold:
        for name in ("Bold", "SemiBold", "Black"):
            try:
                f.set_variation_by_name(name)
                break
            except Exception:
                continue
    return f


def wrap(draw, text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        t = cur + ch
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            if cur and cur[-1] == ch and len(cur) > 1:
                lines.append(cur[:-1])
                cur = cur[-1] + ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, cjk, maxw, maxh, start=132, minsize=58, bold=True):
    size = start
    while size > minsize:
        font = load(cjk, size, bold)
        lines = wrap(draw, text, font, maxw)
        lh = int(size * 1.30)
        if len(lines) * lh <= maxh:
            return font, lines, lh
        size -= 6
    font = load(cjk, minsize, bold)
    return font, wrap(draw, text, font, maxw), int(minsize * 1.30)


def glow_text(base, cx, cy, text, font, fill, glow, radius=24, alpha=150):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((cx, cy), text, font=font, fill=glow + (alpha,), anchor="mm")
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)))
    ImageDraw.Draw(base).text((cx, cy), text, font=font, fill=fill, anchor="mm")


def make_cover(title, sub, kicker, out, bg=None, st=None):
    st = st or {}
    cjk = os.path.join(FONT_DIR, st.get("font_cjk") or "NotoSansSC.ttf")
    wide = os.path.join(FONT_DIR, st.get("font_wide") or "Audiowide-Regular.ttf")
    tech = os.path.join(FONT_DIR, st.get("font_tech") or "Exo2-Italic.ttf")
    main_color = hex_color(st.get("main_color"), WHITE)
    glow_color = hex_color(st.get("glow_color"), PURPLE)
    sub_color = hex_color(st.get("sub_color"), GREY)
    kicker_color = hex_color(st.get("kicker_color"), PURPLE_LIGHT)
    divider_color = hex_color(st.get("divider_color"), PURPLE)
    dot_color = hex_color(st.get("dot_color"), DOT)
    bg_color = hex_color(st.get("bg_color"), (5, 5, 8))
    brand_color = hex_color(st.get("brand_color"), (92, 92, 100))
    brand_text = st.get("brand_text") if st.get("brand_text") else BRAND
    tmax = st.get("title_max_size") or 132
    tmin = st.get("title_min_size") or 58
    sub_size = st.get("sub_size") or 50
    g_radius = st.get("glow_radius") or 24
    g_alpha = st.get("glow_alpha") or 150

    if bg and os.path.exists(bg):
        raw = Image.open(bg).convert("RGB")
        sw, sh = raw.size
        scale = max(W / sw, H / sh)
        raw = raw.resize((int(sw * scale), int(sh * scale)))
        x0 = (raw.size[0] - W) // 2
        y0 = (raw.size[1] - H) // 2
        raw = raw.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(30))
        img = raw.convert("RGBA")
        img.alpha_composite(Image.new("RGBA", (W, H), (4, 4, 8, 216)))
    else:
        img = Image.new("RGBA", (W, H), bg_color + (255,))
    d = ImageDraw.Draw(img)
    for y in range(60, H, 56):
        for x in range(48, W, 56):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=dot_color)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([W / 2 - 430, H / 2 - 430, W / 2 + 430, H / 2 + 430], fill=glow_color + (44,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(190)))
    TOP, BOT = 430, 1400
    y = TOP
    if kicker:
        kf = load(cjk if any(ord(c) > 127 for c in kicker) else tech, 46)
        d.text((W / 2, y), kicker, font=kf, fill=kicker_color, anchor="mm")
        y += 110
    maxw = W - 180
    font, lines, lh = fit(d, title, cjk, maxw, BOT - TOP - 200, tmax, tmin)
    block = len(lines) * lh
    cy = y + max(0, (BOT - TOP - 200 - block) // 2) + block // 2
    ty = cy - block // 2 + lh // 2
    for ln in lines:
        glow_text(img, W / 2, ty, ln, font, main_color, glow_color, g_radius, g_alpha)
        ty += lh
    ly = cy + block // 2 + 46
    d.rectangle([W / 2 - 90, ly, W / 2 + 90, ly + 6], fill=divider_color)
    if sub:
        sf = load(cjk, sub_size)
        sy = ly + 100
        for ln in wrap(d, sub, sf, W - 260):
            d.text((W / 2, sy), ln, font=sf, fill=sub_color, anchor="mm")
            sy += int(sub_size * 1.5)
    d.rectangle([0, 1500, W, 1503], fill=(30, 30, 36))
    if brand_text and brand_text.lower() != "none":
        d.text((W / 2, 1556), brand_text, font=load(wide, 40), fill=brand_color, anchor="mm")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.convert("RGB").save(out, quality=95)
    return out


def read_config_title(root):
    p = os.path.join(root, "src", "config.ts")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"title:s*{([^}]*)}", txt)
    if not m:
        return None
    body = m.group(1)
    def grab(k):
        mm = re.search(k + r":s*'([^']*)'", body)
        return mm.group(1) if mm else ""
    big, rest, en, tag = grab("big"), grab("rest"), grab("en"), grab("tagline")
    main = rest or big
    return [x for x in (main, tag, en) if x] or None


def read_title(root):
    p = os.path.join(root, "title.txt")
    if os.path.exists(p):
        lines = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]
        if lines:
            return lines
    return read_config_title(root)


def safe_name(s, maxlen=60):
    bad = '\\/:*?"<>|\r\n\t'
    out = "".join(("_" if c in bad else c) for c in s)
    out = re.sub(r"\s+", " ", out).strip(" .")
    return (out[:maxlen].rstrip(" .") or "video")


def main():
    if len(sys.argv) < 2:
        print("用法: python -X utf8 scripts/make_cover_vertical.py <项目根> [--out x.png] [--bg 帧.png] [--style s.json]")
        sys.exit(1)
    root = os.path.abspath(sys.argv[1])
    info = read_title(root)
    if not info:
        print("缺少标题：建 title.txt（第1行主标题/第2行副标题/第3行英文小标）或在 config.ts 填 VIDEO.title")
        sys.exit(1)
    st = load_style(root, sys.argv)
    title = info[0]
    sub = info[1] if len(info) > 1 else None
    kicker = info[2] if len(info) > 2 else None
    bg = sys.argv[sys.argv.index("--bg") + 1] if "--bg" in sys.argv else None
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(root, "renders", safe_name(title) + "_cover_v.png")
    print("OK 竖版封面: " + make_cover(title, sub, kicker, out, bg, st))
    print("   尺寸: %dx%d%s" % (W, H, "（背景来自视频帧）" if bg else ""))


if __name__ == "__main__":
    main()
