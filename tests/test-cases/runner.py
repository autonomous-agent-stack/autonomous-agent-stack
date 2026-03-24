"""
Test Runner
Execute all tests and generate comprehensive reports
"""

import unittest
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import traceback


class TestRunner:
    """Custom test runner with detailed reporting"""
    
    def __init__(self, test_dir: str = None):
        self.test_dir = test_dir or Path(__file__).parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
            },
            "suites": [],
            "duration": 0
        }
    
    def discover_tests(self) -> unittest.TestSuite:
        """Discover all test cases"""
        loader = unittest.TestLoader()
        start_dir = str(self.test_dir)
        pattern = "test_*.py"
        
        suite = loader.discover(start_dir, pattern=pattern)
        return suite
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all tests and collect results"""
        print("=" * 70)
        print("AI SYSTEM TEST SUITE")
        print("=" * 70)
        print(f"Starting tests at: {self.results['timestamp']}")
        print()
        
        # Discover tests
        suite = self.discover_tests()
        
        # Count tests
        self.results["summary"]["total"] = suite.countTestCases()
        print(f"Discovered {self.results['summary']['total']} test cases")
        print()
        
        # Run tests
        start_time = time.time()
        
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=open(str(self.test_dir / "test_output.log"), "w")
        )
        
        result = runner.run(suite)
        
        self.results["duration"] = time.time() - start_time
        
        # Parse results
        self.results["summary"]["passed"] = result.testsRun - len(result.failures) - len(result.errors)
        self.results["summary"]["failed"] = len(result.failures)
        self.results["summary"]["errors"] = len(result.errors)
        self.results["summary"]["skipped"] = len(result.skipped)
        
        # Collect detailed results
        self._collect_suite_results(suite, result)
        
        return self.results
    
    def _collect_suite_results(self, suite: unittest.TestSuite, result: unittest.TestResult):
        """Collect detailed results for each test suite"""
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                self._collect_suite_results(test, result)
            else:
                suite_name = test.__class__.__name__
                
                # Find or create suite entry
                suite_entry = next(
                    (s for s in self.results["suites"] if s["name"] == suite_name),
                    None
                )
                
                if not suite_entry:
                    suite_entry = {
                        "name": suite_name,
                        "tests": [],
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "skipped": 0
                    }
                    self.results["suites"].append(suite_entry)
                
                # Determine test status
                status = "passed"
                for failure in result.failures:
                    if failure[0] == test:
                        status = "failed"
                        suite_entry["failed"] += 1
                        break
                else:
                    for error in result.errors:
                        if error[0] == test:
                            status = "error"
                            suite_entry["errors"] += 1
                            break
                    else:
                        for skip in result.skipped:
                            if skip[0] == test:
                                status = "skipped"
                                suite_entry["skipped"] += 1
                                break
                        else:
                            suite_entry["passed"] += 1
                
                suite_entry["tests"].append({
                    "name": test._testMethodName,
                    "status": status
                })
    
    def generate_report(self, output_dir: str = None) -> str:
        """Generate comprehensive test report"""
        output_dir = Path(output_dir or self.test_dir / "reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML report
        html_report = self._generate_html_report()
        html_path = output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_report)
        
        # Generate JSON report
        json_path = output_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        
        # Generate summary
        self._print_summary()
        
        print(f"\nReports generated:")
        print(f"  HTML: {html_path}")
        print(f"  JSON: {json_path}")
        
        return str(html_path)
    
    def _generate_html_report(self) -> str:
        """Generate HTML test report"""
        summary = self.results["summary"]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI System Test Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 0;
        }}
        .passed {{ color: #10b981; }}
        .failed {{ color: #ef4444; }}
        .errors {{ color: #f59e0b; }}
        .skipped {{ color: #6b7280; }}
        .suite {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .suite h2 {{
            margin: 0 0 20px 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .test {{
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .test.passed {{
            background-color: #d1fae5;
            border-left: 4px solid #10b981;
        }}
        .test.failed {{
            background-color: #fee2e2;
            border-left: 4px solid #ef4444;
        }}
        .test.error {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
        }}
        .test.skipped {{
            background-color: #f3f4f6;
            border-left: 4px solid #6b7280;
        }}
        .test-name {{
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge.passed {{ background: #10b981; color: white; }}
        .badge.failed {{ background: #ef4444; color: white; }}
        .badge.error {{ background: #f59e0b; color: white; }}
        .badge.skipped {{ background: #6b7280; color: white; }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
            display: flex;
        }}
        .progress-segment {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI System Test Report</h1>
        <p>Generated: {self.results['timestamp']}</p>
        <p>Duration: {self.results['duration']:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="summary-card">
            <h3>Total Tests</h3>
            <p class="value">{summary['total']}</p>
        </div>
        <div class="summary-card">
            <h3>Passed</h3>
            <p class="value passed">{summary['passed']}</p>
        </div>
        <div class="summary-card">
            <h3>Failed</h3>
            <p class="value failed">{summary['failed']}</p>
        </div>
        <div class="summary-card">
            <h3>Errors</h3>
            <p class="value errors">{summary['errors']}</p>
        </div>
        <div class="summary-card">
            <h3>Skipped</h3>
            <p class="value skipped">{summary['skipped']}</p>
        </div>
        <div class="summary-card">
            <h3>Success Rate</h3>
            <p class="value passed">{(summary['passed']/summary['total']*100):.1f}%</p>
        </div>
    </div>
    
    <div class="progress-bar">
        <div class="progress-segment passed" style="width: {(summary['passed']/summary['total']*100):.1f}%">
            ✓ {(summary['passed']/summary['total']*100):.1f}%
        </div>
        <div class="progress-segment failed" style="width: {(summary['failed']/summary['total']*100):.1f}%">
            ✗ {(summary['failed']/summary['total']*100):.1f}%
        </div>
        <div class="progress-segment error" style="width: {(summary['errors']/summary['total']*100):.1f}%">
            ⚠ {(summary['errors']/summary['total']*100):.1f}%
        </div>
    </div>
"""
        
        # Add test suites
        for suite in self.results["suites"]:
            html += f"""
    <div class="suite">
        <h2>{suite['name']}</h2>
        <p>
            Passed: <span class="passed">{suite['passed']}</span> | 
            Failed: <span class="failed">{suite['failed']}</span> | 
            Errors: <span class="errors">{suite['errors']}</span> | 
            Skipped: <span class="skipped">{suite['skipped']}</span>
        </p>
"""
            for test in suite["tests"]:
                html += f"""
        <div class="test {test['status']}">
            <span class="test-name">{test['name']}</span>
            <span class="badge {test['status']}">{test['status']}</span>
        </div>
"""
            html += "    </div>\n"
        
        html += """
</body>
</html>
"""
        return html
    
    def _print_summary(self):
        """Print test summary to console"""
        summary = self.results["summary"]
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:    {summary['total']}")
        print(f"Passed:         ✓ {summary['passed']}")
        print(f"Failed:         ✗ {summary['failed']}")
        print(f"Errors:         ⚠ {summary['errors']}")
        print(f"Skipped:        ○ {summary['skipped']}")
        print(f"Success Rate:   {(summary['passed']/summary['total']*100):.1f}%")
        print(f"Duration:       {self.results['duration']:.2f}s")
        print("=" * 70)
        
        # Print suite breakdown
        print("\nSuite Breakdown:")
        for suite in self.results["suites"]:
            print(f"\n{suite['name']}:")
            print(f"  Passed:   {suite['passed']}")
            print(f"  Failed:   {suite['failed']}")
            print(f"  Errors:   {suite['errors']}")
            print(f"  Skipped:  {suite['skipped']}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run AI System Tests")
    parser.add_argument(
        "--test-dir",
        default=None,
        help="Directory containing tests"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for reports"
    )
    
    args = parser.parse_args()
    
    # Run tests
    runner = TestRunner(test_dir=args.test_dir)
    runner.run_tests()
    
    # Generate report
    report_path = runner.generate_report(output_dir=args.output_dir)
    
    # Exit with appropriate code
    summary = runner.results["summary"]
    if summary["failed"] > 0 or summary["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
