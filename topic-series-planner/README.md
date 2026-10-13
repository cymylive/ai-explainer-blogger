# topic-series-planner

给一个**主题**，自动规划成多集合集的短视频选题清单（xlsx）。

## 用法

用户只需给一个主题：

> 给我做一个「历史冷知识」的合集选题清单

Agent 会：
1. 把主题拆成 4-8 个**合集**（每个合集名 ≤6 字，一眼知道讲什么）
2. 每个合集写 10-15 集，每集给：标题、选题角度、钩子类型、时长（分钟）
3. 校验（标题全局唯一 + 同合集角度不重复 + 时长合法）
4. 生成 xlsx 到桌面

## 输出

**<主题>视频合集清单.xlsx**，两个表：
- **<主题>清单**：序号 / 合集主题 / 集数 / 视频标题 / 选题角度 / 钩子类型 / 时长(分钟) / 累计时长
- **合集概览**：合集 / 集数 / 总时长 / 一句话定位

## 文件

| 路径 | 作用 |
|---|---|
| `SKILL.md` | agent 入口：工作流程与规则 |
| `scripts/make_series_xlsx.py` | JSON → xlsx（含去重校验） |
| `references/series-schema.md` | JSON 结构说明 |
| `references/hook-formulas.md` | 钩子公式库 + 选题角度清单 |
| `references/example-universe.json` | 完整示例（宇宙科普 8 合集 100 集） |

## 依赖

- Python：`E:\python\python-V\python3.14\python.exe`（openpyxl 3.1.5）
- 命令行加 `-X utf8`

## 手动调用

```bash
E:\python\python-V\python3.14\python.exe -X utf8 scripts\make_series_xlsx.py series.json --out "C:\Users\cymylive\Desktop\xxx视频合集清单.xlsx"
```

## 与其它 skill 的分工

- **本 skill**：选题规划（一个主题 → 一批成系列的标题清单）
- **douyin-viral-script**：单条视频的脚本/钩子/分镜
- **anything2explainer**：把选定的标题做成实际的讲解视频
