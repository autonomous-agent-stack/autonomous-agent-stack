#!/usr/bin/env python3
"""
AI Job Hunter 使用示例
"""

from main import JobHunter

def example_1_basic_search():
    """示例 1：基础搜索"""
    print("="*80)
    print("示例 1：基础搜索")
    print("="*80)

    hunter = JobHunter()

    # 搜索 AI 工程师职位
    jobs = hunter.search_jobs(
        keywords="AI Engineer",
        location="Remote"
    )

    # 显示结果
    hunter.display_jobs(jobs, limit=5)
    print()


def example_2_platform_specific_search():
    """示例 2：指定平台搜索"""
    print("="*80)
    print("示例 2：指定平台搜索")
    print("="*80)

    hunter = JobHunter()

    # 只在 LinkedIn 和 Indeed 上搜索
    jobs = hunter.search_jobs(
        keywords="Python Developer",
        location="San Francisco",
        platforms=["linkedin", "indeed"]
    )

    hunter.display_jobs(jobs, limit=3)
    print()


def example_3_filter_jobs():
    """示例 3：筛选职位"""
    print("="*80)
    print("示例 3：筛选职位")
    print("="*80)

    hunter = JobHunter()

    # 先搜索
    jobs = hunter.search_jobs(
        keywords="Data Scientist",
        location="Remote"
    )

    print(f"\n筛选前: {len(jobs)} 个职位")

    # 按标签筛选
    filtered = hunter.filter_jobs(
        jobs,
        required_tags=["AI"]
    )

    print(f"筛选后（包含 AI 标签）: {len(filtered)} 个职位")

    # 按薪资筛选
    filtered = hunter.filter_jobs(
        jobs,
        min_salary=100000,
        max_salary=150000
    )

    print(f"筛选后（薪资 $100k-$150k）: {len(filtered)} 个职位")
    print()


def example_4_save_and_export():
    """示例 4：保存和导出"""
    print("="*80)
    print("示例 4：保存和导出")
    print("="*80)

    hunter = JobHunter()

    # 搜索职位
    jobs = hunter.search_jobs(
        keywords="Machine Learning Engineer",
        location="Remote"
    )

    # 保存感兴趣的职位
    if jobs:
        hunter.save_job(jobs[0])
        hunter.save_job(jobs[1])

    # 查看已保存的职位
    print("\n已保存的职位:")
    saved_jobs = hunter.list_saved_jobs()
    hunter.display_jobs(saved_jobs, limit=len(saved_jobs))

    # 导出为不同格式
    print("\n导出职位:")
    hunter.export_jobs(jobs[:3], format="json", filename="example_jobs.json")
    hunter.export_jobs(jobs[:3], format="csv", filename="example_jobs.csv")
    hunter.export_jobs(jobs[:3], format="markdown", filename="example_jobs.md")

    print()


def example_5_comprehensive_workflow():
    """示例 5：完整工作流程"""
    print("="*80)
    print("示例 5：完整工作流程")
    print("="*80)

    hunter = JobHunter()

    # 1. 搜索多个关键词
    keywords = ["AI Engineer", "Data Scientist", "Machine Learning"]
    all_jobs = []

    for keyword in keywords:
        print(f"\n🔍 搜索: {keyword}")
        jobs = hunter.search_jobs(
            keywords=keyword,
            location="Remote",
            platforms=["linkedin", "indeed"]
        )
        all_jobs.extend(jobs)

    print(f"\n📊 总计找到 {len(all_jobs)} 个职位")

    # 2. 筛选职位
    print("\n🔧 应用筛选条件...")
    filtered_jobs = hunter.filter_jobs(
        all_jobs,
        min_salary=100000,
        required_tags=["AI"]
    )
    print(f"✓ 筛选后剩余 {len(filtered_jobs)} 个职位")

    # 3. 保存最好的职位
    print("\n💾 保存前 3 个职位...")
    for job in filtered_jobs[:3]:
        hunter.save_job(job)

    # 4. 导出完整报告
    print("\n📤 生成求职报告...")
    hunter.export_jobs(
        filtered_jobs,
        format="markdown",
        filename="job_search_report.md"
    )

    print("\n✅ 工作流程完成！")
    print()


def main():
    """运行所有示例"""
    print("\n" + "="*80)
    print("AI Job Hunter - 使用示例")
    print("="*80 + "\n")

    # 运行各个示例
    example_1_basic_search()
    example_2_platform_specific_search()
    example_3_filter_jobs()
    example_4_save_and_export()
    example_5_comprehensive_workflow()

    print("="*80)
    print("所有示例运行完成！")
    print("="*80)


if __name__ == "__main__":
    main()
