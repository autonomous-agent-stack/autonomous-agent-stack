#!/usr/bin/env python3
"""
GitHub Issue SLA Monitor
监控 GitHub Issue 的 SLA（服务级别协议）合规性

功能:
- 监控 Issue 响应时间
- 检测 SLA 违规
- 自动发送告警
- 生成 SLA 报告

使用:
    python issue-sla-monitor.py owner/repo [options]

示例:
    python issue-sla-monitor.py owner/repo --sla-config sla.json --slack-webhook $SLACK_WEBHOOK
    python issue-sla-monitor.py owner/repo --report --output sla-report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from github import Github
except ImportError:
    print("错误: 需要安装 PyGithub")
    print("安装: pip install PyGithub")
    sys.exit(1)


class SLAConfig:
    """SLA 配置"""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            config = json.load(f)

        # SLA 时间（小时）
        self.response_sla = config.get("response_sla", {})
        self.resolution_sla = config.get("resolution_sla", {})

        # 优先级标签前缀
        self.priority_label_prefix = config.get("priority_label_prefix", "priority:")

        # 告警配置
        self.alert_enabled = config.get("alert_enabled", True)
        self.alert_comment = config.get("alert_comment", True)


class SLAMonitor:
    """SLA 监控器"""

    def __init__(self, token: str, sla_config: SLAConfig):
        self.github = Github(token)
        self.config = sla_config

    def check_repo_sla(self, repo_name: str) -> Dict:
        """检查仓库的 SLA 合规性"""
        repo = self.github.get_repo(repo_name)

        # 获取所有开放的 Issues
        open_issues = repo.get_issues(state='open')

        violations = []
        compliant = []

        for issue in open_issues:
            if issue.pull_request:
                continue  # 跳过 PR

            result = self._check_issue_sla(issue)

            if result["status"] == "violation":
                violations.append(result)
            else:
                compliant.append(result)

        # 生成报告
        total = len(violations) + len(compliant)
        violation_rate = len(violations) / total * 100 if total > 0 else 0

        return {
            "repository": repo_name,
            "total_issues": total,
            "violations": len(violations),
            "compliant": len(compliant),
            "violation_rate": violation_rate,
            "violation_details": violations,
            "timestamp": datetime.now().isoformat()
        }

    def _check_issue_sla(self, issue) -> Dict:
        """检查单个 Issue 的 SLA"""
        created_at = issue.created_at
        now = datetime.now()

        # 计算已用时间（小时）
        hours_since_creation = (now - created_at).total_seconds() / 3600

        # 获取优先级
        priority = self._get_issue_priority(issue)

        # 获取 SLA 限制
        response_sla = self.config.response_sla.get(priority, 24)
        resolution_sla = self.config.resolution_sla.get(priority, 72)

        # 检查响应 SLA（是否已分配）
        response_violation = None
        if not issue.assignees or len(list(issue.assignees)) == 0:
            if hours_since_creation > response_sla:
                response_violation = {
                    "type": "response",
                    "sla_hours": response_sla,
                    "actual_hours": hours_since_creation,
                    "overdue_by": hours_since_creation - response_sla
                }

        # 检查解决 SLA（是否仍开放）
        resolution_violation = None
        if issue.state == "open":
            if hours_since_creation > resolution_sla:
                resolution_violation = {
                    "type": "resolution",
                    "sla_hours": resolution_sla,
                    "actual_hours": hours_since_creation,
                    "overdue_by": hours_since_creation - resolution_sla
                }

        # 判断状态
        status = "compliant"
        violations_list = []

        if response_violation:
            violations_list.append(response_violation)
            status = "violation"

        if resolution_violation:
            violations_list.append(resolution_violation)
            status = "violation"

        return {
            "issue_number": issue.number,
            "title": issue.title,
            "priority": priority,
            "status": status,
            "hours_since_creation": hours_since_creation,
            "created_at": created_at.isoformat(),
            "assignees": [a.login for a in issue.assignees],
            "violations": violations_list,
            "url": issue.html_url
        }

    def _get_issue_priority(self, issue) -> str:
        """获取 Issue 优先级"""
        for label in issue.labels:
            if label.name.startswith(self.config.priority_label_prefix):
                return label.name
        return "priority:medium"  # 默认

    def send_sla_alert(self, repo_name: str, violation: Dict):
        """发送 SLA 违规告警"""
        issue = self.github.get_repo(repo_name).get_issue(violation["issue_number"])

        # 构建告警消息
        message = f"## ⚠️ SLA 违规警报\n\n"

        for v in violation["violations"]:
            sla_type = "响应" if v["type"] == "response" else "解决"
            message += f"**{sla_type} SLA 已超时**\n\n"
            message += f"- **SLA**: {v['sla_hours']} 小时\n"
            message += f"- **实际**: {v['actual_hours']:.1f} 小时\n"
            message += f"- **超时**: {v['overdue_by']:.1f} 小时\n\n"

        message += f"@maintainers 请立即处理此 Issue！\n\n"
        message += f"---\n"
        message += f"*由 SLA Monitor 自动检测*"

        # 添加评论
        if self.config.alert_comment:
            issue.create_comment(message)

        # 添加标签
        issue.add_to_labels("sla-violation")

        print(f"✅ 已发送 SLA 告警: Issue #{violation['issue_number']}")

    def generate_sla_report(self, repo_name: str) -> str:
        """生成 SLA 报告"""
        result = self.check_repo_sla(repo_name)

        report = f"# SLA 合规性报告\n\n"
        report += f"**仓库**: {repo_name}\n"
        report += f"**生成时间**: {result['timestamp']}\n"
        report += f"\n---\n\n"

        # 总览
        report += "## 📊 总览\n\n"
        report += f"| 指标 | 数值 |\n"
        report += f"|------|------|\n"
        report += f"| 总 Issues | {result['total_issues']} |\n"
        report += f"| 违规 | {result['violations']} |\n"
        report += f"| 合规 | {result['compliant']} |\n"
        report += f"| 违规率 | {result['violation_rate']:.1f}% |\n"
        report += "\n"

        # 违规详情
        if result['violation_details']:
            report += "## ⚠️ SLA 违规详情\n\n"

            for v in result['violation_details']:
                report += f"### Issue #{v['issue_number']}: {v['title']}\n\n"
                report += f"- **优先级**: {v['priority']}\n"
                report += f"- **创建时间**: {v['created_at']}\n"
                report += f"- **已用时间**: {v['hours_since_creation']:.1f} 小时\n"
                report += f"- **负责人**: {', '.join(v['assignees']) if v['assignees'] else '未分配'}\n"
                report += f"- **链接**: {v['url']}\n\n"

                for violation in v['violations']:
                    sla_type = "响应" if violation['type'] == "response" else "解决"
                    report += f"  - **{sla_type} SLA**: {violation['sla_hours']}h, "
                    report += f"实际: {violation['actual_hours']:.1f}h, "
                    report += f"超时: {violation['overdue_by']:.1f}h\n"

                report += "\n"
        else:
            report += "## ✅ 无 SLA 违规\n\n"
            report += "所有 Issues 都符合 SLA 要求！\n\n"

        return report


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Issue SLA Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查 SLA 并发送告警
  python issue-sla-monitor.py owner/repo --sla-config sla.json

  # 生成报告
  python issue-sla-monitor.py owner/repo --sla-config sla.json --report --output sla-report.md

  # 仅监控不发送告警
  python issue-sla-monitor.py owner/repo --sla-config sla.json --dry-run
        """
    )

    parser.add_argument("repo", help="仓库 (owner/repo)")
    parser.add_argument("--sla-config", required=True, help="SLA 配置文件 (JSON)")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--output", help="输出文件")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    parser.add_argument("--token", help="GitHub Token (或使用 GITHUB_TOKEN 环境变量)")

    args = parser.parse_args()

    # 获取 Token
    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token:
        print("错误: 需要提供 GitHub Token")
        print("使用 --token 参数或设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)

    # 加载 SLA 配置
    sla_config = SLAConfig(args.sla_config)

    # 创建监控器
    monitor = SLAMonitor(token, sla_config)

    if args.report:
        # 生成报告
        print(f"📊 生成 SLA 报告...")
        report = monitor.generate_sla_report(args.repo)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"✅ 报告已保存到: {args.output}")
        else:
            print(report)
    else:
        # 监控并告警
        print(f"🔍 监控仓库: {args.repo}")

        result = monitor.check_repo_sla(args.repo)

        print(f"\n📊 总览:")
        print(f"  总 Issues: {result['total_issues']}")
        print(f"  违规: {result['violations']}")
        print(f"  合规: {result['compliant']}")
        print(f"  违规率: {result['violation_rate']:.1f}%")

        if not args.dry_run:
            # 发送告警
            for violation in result['violation_details']:
                monitor.send_sla_alert(args.repo, violation)
        else:
            print("\n[DRY RUN] 未实际发送告警")


if __name__ == "__main__":
    main()
