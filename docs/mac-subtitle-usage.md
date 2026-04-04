# Mac Subtitle Usage

这条线只做一件事：在 Mac 上用 `yt-dlp` 抓现成字幕，然后产出一个干净版本的 `.srt` 或 `.txt`。

它不下载视频，不抽音频，也不依赖 `ffmpeg` 或 `Whisper`。

## 适用场景

- Linux 执行面暂时离线
- 只需要抓 YouTube 现成字幕
- 想先把字幕资料同步回仓库，后续再补 Linux 转录能力

## 环境准备

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install yt-dlp
```

## 模块导入

阶段 3 之后，优先走独立导入面，而不是直接依赖 `autoresearch.*` 内部路径：

```python
from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle, run_subtitle_job
```

## 最小用法

```python
from subtitle_offline.contract import SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle

result = fetch_subtitle(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "./data/subtitles",
    output_format=SubtitleOutputFormat.SRT,
)

print(result.status)
print(result.output_path)
```

如果你只要纯文本：

```python
result = fetch_subtitle(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "./data/subtitles",
    output_format=SubtitleOutputFormat.TXT,
)
```

## 离线 fixture 检查

如果你只是想在 Mac 上验证 clean pipeline，不走任何网络请求，直接用本地字幕文件：

```python
from pathlib import Path

from subtitle_offline.contract import SubtitleOutputFormat
from subtitle_offline.service import run_subtitle_job

job = run_subtitle_job(
    Path("tests/fixtures/subtitles/basic-webvtt.vtt"),
    Path("./artifacts/subtitles"),
    output_format=SubtitleOutputFormat.TXT,
)

print(job.to_dict())
```

也可以直接走 CLI：

```bash
source venv/bin/activate
PYTHONPATH=src python scripts/subtitle_cli.py \
  --input tests/fixtures/subtitles/basic-webvtt.vtt \
  --offline \
  --output-dir artifacts/subtitles-check \
  --format txt
```

在线抓取则去掉 `--offline`，把 `--input` 换成 YouTube URL：

```bash
source venv/bin/activate
PYTHONPATH=src python scripts/subtitle_cli.py \
  --input https://www.youtube.com/watch?v=dQw4w9WgXcQ \
  --output-dir artifacts/subtitles-online \
  --format srt
```

## 最小在线 smoke test

如果你要验证真实 `yt-dlp` 在线抓取，可以单独跑 smoke 脚本：

```bash
source venv/bin/activate
PYTHONPATH=src python scripts/subtitle_online_smoke_test.py \
  --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  --output-dir artifacts/subtitles-smoke \
  --format srt \
  --json-out artifacts/subtitles-smoke/result.json
```

这一步会真实访问外网，只建议在你明确要验证端到端时执行。

脚本会在 `metadata` 里附带轻量错误分类：

- `rate_limited`
- `network_ssl`
- `no_subtitle_output`
- `unknown_download_error`

如果想用 pytest 方式跑真实集成测试，显式打开：

```bash
source venv/bin/activate
export RUN_SUBTITLE_ONLINE_SMOKE=1
export SUBTITLE_ONLINE_SMOKE_URL="https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
PYTHONPATH=src python -m pytest -q tests/test_subtitle_online_smoke_integration.py
```

## 极薄 API 路由

如果你希望让这条 Mac-only pipeline 被程序调用，而不是只走 CLI，现在有两个独立端点：

- `POST /api/v1/subtitle/offline`
- `POST /api/v1/subtitle/online`

离线调用示例：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/subtitle/offline \
  -H 'Content-Type: application/json' \
  -d '{
    "input_path": "tests/fixtures/subtitles/basic-webvtt.vtt",
    "output_dir": "artifacts/subtitles-api",
    "output_format": "txt"
  }'
```

在线调用示例：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/subtitle/online \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "output_dir": "artifacts/subtitles-api",
    "output_format": "srt"
  }'
```

## 输出约定

- 原始字幕：`<title>-<id>.<lang>.srt`
- 清理后的 SRT：`<title>-<id>.<lang>_clean.srt`
- 清理后的纯文本：`<title>-<id>.<lang>_clean.txt`

`.srt` 会保留编号和时间戳，只清理多余空白。`.txt` 会去掉编号和时间戳，只保留正文。

## Mac 接管 Linux 离线窗口

推荐分工：

- Mac：临时接管字幕抓取、资料整理、提交 PR
- Linux：恢复后继续承担重任务、长测试、转录 fallback

建议流程：

1. Linux 离线时，不在 Mac 上补 `ffmpeg` / `Whisper`，只跑 subtitle-only。
2. 抓到字幕后，把 `_clean.srt` 或 `_clean.txt` 落到明确目录。
3. 用小 PR 回并，不把 Mac 临时方案和 Linux 执行面逻辑混在一起。
4. Linux 恢复后，如果还需要无字幕视频转录，再单独补 ASR pipeline。
