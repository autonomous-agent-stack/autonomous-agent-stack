# Voice Agent 生态研究

**日期**: 2026-03-23
**来源**: GitHub Search

## 🔥 热门项目

### 框架/平台

| Stars | 名称 | 说明 |
|-------|------|------|
| 4.6k | [speech-to-speech](https://github.com/huggingface/speech-to-speech) | HuggingFace 本地语音 Agent |
| 2.5k | [openai-agents-js](https://github.com/openai/openai-agents-js) | OpenAI 官方，支持 voice agents |
| 1k | [AVA-AI-Voice-Agent](https://github.com/hkjarral/AVA-AI-Voice-Agent-for-Asterisk) | Asterisk/FreePBX 集成 |
| 552 | [echokit_server](https://github.com/second-state/echokit_server) | 开源语音 Agent 平台 |
| 432 | [react-voice-agent](https://github.com/langchain-ai/react-voice-agent) | LangChain 语音 Agent |
| 268 | [dograh](https://github.com/dograh-hq/dograh) | 开源语音 Agent 平台 |
| 315 | [macos-local-voice-agents](https://github.com/kwindla/macos-local-voice-agents) | macOS 本地运行 |

### 示例/教程

| Stars | 名称 | 说明 |
|-------|------|------|
| 252 | [openai-voice-agent-sdk-sample](https://github.com/openai/openai-voice-agent-sdk-sample) | OpenAI Voice SDK 示例 |
| 149 | [ten-days-of-voice-agents-2025](https://github.com/murf-ai/ten-days-of-voice-agents-2025) | 10 天语音 Agent 教程 |

## 🏗️ 架构

### 基础流程

```
语音输入 (STT) → LLM 处理 → 语音输出 (TTS)
     ↑                            ↓
     ←←←←←← 全双工通信 ←←←←←←←←←←
```

### Realtime API 架构

```
┌──────────────────────────────────┐
│        Client (Browser)          │
│  ┌────────────────────────────┐  │
│  │  WebSocket Connection      │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │  Audio Stream (Opus)       │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
           ↓ ↑ WebSocket
┌──────────────────────────────────┐
│      OpenAI Realtime API         │
│  ┌────────────────────────────┐  │
│  │  Speech-to-Speech Model    │  │
│  │  (GPT-4o-realtime)         │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### 本地方案

```
Whisper (STT) → LLM → TTS (Piper/Coqui)
     ↑                       ↓
     ←←← 本地音频流 ←←←←←←←←←
```

## 🎙️ 技术栈

### STT (语音识别)

| 工具 | 延迟 | 质量 | 成本 |
|------|------|------|------|
| OpenAI Whisper | 中 | 高 | API |
| Whisper.cpp | 低 | 高 | 本地 |
| Deepgram | 极低 | 高 | API |
| Vosk | 低 | 中 | 本地 |

### TTS (语音合成)

| 工具 | 延迟 | 质量 | 成本 |
|------|------|------|------|
| OpenAI TTS | 中 | 高 | API |
| ElevenLabs | 中 | 极高 | API |
| Piper | 极低 | 中 | 本地 |
| Coqui TTS | 低 | 高 | 本地 |

### VAD (语音活动检测)

- Silero VAD
- WebRTC VAD
- RNNoise

## 💡 洞察

1. **Realtime API 是趋势** — OpenAI/Gemini 都支持
2. **本地语音 Agent** — HuggingFace 4.6k stars
3. **电话系统集成** — Asterisk/FreePBX 集成
4. **全双工通信** — 实时双向音频流
5. **低延迟是关键** — VAD + 流式处理

## 📊 对比

| 方案 | 延迟 | 成本 | 隐私 |
|------|------|------|------|
| OpenAI Realtime | ~300ms | 高 | 云端 |
| 本地 Whisper + TTS | ~1s | 低 | 本地 |
| Deepgram + ElevenLabs | ~200ms | 高 | 云端 |

## 🔧 实践建议

1. **生产环境** → Realtime API
2. **隐私敏感** → 本地方案
3. **电话系统** → Asterisk + AVA
4. **快速原型** → LangChain react-voice-agent
5. **高质量 TTS** → ElevenLabs

## 🔗 待研究

- [ ] HuggingFace speech-to-speech 架构
- [ ] OpenAI Realtime API 实现细节
- [ ] VoltAgent 的 Voice 支持
- [ ] 低延迟本地方案优化
