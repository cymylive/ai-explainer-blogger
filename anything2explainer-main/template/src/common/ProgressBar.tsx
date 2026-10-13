import React from 'react';
import {useCurrentFrame} from 'remotion';
import {FONT_HEAVY} from './lib';
import {kf} from './easing';
import {fitSize} from './textfit';
import {TOTAL_FRAMES, CHAPTER_STARTS, SENTENCES} from './timeline';

/**
 * 底部章节进度条（半透明条体 y687–720、n−1 根等宽分隔线、章节名粗黑斜体 24px）。
 * 章节切换帧来自 timeline.ts（tts_build.py 自动生成）。
 *
 * ⚠ 填充必须**分段线性**：分隔线是等宽（1280/NCH），但各章帧长不等——
 *   若填充按总帧数线性推进（旧实现 1280*N/TOTAL），填充跨过分隔线的时刻
 *   会与本章真正开始的时刻错位（章越长错得越多）。现在填充在每段内按该章
 *   真实帧长推进，跨分隔线的时刻 == 该章开始帧，与高亮一致。
 */
export const PROGRESS_ALPHA = 0.52;
export const FILL_RGBA = 'rgba(190,170,250,0.52)';
export const TRACK_RGBA = 'rgba(243,243,243,0.32)';
export const BAR_TOP = 687;
export const BAR_H = 720 - BAR_TOP;
const NCH = Math.max(1, CHAPTER_STARTS.length);
const SEG_W = 1280 / NCH;
export const DIVIDERS = Array.from({length: NCH - 1}, (_, i) => Math.round(((i + 1) * 1280) / NCH)); // n 章等宽分隔
export const DIVIDER_W = 4;
const CENTERS = Array.from({length: NCH}, (_, i) => Math.round(((i + 0.5) * 1280) / NCH));
// 当前章高亮切在**章节卡起始帧**（上一章末句 to+3），不是本章首句帧——否则章节卡宣告新章的 45 帧里进度条还亮着上一章（QC v1 C2 #1；lessons「覆盖层」）
const cardStart = (c: {n: number; from: number}) => {
  const prev = [...SENTENCES].reverse().find((x) => x.chapter < c.n);
  return prev ? prev.to + 3 : c.from;
};
export const CHAPTERS: Array<{text: string; cx: number; from: number}> = CHAPTER_STARTS.map((c, i) => ({text: c.title, cx: CENTERS[i] ?? 640, from: i === 0 ? c.from : cardStart(c)}));
export const CHAPTER_HIGHLIGHT_END = TOTAL_FRAMES + 1;
export const LABEL_SIZE = 24;
export const LABEL_SLOT_W = Math.round(1280 / NCH) - 30; // 章名不得压到分隔线上（英文章名长，自动缩到 17px 兜底）
export const LABEL_SCALE_Y = 0.9;
export const LABEL_TOP = 690.5;
export const LABEL_SKEW = -10;
export const LABEL_DIM_ALPHA = 0.55;

export const currentChapter = (N: number) => {
  if (N >= CHAPTER_HIGHLIGHT_END) return -1;
  let idx = -1;
  for (let i = 0; i < CHAPTERS.length; i++) if (N >= CHAPTERS[i].from) idx = i;
  return idx; // 片头（第一章开始前）无高亮
};

/** 章节边界帧：b[0]=1，b[i]=第 i 章（i≥1）的切换帧，b[NCH]=TOTAL+1。 */
export const CHAPTER_BOUNDS: number[] = [1, ...CHAPTERS.slice(1).map((c) => c.from), TOTAL_FRAMES + 1];

/** 分段线性填充宽度：每章占等宽 SEG_W，段内按该章真实帧长推进，跨分隔线 == 该章开始帧。 */
export const fillWidth = (N: number): number => {
  const n = Math.max(1, Math.min(TOTAL_FRAMES, N));
  let i = NCH - 1;
  for (let k = 0; k < NCH; k++) {
    if (n >= CHAPTER_BOUNDS[k] && n < CHAPTER_BOUNDS[k + 1]) { i = k; break; }
  }
  const span = Math.max(1, CHAPTER_BOUNDS[i + 1] - CHAPTER_BOUNDS[i]);
  const t = Math.max(0, Math.min(1, (n - CHAPTER_BOUNDS[i]) / span));
  return (i + t) * SEG_W;
};

export const ProgressBar: React.FC<{dimKf?: Array<[number, number]>; frame?: number}> = ({dimKf = [], frame}) => {
  const cur = useCurrentFrame();
  const N = frame ?? cur + 1;
  const fillW = fillWidth(N);
  const dim = dimKf.length ? kf(N, dimKf) : 1;
  const ch = currentChapter(N);
  return (
    <div style={{position: 'absolute', left: 0, top: BAR_TOP, width: 1280, height: BAR_H, pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1280, height: BAR_H, transform: 'translateY(0.25px)'}}>
        <div style={{position: 'absolute', left: fillW, top: 0, width: 1280 - fillW, height: BAR_H, background: TRACK_RGBA}} />
        <div style={{position: 'absolute', left: 0, top: 0, width: fillW, height: BAR_H, background: FILL_RGBA}} />
        {dim < 0.999 ? <div style={{position: 'absolute', left: 0, top: 0, width: 1280, height: BAR_H, background: '#000', opacity: 1 - dim}} /> : null}
      </div>
      {DIVIDERS.map((x) => (
        <div key={x} style={{position: 'absolute', left: x - DIVIDER_W / 2, top: 693 - BAR_TOP, width: DIVIDER_W, height: 22, background: 'rgba(255,255,255,0.9)'}} />
      ))}
      {CHAPTERS.map((c, i) => (
        <div
          key={c.text}
          style={{
            position: 'absolute', left: c.cx, top: LABEL_TOP - BAR_TOP,
            transform: `translateX(-50%) skewX(${LABEL_SKEW}deg) scaleY(${LABEL_SCALE_Y})`, transformOrigin: '50% 50%',
            whiteSpace: 'nowrap', fontFamily: FONT_HEAVY, fontWeight: 900, fontSize: fitSize(c.text, LABEL_SLOT_W, LABEL_SIZE, 17), lineHeight: 1,
            color: i === ch ? 'rgba(255,255,255,1)' : `rgba(255,255,255,${LABEL_DIM_ALPHA})`,
          }}
        >
          {c.text}
        </div>
      ))}
    </div>
  );
};
