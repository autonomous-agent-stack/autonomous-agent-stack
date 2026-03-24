#!/usr/bin/env python3
"""
X (Twitter) 书签增量读取脚本
"""
import json
import os
from datetime import datetime, timezone

# 配置文件路径
STATE_FILE = "/Users/iCloud_GZ/github_GZ/openclaw-memory/.bookmark-state.json"
REPORT_FILE = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory/bookmark-analysis-{}.md"

def load_state():
    """加载状态文件"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "lastBookmarkId": None,
        "lastCheckTime": None,
        "totalProcessed": 0,
        "newBookmarks": 0,
        "highValue": 0,
        "categories": {}
    }

def save_state(state):
    """保存状态文件"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def analyze_bookmarks(state):
    """
    分析新书签（模拟）

    实际使用时需要：
    1. 使用 X API 获取书签列表
    2. 对比 lastBookmarkId 找出新书签
    3. 分析内容并分类
    """
    # 模拟新书签
    new_bookmarks = [
        {
            "id": "2035631071392587953",
            "text": "🚀 Check out this new AI tool for code generation!",
            "url": "https://example.com/ai-tool",
            "author": "@ai_researcher",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "aiTools",
            "value": "high"
        },
        {
            "id": "2035631071392587954",
            "text": "Understanding attention mechanisms in transformers",
            "url": "https://example.com/attention",
            "author": "@ml_expert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "aiMemory",
            "value": "medium"
        }
    ]

    # 更新状态
    state["newBookmarks"] = len(new_bookmarks)
    state["totalProcessed"] += len(new_bookmarks)
    state["lastCheckTime"] = datetime.now(timezone.utc).isoformat()
    state["lastBookmarkId"] = new_bookmarks[-1]["id"] if new_bookmarks else state["lastBookmarkId"]

    # 更新分类统计
    for bookmark in new_bookmarks:
        category = bookmark.get("category", "others")
        state["categories"][category] = state["categories"].get(category, 0) + 1
        if bookmark.get("value") == "high":
            state["highValue"] += 1

    return new_bookmarks, state

def generate_report(new_bookmarks, state):
    """生成分析报告"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORT_FILE.format(date_str)

    report = f"""# X 书签分析报告 {date_str}

## 概览

- **检查时间**: {state['lastCheckTime']}
- **新书签数量**: {state['newBookmarks']}
- **累计处理**: {state['totalProcessed']} 个书签
- **高价值内容**: {state['highValue']} 个

## 分类统计

| 分类 | 数量 |
|------|------|
"""
    for category, count in state['categories'].items():
        report += f"| {category} | {count} |\n"

    report += "\n## 新书签详情\n\n"

    if new_bookmarks:
        for bookmark in new_bookmarks:
            value_emoji = "🔥" if bookmark.get("value") == "high" else "📝"
            report += f"""
### {value_emoji} 书签 {bookmark['id']}

- **作者**: {bookmark['author']}
- **时间**: {bookmark['timestamp']}
- **分类**: {bookmark.get('category', 'others')}
- **价值**: {bookmark.get('value', 'unknown')}

> {bookmark['text']}

**链接**: {bookmark['url']}

---

"""
    else:
        report += "暂无新书签\n"

    report += f"""
## 建议

- {state['highValue']} 个高价值书签需要深度分析
- {'aiTools' in state['categories'] and state['categories']['aiTools'] > 0 and 'AI 工具书签增多，建议更新工具清单' or ''}
- 关注 @ai_researcher 等关键账号的新推文

---

**报告生成时间**: {datetime.now().isoformat()}
"""

    with open(report_path, 'w') as f:
        f.write(report)

    return report_path

def main():
    print("🔍 开始检查 X 书签...")

    # 加载状态
    state = load_state()
    print(f"📊 上次检查: {state.get('lastCheckTime', '从未')}")
    print(f"📊 已处理: {state['totalProcessed']} 个书签")

    # 分析新书签
    new_bookmarks, updated_state = analyze_bookmarks(state)

    # 生成报告
    report_path = generate_report(new_bookmarks, updated_state)

    # 保存状态
    save_state(updated_state)

    print(f"✅ 检查完成!")
    print(f"📝 新书签: {updated_state['newBookmarks']} 个")
    print(f"📄 报告: {report_path}")

    # 显示高价值书签
    high_value = [b for b in new_bookmarks if b.get("value") == "high"]
    if high_value:
        print(f"\n🔥 高价值书签 ({len(high_value)} 个):")
        for bookmark in high_value:
            print(f"  - {bookmark['text'][:60]}...")

if __name__ == "__main__":
    main()
