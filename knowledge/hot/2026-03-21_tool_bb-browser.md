# bb-browser - 坏孩子浏览器

**来源**: https://x.com/yan5xu/status/2032858943874281782
**作者**: @yan5xu
**发现日期**: 2026-03-21
**优先级**: ⭐⭐⭐ 高

## 核心创新

丧良心但好用的浏览器CLI化工具

## 支持平台（50+命令）

- Reddit
- Twitter
- GitHub
- Hacker News
- 小红书
- 知乎
- B站
- 微博
- 豆瓣
- YouTube
- 持续更新中...

## 技术特点

### 超丧良心实现
- Chrome插件 + CDP直接操控真实浏览器
- **不是无头浏览器**
- **不是偷Cookie**
- **不是模拟请求**
- 直接用你的登录态

### 实现方式
- 直接在浏览器console里跑eval
- 登录态、鉴权自动解决
- 大厂前端很难防

## 使用方式

```bash
bb-browser site reddit
bb-browser site twitter
bb-browser site github
```

## AI友好

```bash
# 埋了guide命令
# 跟Agent说："我需要把XX网站CLI化"
# 它就能帮你做了
```

## 核心优势

1. 绕过最麻烦的登录态
2. 无需处理各种鉴权
3. 真实浏览器环境
4. CLI/MCP双支持

## 热度数据

- 212.6k Views
- 2.7k Likes

## 待实践

- [ ] 安装bb-browser CLI
- [ ] 测试小红书/知乎抓取
- [ ] 探索MCP集成
- [ ] 自定义网站支持

## 关联

- #35 Chrome DevTools MCP
- #38 Chrome一键夺舍指南
