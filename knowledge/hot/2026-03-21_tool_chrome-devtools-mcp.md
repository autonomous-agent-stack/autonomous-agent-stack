# Chrome DevTools MCP - AI接管浏览器

**来源**: https://x.com/geekshellio/status/2033779082823938138
**官方**: Google Chrome团队
**发现日期**: 2026-03-21
**优先级**: ⭐⭐ 中

## 核心价值

让Claude/Codex直接接管你正在用的浏览器，登录状态、cookie、后台权限全部复用

## 功能特点

### 1. 真实浏览器操作
- 在你眼前的浏览器窗口实时发生
- 复用所有登录状态
- cookie和权限全保留

### 2. 实际应用场景
- Notion同步飞书
- 整理GitHub star
- 查Analytics数据
- 删Twitter帖子
- Instagram数据提取
- Shopify后台分析
- 本地dev页面性能分析

## 设置步骤

### 第一步：开启远程调试
```
Chrome地址栏输入：
chrome://inspect/#remote-debugging
勾选 Allow remote debugging
```

### 第二步：添加MCP工具

**Claude Code:**
```bash
claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest --autoConnect
```

**Codex:**
```bash
codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
```

### 第三步：重启并测试
```bash
# 重启Claude Code/Codex
# 测试连接：
"截图当前页面"
```

## 实战示例

### 1. Instagram数据提取
> "打开我的Instagram Saved列表，筛选所有日本相关Reels，提取地点名称、类别、地址、截图，整理成表格，最后建一个可浏览的HTML网站"

### 2. Twitter管理
> "打开Twitter后台，列出过去7天我发的帖（按点赞排序），删掉点赞<10的，先给我看列表确认"

### 3. Shopify分析
> "打开Shopify后台，进入Analytics→过去24小时数据，截图关键图表，总结Top 3产品、流量来源和异常点"

### 4. 性能优化
> "打开我的本地dev页面，运行performance trace，分析LCP/FCP问题，列出优化建议并帮我改代码，改完再验证一次"

## 优势

- 复用现有登录状态，无需重新认证
- 真实浏览器环境，兼容性好
- 实时可视化操作
- 覆盖80%日常浏览器重复操作

## 注意事项

- 第一次用先测试"截图当前页面"
- 复杂任务先看列表确认
- 确保浏览器保持开启

## 待实践

- [ ] 开启远程调试
- [ ] 安装MCP工具
- [ ] 测试基础功能
- [ ] 实战复杂任务
