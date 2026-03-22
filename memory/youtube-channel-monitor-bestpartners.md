# YouTube频道监控 - 最佳拍档

## ✅ 已订阅

**频道**: 最佳拍档 (@bestpartners)
**URL**: https://youtube.com/@bestpartners
**订阅时间**: 2026-03-22

---

## 📋 监控配置

### **状态文件**
- 配置: `~/.openclaw/workspace/.channel-subscriptions.json`
- 状态: `~/.openclaw/workspace/.youtube-channel-state.json`
- 脚本: `/home/lisa/.openclaw/scripts/check-youtube-channel.sh`

### **心跳任务**
- 频率: 每次心跳
- 动作:
  1. 检查最新视频
  2. 下载字幕（如有）
  3. 整理关键内容
  4. 生成报告

---

## 📊 频道信息

**频道名**: 最佳拍档
**最新视频**: JqFUbl-OVzc
**标题**: 【人工智能】AI时代"人的尺度" | Ivan Zhao访谈 | 700个Agent协同

---

## 🔍 已获取视频列表（前10个）

1. **JqFUbl-OVzc** - AI时代"人的尺度" | Ivan Zhao访谈
2. **aKG7_3bkrvg** - 持续自我提升式AI | 斯坦福杨紫童博士答辩
3. **m9j3pGsXM2Q** - AI时代什么不贬值 | 埃里克霍维茨
4. **IRhhzGAcEjo** - AI五大底层范式
5. **zyRKFw0EO3M** - Are you calling the real API?
6. **J3ozcmiIp8A** - UBI真的能实现么 | Andrew Yang
7. **BGaepdtpJTY** - 英伟达GTC 2026 | 黄仁勋
8. **Ua7DZv0qGHQ** - AI开启算法自我演化 | AlphaEvolve
9. **So9lS8j5bLY** - 谁会首先被AI淘汰 | Anthropic报告

---

## ⚠️ 已知问题

- **SSL错误**: yt-dlp偶发SSL连接问题，会自动重试
- **字幕下载**: 需手动执行（如需要）

---

## 📝 使用说明

### **查看监控报告**
```bash
cat ~/.openclaw/workspace/memory/youtube-bestpartners-*.md
```

### **手动执行监控**
```bash
/home/lisa/.openclaw/scripts/check-youtube-channel.sh
```

### **下载字幕**
```bash
yt-dlp --write-auto-sub --sub-lang zh-Hans --skip-download [VIDEO_URL]
```

---

**订阅状态**: ✅ 活跃
**下次检查**: 下次心跳
