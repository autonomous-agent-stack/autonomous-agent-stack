#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI + RPA 快速开始示例
展示如何使用自然语言生成 RPA 流程
"""

import json
from pathlib import Path

# 假设我们已经有了相关的模块（实际使用时需要实现或导入）
# from src.nl_parser import NLToRPAConverter
# from src.rpa_executor import FlowExecutor
# from src.optimizer import FlowOptimizer


def example_1_simple_automation():
    """示例 1：简单的自动化任务"""
    print("\n" + "="*60)
    print("示例 1：简单的自动化任务")
    print("="*60)

    user_input = "每天早上9点，打开 https://example.com，下载报表，保存到桌面"
    print(f"\n用户需求: {user_input}")

    # 模拟 AI 转换结果
    result = {
        "status": "success",
        "domain": "data_collection",
        "intent": "automate_recurring",
        "flow": {
            "flow_name": "网站报表下载自动化",
            "version": "1.0",
            "variables": {
                "URL": {"type": "string", "value": "https://example.com"},
                "output_path": {"type": "string", "value": "~/Desktop/report.xlsx"}
            },
            "steps": [
                {
                    "step_id": 1,
                    "action": "open_browser",
                    "description": "打开网站",
                    "params": {"url": "https://example.com"}
                },
                {
                    "step_id": 2,
                    "action": "download_report",
                    "description": "下载报表",
                    "params": {"output_path": "~/Desktop/report.xlsx"}
                }
            ]
        }
    }

    print("\n生成的流程:")
    print(f"  流程名称: {result['flow']['flow_name']}")
    print(f"  步骤数量: {len(result['flow']['steps'])}")
    print("\n步骤列表:")
    for step in result['flow']['steps']:
        print(f"  {step['step_id']}. {step['description']} ({step['action']})")

    return result


def example_2_complex_workflow():
    """示例 2：复杂的工作流"""
    print("\n" + "="*60)
    print("示例 2：复杂的工作流")
    print("="*60)

    user_input = """
    读取 sales.xlsx 文件，筛选金额大于1000的订单，
    按地区分组统计，生成饼图，保存为 report.html，
    完成后发送邮件给团队
    """
    print(f"\n用户需求: {user_input.strip()}")

    # 模拟 AI 转换结果
    result = {
        "status": "success",
        "domain": "data_processing",
        "intent": "transform_data",
        "flow": {
            "flow_name": "销售数据分析自动化",
            "version": "1.0",
            "variables": {
                "input_file": {"type": "string", "value": "sales.xlsx"},
                "output_file": {"type": "string", "value": "report.html"},
                "team_email": {"type": "string", "value": "team@company.com"}
            },
            "steps": [
                {
                    "step_id": 1,
                    "action": "read_excel",
                    "description": "读取 Excel 文件",
                    "params": {"path": "sales.xlsx"}
                },
                {
                    "step_id": 2,
                    "action": "filter_data",
                    "description": "筛选金额大于1000的订单",
                    "params": {"condition": "amount > 1000"}
                },
                {
                    "step_id": 3,
                    "action": "group_data",
                    "description": "按地区分组统计",
                    "params": {"group_by": "region"}
                },
                {
                    "step_id": 4,
                    "action": "create_chart",
                    "description": "生成饼图",
                    "params": {"chart_type": "pie"}
                },
                {
                    "step_id": 5,
                    "action": "save_html",
                    "description": "保存为 HTML 文件",
                    "params": {"path": "report.html"}
                },
                {
                    "step_id": 6,
                    "action": "send_email",
                    "description": "发送邮件",
                    "params": {
                        "to": "team@company.com",
                        "subject": "销售分析报告",
                        "attachments": ["report.html"]
                    }
                }
            ]
        }
    }

    print("\n生成的流程:")
    print(f"  流程名称: {result['flow']['flow_name']}")
    print(f"  步骤数量: {len(result['flow']['steps'])}")
    print("\n步骤列表:")
    for step in result['flow']['steps']:
        print(f"  {step['step_id']}. {step['description']}")

    return result


def example_3_conditional_logic():
    """示例 3：条件判断逻辑"""
    print("\n" + "="*60)
    print("示例 3：条件判断逻辑")
    print("="*60)

    user_input = "监控网站 https://example.com，如果出现'系统维护'字样，发送警报邮件"
    print(f"\n用户需求: {user_input}")

    # 模拟 AI 转换结果
    result = {
        "status": "success",
        "domain": "web_testing",
        "intent": "monitor_changes",
        "flow": {
            "flow_name": "网站监控自动化",
            "version": "1.0",
            "variables": {
                "target_url": {"type": "string", "value": "https://example.com"},
                "alert_email": {"type": "string", "value": "admin@company.com"}
            },
            "steps": [
                {
                    "step_id": 1,
                    "action": "open_browser",
                    "description": "打开网站",
                    "params": {"url": "https://example.com"}
                },
                {
                    "step_id": 2,
                    "action": "extract_text",
                    "description": "提取页面文本",
                    "params": {"selector": "body"}
                },
                {
                    "step_id": 3,
                    "action": "condition",
                    "description": "判断是否维护",
                    "params": {
                        "condition": "if '系统维护' in extracted_text"
                    }
                },
                {
                    "step_id": 4,
                    "action": "send_alert",
                    "description": "发送警报邮件",
                    "params": {
                        "to": "admin@company.com",
                        "subject": "网站维护警报"
                    }
                },
                {
                    "step_id": 5,
                    "action": "wait",
                    "description": "等待10分钟",
                    "params": {"duration": 600}
                },
                {
                    "step_id": 6,
                    "action": "loop",
                    "description": "循环监控",
                    "params": {"count": "infinite"}
                }
            ]
        }
    }

    print("\n生成的流程:")
    print(f"  流程名称: {result['flow']['flow_name']}")
    print(f"  步骤数量: {len(result['flow']['steps'])}")
    print("\n步骤列表:")
    for step in result['flow']['steps']:
        print(f"  {step['step_id']}. {step['description']}")

    return result


def example_4_performance_optimization():
    """示例 4：性能优化"""
    print("\n" + "="*60)
    print("示例 4：性能优化")
    print("="*60)

    print("\n执行日志分析...")

    # 模拟执行日志
    execution_logs = [
        {
            "flow_name": "网站报表下载自动化",
            "started_at": "2026-03-24T09:00:00+08:00",
            "finished_at": "2026-03-24T09:00:20+08:00",
            "status": "completed",
            "steps": [
                {"step_id": 1, "duration": 3.5, "status": "success"},
                {"step_id": 2, "duration": 16.5, "status": "success"}
            ]
        },
        {
            "flow_name": "网站报表下载自动化",
            "started_at": "2026-03-25T09:00:00+08:00",
            "finished_at": "2026-03-25T09:00:18+08:00",
            "status": "completed",
            "steps": [
                {"step_id": 1, "duration": 3.2, "status": "success"},
                {"step_id": 2, "duration": 14.8, "status": "success"}
            ]
        }
    ]

    # 模拟优化建议
    recommendations = [
        {
            "type": "performance",
            "step_id": 2,
            "title": "减少固定等待时间",
            "issue": "步骤2平均执行时间过长: 15.65秒",
            "suggestion": "将固定等待（sleep）替换为显式等待，等待元素出现后再继续",
            "expected_improvement": "减少 30-50% 等待时间"
        },
        {
            "type": "reliability",
            "step_id": 1,
            "title": "优化选择器",
            "issue": "打开页面时偶尔失败",
            "suggestion": "添加页面加载完成检查，使用更稳定的等待策略",
            "expected_improvement": "提高 95% 成功率"
        }
    ]

    print("\n优化建议:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n  {i}. [{rec['type'].upper()}] {rec['title']}")
        print(f"     问题: {rec['issue']}")
        print(f"     建议: {rec['suggestion']}")
        if rec.get('expected_improvement'):
            print(f"     预期效果: {rec['expected_improvement']}")

    return recommendations


def save_example_results():
    """保存示例结果到文件"""
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    examples = {
        "example_1_simple_automation.json": example_1_simple_automation(),
        "example_2_complex_workflow.json": example_2_complex_workflow(),
        "example_3_conditional_logic.json": example_3_conditional_logic(),
        "example_4_performance_optimization.json": {
            "recommendations": example_4_performance_optimization()
        }
    }

    for filename, result in examples.items():
        output_path = output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 示例结果已保存: {output_path}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("AI + RPA 深度集成 - 快速开始示例")
    print("="*60)
    print("\n本示例展示如何使用自然语言生成 RPA 流程")

    # 运行所有示例
    example_1_simple_automation()
    example_2_complex_workflow()
    example_3_conditional_logic()
    example_4_performance_optimization()

    # 保存结果
    save_example_results()

    print("\n" + "="*60)
    print("所有示例运行完成！")
    print("="*60)
    print("\n下一步：")
    print("1. 查看 README.md 了解完整文档")
    print("2. 阅读 ai-rpa-integration-deep-dive.md 了解技术细节")
    print("3. 根据实际需求调整示例代码")
    print()


if __name__ == "__main__":
    main()
