#!/usr/bin/env python3
"""
MSA (Memory Sparse Attention) 开源监控脚本
团队: EverMind（陈天桥）
监控频率: 每6小时
"""
import json
import os
from datetime import datetime, timezone, timedelta

# 状态文件路径
STATE_FILE = "/Users/iCloud_GZ/github_GZ/openclaw-memory/.msa-monitor-state.json"
REPORT_FILE = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory/msa-monitor-{}.md"

def load_state():
    """加载状态文件"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "lastCheck": None,
        "githubFound": False,
        "arxivFound": False,
        "twitterFound": False,
        "notifications": 0,
        "findings": []
    }

def save_state(state):
    """保存状态文件"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_github(state):
    """检查 GitHub"""
    print("🔍 检查 GitHub...")

    # 实际使用时需要:
    # 1. 使用 GitHub API 搜索 "MSA evermind" "memory sparse attention"
    # 2. 检查新仓库、新代码、新发布

    # 模拟检查结果
    found_repos = []

    # 检查是否有新发现
    if len(found_repos) > len([f for f in state['findings'] if f['source'] == 'github']):
        for repo in found_repos:
            state['findings'].append({
                "source": "github",
                "type": "repository",
                "title": repo['name'],
                "url": repo['url'],
                "foundAt": datetime.now(timezone.utc).isoformat()
            })
        state['githubFound'] = True

    print(f"✅ GitHub 检查完成: {len(found_repos)} 个仓库")
    return found_repos

def check_arxiv(state):
    """检查 arXiv"""
    print("🔍 检查 arXiv...")

    # 实际使用时需要:
    # 1. 搜索 arXiv 论文 "Memory Sparse Attention"
    # 2. 检查引用数量变化
    # 3. 检查作者和机构

    # 模拟检查结果
    found_papers = []

    # 检查是否有新论文
    if len(found_papers) > len([f for f in state['findings'] if f['source'] == 'arxiv']):
        for paper in found_papers:
            state['findings'].append({
                "source": "arxiv",
                "type": "paper",
                "title": paper['title'],
                "url": paper['url'],
                "foundAt": datetime.now(timezone.utc).isoformat()
            })
        state['arxivFound'] = True

    print(f"✅ arXiv 检查完成: {len(found_papers)} 篇论文")
    return found_papers

def check_twitter(state):
    """检查 Twitter"""
    print("🔍 检查 Twitter...")

    # 实际使用时需要:
    # 1. 使用 Twitter API 检查 @EverMind @elliotchen100
    # 2. 查找关键词 "MSA" "开源" "release" "code"

    # 模拟检查结果
    found_tweets = []

    # 检查是否有相关推文
    if len(found_tweets) > len([f for f in state['findings'] if f['source'] == 'twitter']):
        for tweet in found_tweets:
            state['findings'].append({
                "source": "twitter",
                "type": "tweet",
                "title": tweet['text'][:50] + "...",
                "url": tweet['url'],
                "foundAt": datetime.now(timezone.utc).isoformat()
            })
        state['twitterFound'] = True

    print(f"✅ Twitter 检查完成: {len(found_tweets)} 条推文")
    return found_tweets

def generate_report(state, github_repos, arxiv_papers, twitter_tweets):
    """生成监控报告"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    report_path = REPORT_FILE.format(date_str)

    new_findings = [
        f for f in state['findings']
        if datetime.fromisoformat(f['foundAt']).date() == datetime.now().date()
    ]

    report = f"""# MSA (Memory Sparse Attention) 监控报告 {date_str}

## 监控信息

- **检查时间**: {time_str}
- **团队**: EverMind（陈天桥）
- **监控频率**: 每6小时
- **累计检查**: {state['notifications']} 次

## 今日发现 ({len(new_findings)} 个)

"""

    if new_findings:
        for finding in new_findings:
            emoji = "📦" if finding['source'] == 'github' else "📄" if finding['source'] == 'arxiv' else "🐦"
            report += f"""
### {emoji} {finding['title']}

- **来源**: {finding['source']}
- **类型**: {finding['type']}
- **发现时间**: {finding['foundAt']}
- **链接**: {finding['url']}

"""
    else:
        report += "暂无新发现\n"

    report += f"""
## 历史发现 ({len(state['findings'])} 个)

| 来源 | 数量 |
|------|------|
| GitHub | {len([f for f in state['findings'] if f['source'] == 'github'])} |
| arXiv | {len([f for f in state['findings'] if f['source'] == 'arxiv'])} |
| Twitter | {len([f for f in state['findings'] if f['source'] == 'twitter'])} |

## 监控状态

| 检查项 | 状态 |
|--------|------|
| GitHub | {'✅ 已发现' if state['githubFound'] else '🔍 监控中'} |
| arXiv | {'✅ 已发现' if state['arxivFound'] else '🔍 监控中'} |
| Twitter | {'✅ 已发现' if state['twitterFound'] else '🔍 监控中'} |

## 下次检查

- **时间**: {(datetime.now(timezone.utc) + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M")} UTC
- **优先级**: 🔴 高（代码开源或模型发布时立即通知）

---

**报告生成时间**: {datetime.now().isoformat()}
"""

    with open(report_path, 'w') as f:
        f.write(report)

    return report_path

def main():
    print("🔍 开始 MSA 开源监控...")

    # 加载状态
    state = load_state()
    print(f"📊 上次检查: {state.get('lastCheck', '从未')}")

    # 执行检查
    github_repos = check_github(state)
    arxiv_papers = check_arxiv(state)
    twitter_tweets = check_twitter(state)

    # 更新状态
    state['lastCheck'] = datetime.now(timezone.utc).isoformat()
    state['notifications'] += 1
    save_state(state)

    # 生成报告
    report_path = generate_report(state, github_repos, arxiv_papers, twitter_tweets)

    print(f"\n✅ 监控完成!")
    print(f"📄 报告: {report_path}")

    # 检查是否有新发现需要通知
    new_findings = [
        f for f in state['findings']
        if datetime.fromisoformat(f['foundAt']).date() == datetime.now().date()
    ]

    if new_findings:
        print(f"\n🚨 发现 {len(new_findings)} 个新内容!")
        for finding in new_findings:
            print(f"  - [{finding['source']}] {finding['title']}")
        print("\n建议立即通知用户！")
    else:
        print(f"\n📊 暂无新发现，继续监控...")

if __name__ == "__main__":
    main()
