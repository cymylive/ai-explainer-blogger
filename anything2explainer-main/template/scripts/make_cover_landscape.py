# -*- coding: utf-8 -*-
"""生成横版封面（1920x1080，B站/公众号/视频号封面）。

用法：
  python -X utf8 scripts/make_cover_landscape.py <项目根> [--out 输出.png] [--bg 视频帧.png] [--style cover_style.json]

输入：同竖版（title.txt 优先，否则 config.ts 的 VIDEO.title）。
--bg 可选：把视频某一帧当背景（默认纯代码绘制点阵底）。
样式：<项目根>/cover_style.json（可选）覆盖颜色/字体/字号/发光。
输出：<项目根>/renders/<标题>_cover_h.png
便携：字体从 <项目根>/public/fonts 读。
"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
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


def fit(draw, text, cjk, maxw, maxh, start=110, minsize=48):
    size = start
    while size > minsize:
        font = load(cjk, size, True)
        lines = wrap(draw, text, font, maxw)
        lh = int(size * 1.28)
        if len(lines) * lh <= maxh:
            return font, lines, lh
        size -= 6
    font = load(cjk, minsize, True)
    return font, wrap(draw, text, font, maxw), int(minsize * 1.28)


def glow_text(base, cx, cy, text, font, fill, glow, radius=22, alpha=150):
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
    tmax = st.get("title_max_size") or 110
    tmin = st.get("title_min_size") or 48
    sub_size = st.get("sub_size") or 44
    g_radius = st.get("glow_radius") or 22
    g_alpha = st.get("glow_alpha") or 150

    if bg and os.path.exists(bg):
        raw = Image.open(bg).convert("RGB").resize((W, H))
        raw = raw.filter(ImageFilter.GaussianBlur(26))
        img = raw.convert("RGBA")
        img.alpha_composite(Image.new("RGBA", (W, H), (4, 4, 8, 214)))
    else:
        img = Image.new("RGBA", (W, H), bg_color + (255,))
    d = ImageDraw.Draw(img)
    for y in range(52, H, 56):
        for x in range(44, W, 56):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=dot_color)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([W / 2 - 520, H / 2 - 420, W / 2 + 520, H / 2 + 420], fill=glow_color + (40,))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(200)))
    LX = 170
    y = 300
    if kicker:
        kfont = load(cjk if any(ord(c) > 127 for c in kicker) else tech, 44)
        d.text((LX, y), kicker, font=kfont, fill=kicker_color, anchor="lm")
        y += 96
    maxw = W - LX * 2 - 240
    font, lines, lh = fit(d, title, cjk, maxw, 400, tmax, tmin)
    for ln in lines:
        lw = d.textlength(ln, font=font)
        glow_text(img, LX + lw / 2, y + lh / 2, ln, font, main_color, glow_color, g_radius, g_alpha)
        y += lh
    y += 36
    d.rectangle([LX, y, LX + 180, y + 6], fill=divider_color)
    y += 68
    if sub:
        sf = load(cjk, sub_size)
        for ln in wrap(d, sub, sf, maxw):
            d.text((LX, y), ln, font=sf, fill=sub_color, anchor="lm")
            y += int(sub_size * 1.45)
    if brand_text and brand_text.lower() != "none":
        d.text((W - 170, H - 92), brand_text, font=load(wide, 38), fill=brand_color, anchor="rm")
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
        print("用法: python -X utf8 scripts/make_cover_landscape.py <项目根> [--out x.png] [--bg 帧.png] [--style s.json]")
        sys.exit(1)
    root = os.path.abspath(sys.argv[1])
    info = read_title(root)
    if not info:
        print("缺少标题：建 title.txt 或在 config.ts 填 VIDEO.title")
        sys.exit(1)
    st = load_style(root, sys.argv)
    title = info[0]
    sub = info[1] if len(info) > 1 else None
    kicker = info[2] if len(info) > 2 else None
    bg = sys.argv[sys.argv.index("--bg") + 1] if "--bg" in sys.argv else None
    out = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
           else os.path.join(root, "renders", safe_name(title) + "_cover_h.png"))
    print("OK 横版封面: " + make_cover(title, sub, kicker, out, bg, st))
    print("   尺寸: %dx%d%s" % (W, H, "（背景来自视频帧）" if bg else ""))


if __name__ == "__main__":
    main()
