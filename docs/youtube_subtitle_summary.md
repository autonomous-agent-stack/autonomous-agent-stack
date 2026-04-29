# YouTube 字幕摘要

## 用法

- `POST /api/v1/youtube/subtitle-summary` 接收一个 YouTube URL 和已经取得的字幕文本。
- 该能力只做本地、确定性的字幕摘要，不猜测视频内容，也不静默退回到通用网页摘要。
- 当前第一块迁移要求调用方显式传入 `subtitle_text`；后续块再接入独立字幕获取流水线。

示例：

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "示例视频",
  "subtitle_text": "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n首先我们介绍这个主题。\n00:00:05.000 --> 00:00:08.000\n最后总结关键结论。",
  "max_key_points": 3
}
```

## 失败行为

- 如果 URL 不是 YouTube URL，结果返回 `summary_status=failed` 和 `error_kind=unsupported_url`。
- 如果未传入字幕文本，结果返回 `summary_status=failed` 和 `error_kind=subtitle_text_required`。
- 如果字幕文本为空或无法提取可用句段，结果返回 `summary_status=failed` 和 `error_kind=empty_subtitle_text`。

# YouTube Subtitle Summary

## Usage

- `POST /api/v1/youtube/subtitle-summary` accepts a YouTube URL and subtitle text that has already been fetched.
- This capability creates a local deterministic subtitle summary only. It does not guess video content or silently fall back to a generic webpage summary.
- This first migration block requires callers to pass `subtitle_text` explicitly; a later block can wire in the independent subtitle-fetching pipeline.

Example:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Example video",
  "subtitle_text": "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nFirst we introduce the topic.\n00:00:05.000 --> 00:00:08.000\nFinally we summarize the key conclusion.",
  "max_key_points": 3
}
```

## Failure Behavior

- If the URL is not a YouTube URL, the result returns `summary_status=failed` and `error_kind=unsupported_url`.
- If subtitle text is missing, the result returns `summary_status=failed` and `error_kind=subtitle_text_required`.
- If subtitle text is empty or no usable caption segment can be extracted, the result returns `summary_status=failed` and `error_kind=empty_subtitle_text`.
