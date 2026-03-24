#!/usr/bin/env python3
"""
AI Job Hunter - 多平台求职工具
支持：LinkedIn AI、Indeed、Glassdoor、Hired、AngelList
"""

import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import requests
from pathlib import Path

@dataclass
class Job:
    """职位信息数据结构"""
    platform: str
    title: str
    company: str
    location: str
    salary: Optional[str] = None
    description: Optional[str] = None
    url: str = ""
    posted_date: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class JobHunter:
    """AI 求职工具主类"""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.saved_jobs = []
        self._load_saved_jobs()

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  配置文件 {config_path} 不存在，使用默认配置")
            return {
                "linkedin": {"api_key": ""},
                "indeed": {"api_key": ""},
                "glassdoor": {"api_key": ""},
                "hired": {"api_key": ""},
                "angellist": {"api_key": ""},
                "search_preferences": {
                    "keywords": "",
                    "location": "",
                    "job_type": "full-time",
                    "experience_level": ""
                }
            }

    def _load_saved_jobs(self):
        """加载已保存的职位"""
        saved_file = Path("saved_jobs.json")
        if saved_file.exists():
            with open(saved_file, 'r', encoding='utf-8') as f:
                self.saved_jobs = [Job(**job) for job in json.load(f)]

    def _save_jobs(self):
        """保存职位到文件"""
        with open("saved_jobs.json", 'w', encoding='utf-8') as f:
            json.dump([asdict(job) for job in self.saved_jobs], f, ensure_ascii=False, indent=2)

    def search_jobs(
        self,
        keywords: str,
        location: str = "",
        platforms: List[str] = None,
        job_type: str = "full-time"
    ) -> List[Job]:
        """
        搜索职位

        Args:
            keywords: 搜索关键词（如 "Python工程师"）
            location: 地点（如 "北京"）
            platforms: 平台列表，默认搜索所有平台
            job_type: 工作类型（full-time, part-time, contract, remote）

        Returns:
            职位列表
        """
        if platforms is None:
            platforms = ["linkedin", "indeed", "glassdoor", "hired", "angellist"]

        all_jobs = []

        print(f"🔍 正在搜索职位: {keywords}")
        if location:
            print(f"📍 地点: {location}")
        print(f"💼 工作类型: {job_type}\n")

        for platform in platforms:
            print(f"🔹 搜索 {platform.upper()}...")
            try:
                jobs = self._search_platform(platform, keywords, location, job_type)
                all_jobs.extend(jobs)
                print(f"   ✓ 找到 {len(jobs)} 个职位")
            except Exception as e:
                print(f"   ✗ 搜索失败: {e}")

        print(f"\n🎯 总计找到 {len(all_jobs)} 个职位")
        return all_jobs

    def _search_platform(
        self,
        platform: str,
        keywords: str,
        location: str,
        job_type: str
    ) -> List[Job]:
        """
        搜索特定平台的职位

        这里提供基础框架，实际实现需要：
        1. 各平台的 API 调用或网页抓取
        2. 处理不同平台的数据格式
        """

        # 模拟数据 - 实际使用时替换为真实 API 调用
        mock_jobs = {
            "linkedin": [
                Job(
                    platform="LinkedIn",
                    title=f"Senior {keywords} Engineer",
                    company="Tech Corp",
                    location=location or "Remote",
                    salary="$120k - $180k",
                    description="We're looking for an experienced engineer...",
                    url="https://linkedin.com/jobs/view/1",
                    tags=["AI", "Remote"]
                ),
                Job(
                    platform="LinkedIn",
                    title=f"{keywords} Developer",
                    company="Innovation Inc",
                    location=location or "San Francisco",
                    salary="$100k - $150k",
                    description="Join our team building the future...",
                    url="https://linkedin.com/jobs/view/2",
                    tags=["Full-time"]
                )
            ],
            "indeed": [
                Job(
                    platform="Indeed",
                    title=f"{keywords} Specialist",
                    company="Data Solutions",
                    location=location or "New York",
                    salary="$90k - $130k",
                    description="Apply your skills to solve real-world problems...",
                    url="https://indeed.com/jobs/view/1"
                )
            ],
            "glassdoor": [
                Job(
                    platform="Glassdoor",
                    title=f"{keywords} Analyst",
                    company="Analytics Plus",
                    location=location or "Boston",
                    salary="$95k - $140k",
                    description="Help us make data-driven decisions...",
                    url="https://glassdoor.com/jobs/view/1"
                )
            ]
        }

        return mock_jobs.get(platform, [])

    def filter_jobs(
        self,
        jobs: List[Job],
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        required_tags: List[str] = None
    ) -> List[Job]:
        """
        筛选职位

        Args:
            jobs: 职位列表
            min_salary: 最低薪资
            max_salary: 最高薪资
            required_tags: 必需的标签

        Returns:
            筛选后的职位列表
        """
        filtered = jobs

        if required_tags:
            filtered = [
                job for job in filtered
                if any(tag in job.tags for tag in required_tags)
            ]

        if min_salary or max_salary:
            filtered = [
                job for job in filtered
                if self._salary_in_range(job.salary, min_salary, max_salary)
            ]

        return filtered

    def _salary_in_range(
        self,
        salary_str: str,
        min_salary: Optional[int],
        max_salary: Optional[int]
    ) -> bool:
        """检查薪资是否在范围内"""
        if not salary_str or (min_salary is None and max_salary is None):
            return True

        try:
            # 提取薪资数字
            import re
            numbers = re.findall(r'\d+', salary_str.replace('k', '000'))
            if not numbers:
                return True

            salary = int(numbers[0])

            if min_salary and salary < min_salary:
                return False
            if max_salary and salary > max_salary:
                return False

            return True
        except:
            return True

    def save_job(self, job: Job):
        """保存职位"""
        self.saved_jobs.append(job)
        self._save_jobs()
        print(f"💾 已保存: {job.title} @ {job.company}")

    def remove_saved_job(self, index: int):
        """移除已保存的职位"""
        if 0 <= index < len(self.saved_jobs):
            job = self.saved_jobs.pop(index)
            self._save_jobs()
            print(f"🗑️  已移除: {job.title}")

    def list_saved_jobs(self) -> List[Job]:
        """列出已保存的职位"""
        return self.saved_jobs

    def export_jobs(self, jobs: List[Job], format: str = "json", filename: str = None):
        """
        导出职位

        Args:
            jobs: 要导出的职位列表
            format: 导出格式（json, csv, markdown）
            filename: 文件名，默认自动生成
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_export_{timestamp}.{format}"

        if format == "json":
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([asdict(job) for job in jobs], f, ensure_ascii=False, indent=2)

        elif format == "csv":
            import csv
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Platform', 'Title', 'Company', 'Location', 'Salary', 'URL'])
                for job in jobs:
                    writer.writerow([job.platform, job.title, job.company,
                                   job.location, job.salary, job.url])

        elif format == "markdown":
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Job Search Results\n\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for i, job in enumerate(jobs, 1):
                    f.write(f"## {i}. {job.title}\n")
                    f.write(f"- **平台**: {job.platform}\n")
                    f.write(f"- **公司**: {job.company}\n")
                    f.write(f"- **地点**: {job.location}\n")
                    if job.salary:
                        f.write(f"- **薪资**: {job.salary}\n")
                    if job.url:
                        f.write(f"- **链接**: {job.url}\n")
                    f.write("\n")

        print(f"📤 已导出 {len(jobs)} 个职位到 {filename}")

    def display_jobs(self, jobs: List[Job], limit: int = 10):
        """显示职位列表"""
        print(f"\n{'='*80}")
        print(f"职位列表 (共 {len(jobs)} 个，显示前 {min(limit, len(jobs))} 个)")
        print(f"{'='*80}\n")

        for i, job in enumerate(jobs[:limit], 1):
            print(f"{i}. {job.title}")
            print(f"   🏢 {job.company} ({job.platform})")
            print(f"   📍 {job.location}")
            if job.salary:
                print(f"   💰 {job.salary}")
            if job.url:
                print(f"   🔗 {job.url}")
            if job.tags:
                print(f"   🏷️  {', '.join(job.tags)}")
            print()


def main():
    parser = argparse.ArgumentParser(description='AI Job Hunter - 多平台求职工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 搜索命令
    search_parser = subparsers.add_parser('search', help='搜索职位')
    search_parser.add_argument('keywords', help='搜索关键词')
    search_parser.add_argument('--location', '-l', help='地点')
    search_parser.add_argument('--platforms', '-p', nargs='+',
                              choices=['linkedin', 'indeed', 'glassdoor', 'hired', 'angellist'],
                              help='指定平台')
    search_parser.add_argument('--type', '-t', default='full-time',
                              choices=['full-time', 'part-time', 'contract', 'remote'],
                              help='工作类型')
    search_parser.add_argument('--export', choices=['json', 'csv', 'markdown'],
                              help='导出格式')
    search_parser.add_argument('--output', '-o', help='输出文件名')

    # 已保存职位命令
    saved_parser = subparsers.add_parser('saved', help='管理已保存的职位')
    saved_parser.add_argument('--list', action='store_true', help='列出已保存的职位')
    saved_parser.add_argument('--remove', type=int, help='移除指定索引的职位')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    hunter = JobHunter()

    if args.command == 'search':
        jobs = hunter.search_jobs(
            keywords=args.keywords,
            location=args.location,
            platforms=args.platforms,
            job_type=args.type
        )

        hunter.display_jobs(jobs)

        if args.export:
            hunter.export_jobs(jobs, format=args.export, filename=args.output)

        # 询问是否保存
        if jobs:
            print("\n💡 提示: 运行 'python main.py saved --list' 查看已保存的职位")

    elif args.command == 'saved':
        if args.list:
            jobs = hunter.list_saved_jobs()
            if jobs:
                hunter.display_jobs(jobs, limit=len(jobs))
            else:
                print("还没有保存任何职位")
        elif args.remove is not None:
            hunter.remove_saved_job(args.remove)


if __name__ == "__main__":
    main()
