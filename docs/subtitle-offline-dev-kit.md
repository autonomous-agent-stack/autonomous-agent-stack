# Subtitle Offline Dev Kit

`subtitle-offline-dev-kit/` 是仓库里的一个离线字幕开发工具包。

它的定位很简单：

- 不负责主线 agent 编排
- 不负责在线下载字幕
- 不改 routing / fallback / live orchestration
- 只负责把字幕文件拿来离线检查、筛异常、做最小回归

如果你平时是 “vibe coding” 的工作方式，可以把它理解成：

- 一套能直接跑的字幕小工具
- 一套不会影响主线系统的安全实验区
- 一套能帮你快速判断“这个字幕目录大概干不干净”的脚本集合

## 什么时候用

用它的场景主要有 4 个：

1. 你拿到一批 `.vtt` / `.srt`，想先看看有没有明显脏数据
2. 你准备做字幕相关开发，但不想一开始就接进主线 agent
3. 你想从真实字幕目录里挑一些代表性样本，做 fixture 或回归测试
4. 你想把字幕线交给别人接手，需要一个离线、可复现、可测试的小工具包

不该用它的场景：

- 不要把它当主线生产 pipeline
- 不要把它当在线下载器
- 不要把它当路由层或 agent skill 框架本身

## 它能做什么

当前 dev kit 主要提供 3 类能力。

### 1. 基础 contract 检查

把字幕文件统一解析成一个最小 contract，然后标记基础异常：

- `missing_text`
- `end_before_start`
- `out_of_order`

入口脚本：

```bash
python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

这个最适合做：

- “我先看这批字幕能不能被正常解析”
- “我改了清洗逻辑，先确认没有把基础行为改坏”

### 2. 大目录异常扫描

如果你不是只看一个文件，而是想扫一整个字幕目录，用扫描器：

```bash
python subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitles \
  --mode audit
```

扫描器会额外找这类结构问题：

- `duplicate_cue`
- `rapid_repeat`
- `long_cue`
- `large_gap`

它更像“候选发现器”，不是严格的生产判定器。

### 3. fixtures + tests 回归

如果你改了字幕逻辑，先跑这里，不要一上来碰主线：

```bash
pytest -q subtitle-offline-dev-kit/tests
```

这让字幕相关开发可以先在 sidecar 里收口，再决定是否接进主系统。

## 最常用的 3 个命令

### 看内置样本是不是还正常

```bash
python subtitle-offline-dev-kit/scripts/check_subtitle_contract.py
```

### 扫真实目录，做广一点的质量巡检

```bash
python subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitles \
  --mode audit \
  --json /tmp/subtitle-audit.json \
  --markdown /tmp/subtitle-audit.md
```

### 扫真实目录，只保留高信号候选

```bash
python subtitle-offline-dev-kit/scripts/scan_subtitle_anomalies.py \
  --input-dir /path/to/subtitles \
  --mode harvest \
  --json /tmp/subtitle-harvest.json
```

## 和 agent / skill 的关系

当前不需要先给 agent 配新 skill。

最合理的顺序是：

1. 先把它当仓库内置 CLI 工具用起来
2. 确认某个 agent 真的会反复调用这些命令
3. 再考虑做一个很薄的 skill 包装层

也就是说：

- dev kit 是能力本体
- skill 只能是它的调用壳
- 不要反过来把逻辑塞进 skill

## 对后续开发的意义

这个目录的价值，不是“功能很多”，而是边界清楚：

- 字幕实验可以先在这里做
- 脏数据可以先在这里筛
- 回归可以先在这里跑
- 接手者可以不理解整套 agent 系统，也能先把字幕线跑起来

对后续开发最实用的方式是：

1. 先在 `subtitle-offline-dev-kit/` 里验证想法
2. 确认 contract、输入输出和样本稳定
3. 再把必要的部分接回主线

这样不会把“试验中的字幕逻辑”直接污染主系统。

## 相关入口

- Dev kit 概览：[`subtitle-offline-dev-kit/README.md`](../subtitle-offline-dev-kit/README.md)
- Mac 使用与交接：[`subtitle-offline-dev-kit/docs/mac-subtitle-pipeline.md`](../subtitle-offline-dev-kit/docs/mac-subtitle-pipeline.md)
