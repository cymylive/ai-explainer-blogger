# -*- coding: utf-8 -*-
"""封面样式配置：读项目根的 cover_style.json（或 --style <json>）覆盖默认值。

所有字段可选，缺省用脚本内默认。颜色支持 "#RRGGBB" 或 [r,g,b]。
0 / 空字符串 表示"不覆盖，用脚本默认"。
"""
import os, json

DEFAULTS = {
    "main_color": "",      # 主标题颜色（默认白）
    "glow_color": "",      # 发光 / 强调色（默认品牌紫 #6630F8）
    "sub_color": "",       # 副标题（钩子句）颜色
    "kicker_color": "",    # 顶部英文小标颜色
    "divider_color": "",   # 分隔线颜色
    "dot_color": "",       # 点阵背景点色
    "bg_color": "",        # 纯色底（无 --bg 时）
    "brand_text": "",      # 底部品牌字（空=不覆盖；设为 "none" 可隐藏）
    "brand_color": "",     # 品牌字颜色
    "font_cjk": "",        # 中文字体文件名（在 public/fonts 下）
    "font_wide": "",       # 宽体展示字体
    "font_tech": "",       # 英文技术字体
    "title_max_size": 0,   # 主标题最大字号（0=脚本默认）
    "title_min_size": 0,   # 主标题最小字号
    "sub_size": 0,         # 副标题字号
    "glow_radius": 0,      # 主标题发光半径
    "glow_alpha": 0,       # 主标题发光透明度 0-255
}


def hex_color(c, default=(255, 255, 255)):
    """'#RRGGBB' / [r,g,b] -> (r,g,b)；解析失败返回 default。"""
    if isinstance(c, (list, tuple)) and len(c) == 3:
        try:
            return tuple(int(x) for x in c)
        except Exception:
            return default
    if isinstance(c, str):
        s = c.strip().lstrip("#")
        if len(s) == 6:
            try:
                return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                pass
    return default


def load_style(root, argv):
    """合并默认 + cover_style.json（项目根或 --style 指定）。"""
    st = dict(DEFAULTS)
    p = os.path.join(root, "cover_style.json")
    if "--style" in argv:
        p = argv[argv.index("--style") + 1]
    if os.path.exists(p):
        try:
            st.update(json.load(open(p, encoding="utf-8")))
        except Exception as e:
            print("[!] cover_style.json 解析失败，用默认样式: " + str(e))
    return st
