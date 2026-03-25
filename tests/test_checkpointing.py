import pytest
import tempfile
import asyncio
from src.orchestrator.checkpointing import GraphCheckpointManager, NodeState

@pytest.mark.asyncio
async def test_save_and_load_checkpoint():
    """测试保存和加载检查点"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = GraphCheckpointManager(f"{tmpdir}/test.db")
        
        # 保存检查点
        checkpoint_id = await cm.save_checkpoint(
            "graph_123", "node_planner",
            NodeState.RUNNING, {"progress": 50}
        )
        
        # 加载检查点
        checkpoint = await cm.load_checkpoint("graph_123", "node_planner")
        
        assert checkpoint is not None
        assert checkpoint["state"] == NodeState.RUNNING
        assert checkpoint["data"]["progress"] == 50

@pytest.mark.asyncio
async def test_get_latest_checkpoint():
    """测试获取最新检查点"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = GraphCheckpointManager(f"{tmpdir}/test.db")
        
        # 保存多个检查点
        await cm.save_checkpoint("graph_123", "node_planner", NodeState.COMPLETED)
        await cm.save_checkpoint("graph_123", "node_generator", NodeState.RUNNING)
        
        # 获取最新检查点
        latest = await cm.get_latest_checkpoint("graph_123")
        
        assert latest is not None
        assert latest["node_id"] == "node_generator"
        assert latest["state"] == NodeState.RUNNING

@pytest.mark.asyncio
async def test_resume_from_checkpoint():
    """测试从检查点恢复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = GraphCheckpointManager(f"{tmpdir}/test.db")
        
        # 保存检查点
        await cm.save_checkpoint("graph_123", "node_executor", NodeState.RUNNING)
        
        # 恢复
        node_id = await cm.resume_from_checkpoint("graph_123")
        
        assert node_id == "node_executor"

@pytest.mark.asyncio
async def test_clear_checkpoints():
    """测试清除检查点"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = GraphCheckpointManager(f"{tmpdir}/test.db")
        
        # 保存检查点
        await cm.save_checkpoint("graph_123", "node_planner", NodeState.COMPLETED)
        
        # 清除
        await cm.clear_checkpoints("graph_123")
        
        # 验证
        checkpoint = await cm.load_checkpoint("graph_123", "node_planner")
        assert checkpoint is None

@pytest.mark.asyncio
async def test_crash_recovery():
    """测试崩溃恢复（断电测试）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        
        # 第一次运行：保存检查点
        cm1 = GraphCheckpointManager(db_path)
        await cm1.save_checkpoint(
            "graph_123", "node_planner",
            NodeState.RUNNING, {"step": 3}
        )
        
        # 模拟崩溃（删除对象）
        del cm1
        
        # 恢复：重新初始化
        cm2 = GraphCheckpointManager(db_path)
        checkpoint = await cm2.load_checkpoint("graph_123", "node_planner")
        
        # 验证恢复成功
        assert checkpoint is not None
        assert checkpoint["state"] == NodeState.RUNNING
        assert checkpoint["data"]["step"] == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
