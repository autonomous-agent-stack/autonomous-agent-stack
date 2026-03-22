# Chrome "一键夺舍" 极客避坑指南

**来源**: https://x.com/xiangxiang103/status/2033710786250739838
**发现日期**: 2026-03-21
**优先级**: ⭐⭐ 中（补充教程）

## 核心更新

Chrome 146官方开启"一键夺舍"开关，AI彻底接管浏览器

## 详细步骤

### 第一步：开启上帝视角
```
chrome://inspect/#remote-debugging
```

### 第二步：勾选开关
☑️ Allow remote debugging for this browser instance

**警告**: 外部应用将有权请求该浏览器的完全控制权

### 第三步：获取监听地址
```
Server running at: 127.0.0.1:9222
```

## 极客方案：chrome-cdp-skill

### 官方包痛点
- 每次执行重复建立连接
- Chrome安全提示疯狂弹窗
- Puppeteer穷举Target超时卡死

### 直连方案优势
1. **静默控制**: 不抢夺物理鼠标焦点
2. **单次授权**: 每个标签页仅需授权一次
3. **秒级响应**: WebSocket直连，百级标签页不卡顿
4. **DOM级精准**: 深入AX Tree，100%精准点击

### 安装命令

**Mac/Linux**:
```bash
npx skills add https://github.com/pasky/chrome-cdp-skill -g --all --copy
```

**Windows** (增强分支):
```bash
npx skills add https://github.com/hanyu0001/chrome-cdp-skill -g --all --copy
```

## 使用示例

```
"帮我打开Gemini，画一张金刚大战哥斯拉的图"
```

## 技术要求

- Node.js 22+
- Chrome 146+

## 安全提示

- 仅限个人学习和本地使用
- 用完立即关闭调试端口
- 禁止非法用途

## 关联资料

- #35 Chrome DevTools MCP
- #36 PageAgent
