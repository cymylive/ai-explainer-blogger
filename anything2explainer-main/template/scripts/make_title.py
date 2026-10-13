# -*- coding: utf-8 -*-
"""按主题生成爆款标题候选并打分，写入 title.txt。

用法：
  python -X utf8 scripts/make_title.py <项目根> [--top N] [--print]

输入：<项目根>/topic.txt
  第1行 = 主题（如「向量数据库」）
  第2行起 = 关键事实 / 钩子素材（每行一条，越具体越好，可选）

输出：
  <项目根>/title_candidates.md   全部候选 + 分数（供挑选）
  <项目根>/title.txt              第1行主标题 / 第2行副标题(钩子句) / 第3行英文小标

说明：本地规则引擎，不依赖外部 API，面向科技/知识科普向。
      给的是候选与客观打分，最终建议由 AI/人在候选基础上定稿。
"""
import os, sys, re

# ---------- 打分 ----------
HOOK_WORDS = ["其实", "根本", "竟然", "居然", "没想到", "才知道", "原来", "真相", "秘密", "骗"]
STALE_WORDS = ["震惊", "必看", "速看", "不看后悔", "太可怕", "惊人", "史上最", "赶紧看", "疯狂"]
NUM_RE = re.compile(r"\d")


def score(title, topic, facts):
    n = len(title)
    s, why = 0, []
    if any(w in title for w in HOOK_WORDS):
        s += 3; why.append("认知反转 +3")
    if NUM_RE.search(title):
        s += 2; why.append("含具体数字 +2")
    if title.endswith(("？", "?")) or "为什么" in title or "怎么" in title:
        s += 2; why.append("疑问/悬念 +2")
    if 8 <= n <= 20:
        s += 2; why.append("长度合规(8-20) +2")
    elif n < 6 or n > 28:
        s -= 2; why.append("长度越界 -2")
    if topic and topic in title:
        s += 2; why.append("含主题词 +2")
    if facts:
        best = max((len(set(title) & set(f)) / max(len(set(f)), 1)) for f in facts)
        if best > 0.55:
            s += 2; why.append("贴合已知事实 +2")
    hit = [w for w in STALE_WORDS if w in title]
    if hit:
        s -= 5; why.append("过时词(%s) -5" % "/".join(hit))
    return s, why


# ---------- 候选生成 ----------
def shorten(fact, maxlen=20):
    f = fact.strip().rstrip("。！？!?")
    f = re.sub(r"^(其实|原来|据说|据说，)", "", f)
    return f if len(f) <= maxlen else f[:maxlen].rstrip("，,、") + "…"


def candidates(topic, facts):
    out = []
    f0 = shorten(facts[0]) if facts else ""
    f1 = shorten(facts[1]) if len(facts) > 1 else ""
    nums = [f for f in facts if NUM_RE.search(f)]
    fn = shorten(nums[0]) if nums else ""

    # 不依赖事实的通用模板（科技/知识向，永远可用）
    out.append(topic + "到底是什么？")
    out.append("3 分钟看懂" + topic)
    out.append("为什么" + topic + "这么重要？")
    out.append(topic + "，可能和你想的完全不一样")
    out.append("关于" + topic + "，这几点你得知道")
    out.append("搞懂" + topic + "，看这一条就够了")
    out.append(topic + "背后的原理，其实很简单")
    out.append("你以为的" + topic + "，其实错了")

    # 依赖事实素材的模板
    if f0:
        out.append(topic + "的真相：" + f0)
        out.append("你以为" + topic + "是A，" + f0)
        out.append("为什么" + topic + "？" + f0)
    if fn:
        out.append(topic + "，" + fn + "到底怎么做到的")
        out.append("关于" + topic + "，" + fn)
    if f1:
        out.append("搞懂" + topic + "最反常识的一点：" + f1)

    cleaned = []
    for c in out:
        c = re.sub(r"[，,、：:]\s*$", "", c.strip())
        if 6 <= len(c) <= 30 and c not in cleaned:
            cleaned.append(c)
    return cleaned


def pick_short(topic, long_title):
    """封面用的短标题（≤12 字，缩略图可读）。优先「X是什么」，退化到主题词。"""
    cands = [topic + "是什么", "搞懂" + topic, topic + "的秘密", topic]
    for c in cands:
        if 2 <= len(c) <= 12:
            return c
    return topic[:12]


def read_topic(root):
    p = os.path.join(root, "topic.txt")
    if not os.path.exists(p):
        return None, []
    lines = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]
    if not lines:
        return None, []
    return lines[0], lines[1:]


def safe_name(s, maxlen=60):
    bad = '\\/:*?"<>|\r\n\t'
    out = "".join(("_" if c in bad else c) for c in s)
    out = re.sub(r"\s+", " ", out).strip(" .")
    return (out[:maxlen].rstrip(" .") or "video")


def main():
    if len(sys.argv) < 2:
        print("用法: python -X utf8 scripts/make_title.py <项目根> [--top N] [--print]")
        sys.exit(1)
    root = os.path.abspath(sys.argv[1])
    top = 10
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])
    topic, facts = read_topic(root)
    if not topic:
        print("缺少 topic.txt（第1行主题，第2行起关键事实）")
        sys.exit(1)

    scored = []
    for c in candidates(topic, facts):
        s, why = score(c, topic, facts)
        scored.append((s, c, why))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    # 去重（同分同串只留一条）
    seen, uniq = set(), []
    for s, c, why in scored:
        if c in seen:
            continue
        seen.add(c); uniq.append((s, c, why))

    md = ["# 标题候选（主题：%s）\n" % topic,
          "> 本地规则引擎打分；最终标题建议由 AI/人在候选基础上定稿。\n"]
    for i, (s, c, why) in enumerate(uniq):
        mark = " ⭐" if i == 0 else ""
        md.append("- **%d 分**%s %s  \n  %s" % (s, mark, c, "；".join(why)))
    open(os.path.join(root, "title_candidates.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    best = uniq[0][1] if uniq else topic          # 爆款长标题（发布 / 文件命名）
    short = pick_short(topic, best)                # 封面短标题（缩略图可读）
    # 副标题挑一条"没被主标题用掉"的事实，避免重复
    sub = topic
    for f in facts:
        sf = shorten(f)
        if sf and sf not in best:
            sub = f
            break
    else:
        sub = facts[0] if facts else topic
    # title.txt：封面用（短标题 / 钩子句 / 英文小标）—— 封面脚本读它
    open(os.path.join(root, "title.txt"), "w", encoding="utf-8").write(
        short + "\n" + sub + "\n\n")
    # publish_title.txt：发布 / 文件名用（爆款长标题，一行）
    open(os.path.join(root, "publish_title.txt"), "w", encoding="utf-8").write(best + "\n")

    if "--print" in sys.argv or True:
        print("标题候选（按分数）：")
        for s, c, why in uniq[:top]:
            print("  %2d 分  %s" % (s, c))
        print("")
        print("已写: title.txt（封面短标题=%s）/ publish_title.txt（发布标题=%s）/ title_candidates.md" % (short, best))
        print("可手动改这两个文件定稿：title.txt=封面（短标题/钩子句/英文小标），publish_title.txt=发布+文件名")


if __name__ == "__main__":
    main()
