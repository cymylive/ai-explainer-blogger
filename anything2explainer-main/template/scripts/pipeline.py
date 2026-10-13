# -*- coding: utf-8 -*-
"""一条龙编排：给主题 -> 成片（含 BGM）+ 横竖版封面。

用法：
  # 1) 建项目（复制模板、改 slug、写 topic/title、装依赖）
  python -X utf8 scripts/pipeline.py new <目标目录> <slug> "<主题>"
      环境变量 A2E_SHARED_NM 指向已有 node_modules 时用 junction 复用（免 npm install）

  # 2) 内容（narration.txt + 镜头）写完后，一键出片
  python -X utf8 scripts/pipeline.py build <项目> [--no-bgm] [--no-cover] [--draft]

  # 3) 只重出封面
  python -X utf8 scripts/pipeline.py cover <项目>

  # 4) 只出草稿（0.5 分辨率，审片用）
  python -X utf8 scripts/pipeline.py draft <项目>

产物：renders/<爆款标题>_final.mp4（+ _bgm.mp4）、renders/<爆款标题>_cover_v.png / _cover_h.png
环境变量：
  A2E_GPU=1|0         渲染时用 GPU 编码加速（默认 1，安全，实测 +8%）
  A2E_GL=angle        启用 GPU 栅格化（老卡有兼容风险，实测 +7%；不设则软件栅格化）
  A2E_SHARED_NM=<目录>  建项目时 junction 复用已有 node_modules（免 npm install）

注意：解说词 narration.txt 与镜头 src/shots/Gn 需 AI/人写，本脚本不代写内容。
"""
import os, sys, re, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.dirname(HERE)
PY = sys.executable


def find_node_dir():
    env = os.environ.get("NODE_ROOT")
    if env and os.path.isfile(os.path.join(env, "node.exe")):
        return env
    which = shutil.which("node")
    if which:
        return os.path.dirname(which)
    for c in ["D:/NodeJS", "D:/nodejs", "E:/node.js", "C:/Program Files/nodejs"]:
        if os.path.isfile(os.path.join(c, "node.exe")):
            return c
    return None


def env_with_node():
    e = dict(os.environ)
    nd = find_node_dir()
    if nd:
        e["PATH"] = nd + os.pathsep + e.get("PATH", "")
    return e


def read_slug(root):
    cfg = open(os.path.join(root, "src", "config.ts"), encoding="utf-8").read()
    return re.search(r"slug:\s*'([^']+)'", cfg).group(1)


def read_output_name(root, slug):
    """输出文件基名：优先 publish_title.txt（爆款标题），其次 title.txt 第1行，否则 slug。"""
    p = os.path.join(root, "publish_title.txt")
    if not os.path.exists(p):
        p = os.path.join(root, "title.txt")
    if os.path.exists(p):
        lines = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]
        if lines:
            t = lines[0]
            bad = '\\/:*?"<>|\r\n\t'
            t = "".join(("_" if c in bad else c) for c in t)
            t = re.sub(r"\s+", " ", t).strip(" .")
            if t:
                return t[:60].rstrip(" .")
    return slug


def run(args, desc, cwd=None):
    print("")
    print("-" * 56)
    print(">> " + desc)
    print("-" * 56)
    r = subprocess.run(args, env=env_with_node(), cwd=cwd)
    if r.returncode != 0:
        print("失败（退出码 %d）" % r.returncode)
        sys.exit(r.returncode)


def cmd_new(dest, slug, topic):
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.listdir(dest):
        print("目标已存在且非空: " + dest)
        sys.exit(1)
    def ignore(d, names):
        return [n for n in names if n in ("node_modules", "build_full", "build", "renders",
                                          "fin_frames", "stills", "audio", "__pycache__")]
    shutil.copytree(TEMPLATE, dest, ignore=ignore)
    cfg = os.path.join(dest, "src", "config.ts")
    txt = open(cfg, encoding="utf-8").read().replace("slug: 'demo'", "slug: '" + slug + "'")
    open(cfg, "w", encoding="utf-8").write(txt)
    for d in ("public/assets/" + slug, "script", "research", "qc", "renders"):
        os.makedirs(os.path.join(dest, d), exist_ok=True)
    open(os.path.join(dest, "topic.txt"), "w", encoding="utf-8").write(topic + "\n")
    shared = os.environ.get("A2E_SHARED_NM")
    nm = os.path.join(dest, "node_modules")
    if shared and os.path.isdir(shared):
        print("复用共享 node_modules: " + shared)
        subprocess.run(["cmd", "/c", "mklink", "/J", nm, shared], env=env_with_node())
    elif not os.path.isdir(nm):
        print("安装依赖（npm install，走 npmmirror）…")
        subprocess.run(["cmd", "/c", "npm install --registry=https://registry.npmmirror.com"],
                       cwd=dest, env=env_with_node())
    # 生成爆款标题候选 -> title.txt（主标题/钩子句/英文小标）
    run([PY, "-X", "utf8", os.path.join(dest, "scripts", "make_title.py"), dest], "生成爆款标题", cwd=dest)
    print("")
    print("=" * 56)
    print("项目就绪: " + dest)
    print("下一步（AI/人写两份内容）：")
    print("  1) " + os.path.join(dest, "script", "narration.txt"))
    print("  2) " + os.path.join(dest, "src", "shots", "G1", "index.ts") + " 与镜头 .tsx")
    print("  3) title.txt（已生成候选，可手动定稿：主标题/钩子句/英文小标）")
    print("写完后: python -X utf8 scripts/pipeline.py build " + dest)
    print("=" * 56)


def _render(root, slug, base, draft):
    out = "renders/" + base + ".mp4"
    cmd = ["cmd", "/c", "npx remotion render src/index.ts Video " + out + " --codec=h264"]
    cmd[2] += (" --crf=28 --scale=0.5" if draft else " --crf=16")
    # GPU 编码加速（默认开，安全零成本，实测 +8%）：--hardware-acceleration=if-possible
    if os.environ.get("A2E_GPU", "1") != "0":
        cmd[2] += " --hardware-acceleration=if-possible"
    # GPU 栅格化（可选，老卡有兼容风险）：设 A2E_GL=angle 启用，实测 +7%
    gl = os.environ.get("A2E_GL")
    if gl:
        cmd[2] += " --gl=" + gl
    gpu_note = "（GPU编码）" if os.environ.get("A2E_GPU", "1") != "0" else ""
    run(cmd, "渲染" + ("草稿（0.5×）" if draft else "成片") + gpu_note + " -> " + out, cwd=root)


def cmd_build(root, no_bgm, no_cover, draft):
    root = os.path.abspath(root)
    run([PY, "-X", "utf8", os.path.join(root, "scripts", "tts_build.py")], "生成配音 + 时间轴", cwd=root)
    run(["cmd", "/c", "npx tsc --noEmit"], "TypeScript 编译检查", cwd=root)
    slug = read_slug(root)
    # 输出文件用爆款标题命名（title.txt 第 1 行），缺失则回退 slug
    base = read_output_name(root, slug)
    suffix = "_draft" if draft else "_final"
    _render(root, slug, base + suffix, draft)
    if not no_bgm:
        vid = "renders/" + base + suffix + ".mp4"
        out = "renders/" + base + suffix + "_bgm.mp4"
        run([PY, "-X", "utf8", os.path.join(root, "scripts", "mix_bgm.py"), vid, out], "混入 BGM", cwd=root)
    if not no_cover:
        cmd_cover(root)


def cmd_cover(root):
    root = os.path.abspath(root)
    run([PY, "-X", "utf8", os.path.join(root, "scripts", "make_cover_vertical.py"), root], "竖版封面", cwd=root)
    run([PY, "-X", "utf8", os.path.join(root, "scripts", "make_cover_landscape.py"), root], "横版封面", cwd=root)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    cmd = a[0]
    if cmd == "new":
        if len(a) < 4:
            print("用法: pipeline.py new <目标目录> <slug> <主题>")
            sys.exit(1)
        cmd_new(a[1], a[2], a[3])
    elif cmd in ("build", "draft"):
        if len(a) < 2:
            print("用法: pipeline.py " + cmd + " <项目> [--no-bgm] [--no-cover]")
            sys.exit(1)
        cmd_build(a[1], "--no-bgm" in a, "--no-cover" in a, cmd == "draft")
    elif cmd == "cover":
        cmd_cover(a[1])
    else:
        print("未知命令: " + cmd)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
