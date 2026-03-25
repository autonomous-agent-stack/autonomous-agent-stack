"""
测试结构化日志功能

验证：
- GraphEngine 节点执行日志
- ToolSynthesis Docker 沙盒日志
- AppleDouble 清理拦截日志
"""

import json
import time
from src.orchestrator.graph_engine import GraphEngine, GraphNode, NodeType
from src.orchestrator.tool_synthesis import ToolSynthesis, DockerConfig
from src.adapters.opensage_adapter import OpenSageAdapter, AppleDoubleCleaner


def test_graph_engine_logging():
    """测试 GraphEngine 日志"""
    print("\n" + "="*60)
    print("测试 GraphEngine 结构化日志")
    print("="*60)
    
    engine = GraphEngine("test_graph")
    
    # 定义测试节点
    def planner_handler(inputs):
        time.sleep(0.1)  # 模拟处理
        return {"plan": "test_plan"}
    
    def generator_handler(inputs):
        time.sleep(0.15)
        return {"code": "print('hello')"}
    
    def executor_handler(inputs):
        time.sleep(0.2)
        return {"result": "success"}
    
    # 添加节点
    engine.add_node(GraphNode(
        id="planner",
        type=NodeType.PLANNER,
        handler=planner_handler,
        retry_config={"max_attempts": 2}
    ))
    
    engine.add_node(GraphNode(
        id="generator",
        type=NodeType.GENERATOR,
        handler=generator_handler,
        dependencies=["planner"]
    ))
    
    engine.add_node(GraphNode(
        id="executor",
        type=NodeType.EXECUTOR,
        handler=executor_handler,
        dependencies=["generator"]
    ))
    
    # 执行图
    results = engine.execute()
    
    # 获取统计信息
    stats = engine.get_execution_stats()
    print(f"\n执行统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    return results


def test_tool_synthesis_logging():
    """测试 ToolSynthesis Docker 沙盒日志"""
    print("\n" + "="*60)
    print("测试 ToolSynthesis Docker 沙盒日志")
    print("="*60)
    
    config = DockerConfig(
        image="python:3.11-slim",
        timeout_seconds=10
    )
    
    synthesizer = ToolSynthesis(config)
    
    # 测试脚本
    test_script = '''#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
result = {
    "message": "Hello from Docker sandbox!",
    "input": data
}
print(json.dumps(result, ensure_ascii=False))
'''
    
    # 执行脚本
    result = synthesizer.execute_script(
        script_content=test_script,
        input_data={"test": "data"},
        script_name="test_script.py"
    )
    
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  耗时: {result.duration_ms}ms")
    print(f"  输出: {result.stdout[:200]}")
    
    return result


def test_appledouble_cleanup_logging():
    """测试 AppleDouble 清理日志（重点）"""
    print("\n" + "="*60)
    print("测试 AppleDouble 清理日志（重点）")
    print("="*60)
    
    cleaner = AppleDoubleCleaner()
    
    # 测试列表清理
    test_list = [
        "file1.txt",
        "._file1.txt",  # AppleDouble
        "file2.txt",
        ".DS_Store",    # macOS 元数据
        "._file2.txt",  # AppleDouble
        "file3.txt"
    ]
    
    print(f"\n原始列表: {test_list}")
    
    cleaned_list, stats = cleaner.clean_list(test_list)
    
    print(f"\n清理后列表: {cleaned_list}")
    print(f"\n清理统计:")
    print(f"  总数: {stats['total_items']}")
    print(f"  移除: {stats['files_removed']}")
    print(f"  保留: {stats['files_kept']}")
    print(f"  耗时: {stats['duration_ms']}ms")
    print(f"  移除的文件: {stats['removed_files']}")
    
    # 测试字典清理
    print("\n" + "-"*60)
    print("测试字典清理:")
    
    test_dict = {
        "normal_key": "value1",
        "._meta_key": "value2",  # AppleDouble
        "another_key": "value3",
        ".DS_Store": "value4",    # macOS 元数据
        "._another_meta": "value5"
    }
    
    print(f"\n原始字典: {list(test_dict.keys())}")
    
    cleaned_dict, dict_stats = cleaner.clean_dict(test_dict)
    
    print(f"\n清理后字典: {list(cleaned_dict.keys())}")
    print(f"\n清理统计:")
    print(f"  总键数: {dict_stats['total_keys']}")
    print(f"  移除: {dict_stats['keys_removed']}")
    print(f"  保留: {dict_stats['keys_kept']}")
    print(f"  耗时: {dict_stats['duration_ms']}ms")
    
    return cleaned_list, cleaned_dict


def test_opensage_adapter_integration():
    """测试 OpenSage 适配器集成"""
    print("\n" + "="*60)
    print("测试 OpenSage 适配器集成")
    print("="*60)
    
    adapter = OpenSageAdapter()
    
    # 测试 AppleDouble 清理
    test_data = [
        "normal_file.txt",
        "._macos_metadata.txt",
        "another_file.txt",
        ".DS_Store"
    ]
    
    print(f"\n原始数据: {test_data}")
    
    cleaned = adapter.clean_appledouble(test_data)
    
    print(f"清理后: {cleaned}")
    
    # 测试 JSON 解析
    print("\n" + "-"*60)
    print("测试 JSON 解析:")
    
    valid_json = '{"key": "value", "number": 42}'
    result = adapter.parse_external_format(valid_json)
    print(f"解析结果: {result}")
    
    return cleaned


def test_error_retry_logging():
    """测试错误重试日志"""
    print("\n" + "="*60)
    print("测试错误重试日志")
    print("="*60)
    
    engine = GraphEngine("retry_test")
    
    attempt_count = {"count": 0}
    
    def failing_handler(inputs):
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise Exception(f"模拟失败 (尝试 {attempt_count['count']})")
        return {"success": True}
    
    # 添加会失败的节点
    engine.add_node(GraphNode(
        id="failing_node",
        type=NodeType.EXECUTOR,
        handler=failing_handler,
        retry_config={"max_attempts": 3, "base_delay_ms": 100}
    ))
    
    # 执行
    results = engine.execute()
    
    print(f"\n最终结果: {results['failing_node'].status}")
    print(f"总尝试次数: {attempt_count['count']}")
    
    return results


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("结构化日志功能测试套件")
    print("="*60)
    
    # 测试 GraphEngine
    graph_results = test_graph_engine_logging()
    
    # 测试 ToolSynthesis
    synthesis_result = test_tool_synthesis_logging()
    
    # 测试 AppleDouble 清理（重点）
    cleaned_list, cleaned_dict = test_appledouble_cleanup_logging()
    
    # 测试 OpenSage 适配器集成
    adapter_result = test_opensage_adapter_integration()
    
    # 测试错误重试
    retry_results = test_error_retry_logging()
    
    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60)
    print("\n重点日志输出已包含:")
    print("  ✓ GraphEngine 节点执行日志")
    print("  ✓ Docker 沙盒启动和执行日志")
    print("  ✓ AppleDouble 清理拦截日志（重点）")
    print("  ✓ 错误重试日志")
    print("  ✓ 节点执行耗时日志")


if __name__ == "__main__":
    main()
