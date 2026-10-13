# -*- coding: utf-8 -*-
"""把 BGM 混入成片（FFmpeg 后处理，视频流 copy 不重编码）。

混音策略：**全程统一音量**，不做 ducking（人声一出现就压 BGM 会让音量忽高忽低，体验差）。
- 配音轨：默认原样保留（TTS 逐句输出响度本就接近，全程恒定）。可选 `VOICE_LUFS`（如 -16）
  启用**双遍 loudnorm**——先测量整轨响度，再用测量值做**线性增益**（linear=true，不动态调整），
  解决逐句拼接的响度跳动，同时保持"全程统一"。**切勿用单遍 loudnorm**：它是动态的，正是忽高忽低的来源。
- BGM 轨：固定增益（默认比配音低 18 dB），循环铺满全片，去低频轰鸣（highpass 120Hz，
  小音量下更干净）、头 2s 淡入、尾 4s 淡出。全程一个音量，不随人声起伏。
- amix normalize=0：禁止 FFmpeg 自动归一化（否则加入 BGM 会把整体压低、音量忽变，正是要避免的）。

便携定位：ffmpeg 依次找 ①环境变量 FFMPEG ②项目内 runtime/ffmpeg/ ③系统 PATH ④常见安装路径；
BGM 从 项目根/assets/bgm_*.mp3 取。

用法：
  python -X utf8 scripts/mix_bgm.py <视频> [输出] [BGM相对dB] [音乐]
    <音乐> 省略 / random          → 从 assets/bgm_*.mp3 随机选
           human_legacy 等         → assets/bgm_<名>.mp3
           完整路径                → 直接用该文件
环境变量：
  PRESET=normal|sleep|fast    片型预设（见下），显式传 BGM_DB 时被覆盖
  BGM_DB=-18                  BGM 相对配音增益(dB)：-14 明显 / -18 轻（默认）/ -22 很轻 / -26 若有若无
  VOICE_LUFS=off              配音轨响度标准化：off（默认，原样）/ -16（双遍 loudnorm 线性增益，全程统一）
  BGM_PICK=random|human_legacy|<路径>

片型预设（PRESET，仅影响 BGM 音量；配套配音语速见 SKILL.md）：
  normal  标准知识科普 → BGM_DB=-18
  sleep   助眠 / 沉浸   → BGM_DB=-24（BGM 更轻，若有若无）
  fast    快节奏 / 信息流 → BGM_DB=-14（BGM 存在感强）
"""
import subprocess, os, sys, json, re, random, glob, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根
ASSETS = os.path.join(HERE, "assets")

PRESETS = {
    "normal": -18,   # 标准知识科普
    "sleep": -24,    # 助眠 / 沉浸
    "fast": -14,     # 快节奏 / 信息流
}


def find_ffmpeg():
    env = os.environ.get("FFMPEG")
    if env and os.path.isfile(env):
        return env
    for c in (os.path.join(HERE, "runtime", "ffmpeg", "ffmpeg.exe"),
              os.path.join(HERE, "runtime", "ffmpeg", "ffmpeg")):
        if os.path.isfile(c):
            return c
    which = shutil.which("ffmpeg")
    if which:
        return which
    for c in ("C:/ffmpeg/bin/ffmpeg.exe", "C:/Program Files/ffmpeg/bin/ffmpeg.exe"):
        if os.path.isfile(c):
            return c
    return None


def find_ffprobe(ff):
    env = os.environ.get("FFPROBE")
    if env and os.path.isfile(env):
        return env
    for c in (os.path.join(HERE, "runtime", "ffmpeg", "ffprobe.exe"),
              os.path.join(HERE, "runtime", "ffmpeg", "ffprobe")):
        if os.path.isfile(c):
            return c
    which = shutil.which("ffprobe")
    if which:
        return which
    if ff:
        cand = ff.replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.isfile(cand):
            return cand
    return "ffprobe"


def list_bgms():
    """assets/bgm_*.mp3 全部候选。"""
    return sorted(glob.glob(os.path.join(ASSETS, "bgm_*.mp3")))


def pick_bgm(spec=None):
    """spec: None/'random'=随机；短名=assets/bgm_<名>.mp3；路径=直接用。"""
    if spec and spec != "random":
        if os.path.exists(spec):
            return spec
        for cand in (os.path.join(ASSETS, "bgm_" + spec + ".mp3"),
                     os.path.join(ASSETS, spec)):
            if os.path.exists(cand):
                return cand
        print("找不到音乐: " + spec)
        sys.exit(1)
    pool = list_bgms()
    if not pool:
        print("assets/ 下没有 bgm_*.mp3")
        sys.exit(1)
    return random.choice(pool)


FF = find_ffmpeg() or "ffmpeg"
FFPROBE = find_ffprobe(FF)


def probe_duration(video):
    try:
        r = subprocess.run([FFPROBE, "-v", "error",
                            "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return float(r.stdout.strip())
    except Exception:
        return 200.0


def measure_loudnorm(video, target_i):
    """双遍 loudnorm 第一遍：测量整轨响度，返回第二遍要用的 measured_* 参数串。
    解析不到（老 ffmpeg 无 print_format=json）返回 None。"""
    cmd = [FF, "-v", "info", "-i", video, "-vn",
           "-af", "loudnorm=I=" + str(target_i) + ":TP=-1.5:LRA=11:print_format=json",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        pairs = [("input_i", "measured_I"), ("input_tp", "measured_TP"),
                 ("input_lra", "measured_LRA"), ("input_thresh", "measured_thresh"),
                 ("target_offset", "offset")]
        return ":".join(ok + "=" + str(d[ik]) for ik, ok in pairs)
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python -X utf8 scripts/mix_bgm.py <视频> [输出] [BGM相对dB] [音乐]")
        print("  BGM 全程固定音量、比配音低指定 dB，不做忽高忽低的 ducking")
        print("  音乐省略或传 random → 从 assets/bgm_*.mp3 随机选")
        print("  候选: " + ", ".join(os.path.basename(x) for x in list_bgms()))
        print("  片型预设 PRESET=normal(-18)/sleep(-24)/fast(-14)；配音响度统一 VOICE_LUFS=-16（双遍）")
        sys.exit(1)
    video = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(video)[0] + "_bgm.mp4"
    spec = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("BGM_PICK", "random")
    voice_lufs = os.environ.get("VOICE_LUFS", "off")  # 默认不处理配音轨：保持 TTS 原响度，全程恒定

    # BGM 增益优先级：显式 CLI 参数 > 片型预设 > BGM_DB 环境变量 > 默认 -18
    if len(sys.argv) > 3:
        bgm_db = float(sys.argv[3])
    else:
        preset = os.environ.get("PRESET", "").strip().lower()
        if preset and preset in PRESETS:
            bgm_db = float(PRESETS[preset])
        else:
            if preset:
                print("⚠ 未知 PRESET=" + preset + "（可选 " + "/".join(PRESETS) + "），忽略")
            bgm_db = float(os.environ.get("BGM_DB", "-18"))

    music = pick_bgm(spec)
    if not os.path.exists(music):
        print("找不到音乐: " + music)
        sys.exit(1)
    print("BGM: " + os.path.basename(music) + "  固定增益 " + str(bgm_db) + "dB（相对配音）")

    dur = probe_duration(video)
    fade_start = max(0, dur - 4)

    # 配音轨：默认原样；VOICE_LUFS 设值时用双遍 loudnorm（线性增益，全程统一，不动态）
    if voice_lufs == "off":
        voc = "[0:a]anull[voc];"
    else:
        meas = measure_loudnorm(video, voice_lufs)
        if meas:
            # linear=true：用测量值做线性增益，整轨一个增益，避免单遍的动态忽高忽低
            voc = ("[0:a]loudnorm=I=" + str(voice_lufs) + ":TP=-1.5:LRA=11:" + meas +
                   ":linear=true[voc];")
            print("配音响度统一：双遍 loudnorm I=" + str(voice_lufs) + " LUFS（线性增益）")
        else:
            voc = "[0:a]anull[voc];"
            print("⚠ 双遍 loudnorm 测量失败（ffmpeg 可能过旧），配音轨原样保留")

    # BGM 轨：固定增益 + 循环 + 去低频轰鸣 + 头淡入尾淡出
    fc = (voc +
          "[1:a]aloop=loop=-1:size=2e9,highpass=f=120,volume=" + str(bgm_db) + "dB,"
          "afade=t=in:st=0:d=2,afade=t=out:st=" + str(fade_start) + ":d=4[bg];"
          "[voc][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    cmd = [FF, "-y", "-v", "error", "-i", video, "-i", music,
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        print("OK " + out + " " + str(os.path.getsize(out)//1024//1024) + "MB")
    else:
        print("FAIL: " + r.stderr[-400:])
        sys.exit(1)


if __name__ == "__main__":
    main()
