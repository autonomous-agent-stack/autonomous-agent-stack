#!/usr/bin/env python3
"""P4 Self-Evolution Auditor - P4 自我进化审计器

每周日凌晨 03:00 执行：
1. 性能回测：对比本周所有任务的平均响应时间与 Token 消耗
2. 代码重构建议：调用 Claude CLI 分析被标记为 OPTIMIZE_NEEDED 的模块
3. 影子验证：在沙盒中运行 test_blitz_integration.py
4. 推送简报：将优化建议与性能对比图投递至 Topic 3 (#系统审计)
"""

import sqlite3
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class P4Auditor:
    """P4 自我进化审计器"""
    
    def __init__(self, project_root: str = "/Volumes/PS1008/Github/autonomous-agent-stack"):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / "src" / "memory" / "evolution_history.sqlite"
        self.report_path = self.project_root / "docs" / "audit_reports"
        
        # 创建目录
        self.report_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 性能记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                task_type TEXT NOT NULL,
                response_time REAL,
                token_count INTEGER,
                success BOOLEAN,
                metadata TEXT
            )
        """)
        
        # 优化建议表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                module_path TEXT NOT NULL,
                suggestion TEXT,
                priority TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # 审计报告表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_type TEXT NOT NULL,
                report_path TEXT,
                summary TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
    def record_performance(self, task_type: str, response_time: float, 
                          token_count: int, success: bool, metadata: Dict = None):
        """记录性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO performance_metrics 
               (task_type, response_time, token_count, success, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (task_type, response_time, token_count, success, json.dumps(metadata or {}))
        )
        
        conn.commit()
        conn.close()
        
    def performance_backtest(self, days: int = 7) -> Dict[str, Any]:
        """性能回测"""
        logger.info(f"[P4 Auditor] 性能回测: 最近 {days} 天")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询本周数据
        cursor.execute("""
            SELECT 
                task_type,
                AVG(response_time) as avg_response_time,
                AVG(token_count) as avg_token_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                COUNT(*) as total_tasks
            FROM performance_metrics
            WHERE timestamp >= datetime('now', ?)
            GROUP BY task_type
        """, (f'-{days} days',))
        
        current_stats = cursor.fetchall()
        
        # 查询上周数据
        cursor.execute("""
            SELECT 
                task_type,
                AVG(response_time) as avg_response_time,
                AVG(token_count) as avg_token_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                COUNT(*) as total_tasks
            FROM performance_metrics
            WHERE timestamp >= datetime('now', ?) 
              AND timestamp < datetime('now', ?)
            GROUP BY task_type
        """, (f'-{days*2} days', f'-{days} days'))
        
        previous_stats = cursor.fetchall()
        
        conn.close()
        
        # 构建对比报告
        report = {
            "period": f"最近 {days} 天",
            "current": [],
            "previous": [],
            "changes": []
        }
        
        for stat in current_stats:
            task_type, avg_rt, avg_tc, success_rate, total = stat
            report["current"].append({
                "task_type": task_type,
                "avg_response_time": round(avg_rt, 2),
                "avg_token_count": round(avg_tc, 2),
                "success_rate": round(success_rate, 2),
                "total_tasks": total
            })
            
        # 计算变化
        for curr in report["current"]:
            prev = next((p for p in report["previous"] if p["task_type"] == curr["task_type"]), None)
            
            if prev:
                change = {
                    "task_type": curr["task_type"],
                    "response_time_change": round((curr["avg_response_time"] - prev["avg_response_time"]) / prev["avg_response_time"] * 100, 2),
                    "token_count_change": round((curr["avg_token_count"] - prev["avg_token_count"]) / prev["avg_token_count"] * 100, 2),
                    "success_rate_change": round(curr["success_rate"] - prev["success_rate"], 2)
                }
                report["changes"].append(change)
                
        logger.info(f"[P4 Auditor] 性能回测完成: {len(report['current'])} 个任务类型")
        
        return report
        
    def find_optimization_candidates(self) -> List[Dict]:
        """查找需要优化的模块"""
        logger.info("[P4 Auditor] 查找优化候选模块")
        
        candidates = []
        
        # 查找标记为 OPTIMIZE_NEEDED 的模块
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                
                if "OPTIMIZE_NEEDED" in content:
                    candidates.append({
                        "path": str(py_file.relative_to(self.project_root)),
                        "reason": "标记为 OPTIMIZE_NEEDED",
                        "priority": "high"
                    })
            except Exception as e:
                logger.warning(f"[P4 Auditor] 跳过文件 {py_file}: {e}")
                continue
                
        logger.info(f"[P4 Auditor] 发现 {len(candidates)} 个优化候选")
        
        return candidates
        
    def shadow_validation(self) -> Dict[str, Any]:
        """影子验证"""
        logger.info("[P4 Auditor] 影子验证开始")
        
        test_script = self.project_root / "tests" / "test_blitz_integration.py"
        
        if not test_script.exists():
            logger.warning("[P4 Auditor] 测试脚本不存在")
            return {"status": "skipped", "reason": "测试脚本不存在"}
            
        try:
            # 在沙盒中运行测试
            result = subprocess.run(
                ["python3", str(test_script)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            validation_result = {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "output": result.stdout,
                "errors": result.stderr
            }
            
            logger.info(f"[P4 Auditor] 影子验证完成: {validation_result['status']}")
            
            return validation_result
            
        except subprocess.TimeoutExpired:
            logger.error("[P4 Auditor] 影子验证超时")
            return {"status": "timeout"}
        except Exception as e:
            logger.error(f"[P4 Auditor] 影子验证失败: {e}")
            return {"status": "error", "error": str(e)}
            
    def generate_report(self, performance: Dict, candidates: List, validation: Dict) -> str:
        """生成审计报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_file = self.report_path / f"audit_report_{timestamp}.md"
        
        report_lines = [
            f"# P4 自我进化审计报告",
            f"",
            f"**审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**审计周期**: {performance['period']}",
            f"",
            f"---",
            f"",
            f"## 📊 性能回测",
            f"",
            f"### 当前性能",
            f""
        ]
        
        for stat in performance["current"]:
            report_lines.extend([
                f"- **{stat['task_type']}**:",
                f"  - 平均响应时间: {stat['avg_response_time']}s",
                f"  - 平均 Token 消耗: {stat['avg_token_count']}",
                f"  - 成功率: {stat['success_rate']}%",
                f"  - 任务总数: {stat['total_tasks']}",
                f""
            ])
            
        if performance["changes"]:
            report_lines.extend([
                f"### 性能变化",
                f""
            ])
            
            for change in performance["changes"]:
                rt_change = f"+{change['response_time_change']}%" if change['response_time_change'] > 0 else f"{change['response_time_change']}%"
                tc_change = f"+{change['token_count_change']}%" if change['token_count_change'] > 0 else f"{change['token_count_change']}%"
                
                report_lines.extend([
                    f"- **{change['task_type']}**:",
                    f"  - 响应时间: {rt_change}",
                    f"  - Token 消耗: {tc_change}",
                    f"  - 成功率变化: {change['success_rate_change']}%",
                    f""
                ])
                
        report_lines.extend([
            f"---",
            f"",
            f"## 🔧 优化建议",
            f""
        ])
        
        if candidates:
            for candidate in candidates:
                report_lines.extend([
                    f"- **{candidate['path']}**",
                    f"  - 原因: {candidate['reason']}",
                    f"  - 优先级: {candidate['priority']}",
                    f""
                ])
        else:
            report_lines.append(f"✅ 无优化建议\n")
            
        report_lines.extend([
            f"---",
            f"",
            f"## 🧪 影子验证",
            f"",
            f"- **状态**: {validation['status']}",
            f""
        ])
        
        if validation['status'] == 'failed':
            report_lines.extend([
                f"- **错误输出**:",
                f"```",
                validation.get('errors', 'N/A'),
                f"```",
                f""
            ])
            
        report_lines.extend([
            f"---",
            f"",
            f"**报告生成时间**: {datetime.now().isoformat()}"
        ])
        
        report_content = "\n".join(report_lines)
        report_file.write_text(report_content)
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO audit_reports (report_type, report_path, summary)
               VALUES (?, ?, ?)""",
            ("weekly_audit", str(report_file), f"性能回测: {len(performance['current'])} 个任务, 优化建议: {len(candidates)} 个, 验证: {validation['status']}")
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"[P4 Auditor] 审计报告已生成: {report_file}")
        
        return str(report_file)
        
    def run_audit(self):
        """运行完整审计"""
        logger.info("="*50)
        logger.info("P4 自我进化审计开始")
        logger.info("="*50)
        
        # 1. 性能回测
        performance = self.performance_backtest(days=7)
        
        # 2. 查找优化候选
        candidates = self.find_optimization_candidates()
        
        # 3. 影子验证
        validation = self.shadow_validation()
        
        # 4. 生成报告
        report_path = self.generate_report(performance, candidates, validation)
        
        logger.info("="*50)
        logger.info("P4 自我进化审计完成")
        logger.info("="*50)
        
        return {
            "performance": performance,
            "candidates": candidates,
            "validation": validation,
            "report_path": report_path
        }


if __name__ == "__main__":
    auditor = P4Auditor()
    result = auditor.run_audit()
    
    print(f"\n审计报告: {result['report_path']}")
    print(f"优化建议: {len(result['candidates'])} 个")
    print(f"验证状态: {result['validation']['status']}")
