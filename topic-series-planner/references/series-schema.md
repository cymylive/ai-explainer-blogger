# series.json 结构

```json
{
  "topic": "宇宙科普",
  "series": [
    {
      "name": "火星探索",
      "position": "人类下一个家园，也是最大的谜团",
      "episodes": [
        {"title": "火星上的一天比地球多40分钟，藏着什么秘密", "angle": "时间", "hook": "反常识", "minutes": 5},
        {"title": "人类为什么拼命想去火星？答案让人后背发凉", "angle": "动机", "hook": "疑问", "minutes": 6}
      ]
    }
  ]
}
```

字段说明：
- `topic`（必填）：总主题，用作 xls 文件名与表名。
- `series[]`（必填）：合集数组，每个含：
  - `name`：合集名（≤6 字，名词短语）。
  - `position`：一句话定位（概览表用）。
  - `episodes[]`：集数组，每集含：
    - `title`：标题（必填，全局唯一）。
    - `angle`：选题角度（2-4 字，**同合集内唯一**）。
    - `hook`：钩子类型。
    - `minutes`：时长（1-60 整数）。

## 校验规则（脚本自动执行）
1. 所有 `title` 全局唯一 —— 重复则报错。
2. 同一合集内所有 `angle` 唯一 —— 防止两集撞选题。
3. `minutes` 是 1-60 整数。

## 完整示例
见 `references/example-universe.json`（宇宙科普 8 合集 100 集）。
