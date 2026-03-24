#!/bin/bash
# Quick Test Execution Script
# Run this script to execute all tests and generate reports

set -e  # Exit on error

echo "=================================="
echo "AI System Test Suite - Quick Run"
echo "=================================="
echo ""

# Change to test directory
cd "$(dirname "$0")"

# Check Python version
echo "Checking Python version..."
python --version || { echo "❌ Python not found!"; exit 1; }
echo "✅ Python found"
echo ""

# Run tests
echo "Running tests..."
echo "----------------"
python runner.py

# Check if tests passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "📊 Reports generated in: ./reports/"
    echo "   - HTML: Open test_report_*.html in browser"
    echo "   - JSON: Check test_results_*.json"
    echo ""
    echo "🎉 Success!"
else
    echo ""
    echo "❌ Some tests failed. Check output above."
    exit 1
fi
