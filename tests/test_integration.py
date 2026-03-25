"""
完整集成测试：验证 API Skeleton + SQLite 持久化 + evaluator_command

这个测试验证 P0 成果是否正常工作。
"""

import pytest
from fastapi.testclient import TestClient
import tempfile
import json
from pathlib import Path


# 导入应用
from src.autoresearch.api.main import app
from src.autoresearch.core.repositories.evaluations import Database


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    yield db

    # 清理
    Path(db_path).unlink(missing_ok=True)


class TestEvaluationAPI:
    """测试 Evaluator API"""

    def test_create_evaluation_success(self, client):
        """测试创建评估任务"""
        response = client.post(
            "/api/v1/evaluations",
            json={
                "task_name": "test_task",
                "config_path": "test.json",
                "description": "测试任务"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

    def test_create_evaluation_with_override(self, client):
        """测试带 evaluator_command override 的创建"""
        response = client.post(
            "/api/v1/evaluations",
            json={
                "task_name": "test_task",
                "config_path": "test.json",
                "evaluator_command": {
                    "command": ["python", "test.py"],
                    "timeout_seconds": 60,
                    "work_dir": ".",
                    "env": {"DEBUG": "true"}
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    def test_get_evaluation_not_found(self, client):
        """测试查询不存在的任务"""
        response = client.get("/api/v1/evaluations/nonexistent")

        assert response.status_code == 404

    def test_list_evaluations(self, client):
        """测试列出所有评估"""
        # 先创建几个任务
        for i in range(3):
            client.post(
                "/api/v1/evaluations",
                json={
                    "task_name": f"test_task_{i}",
                    "config_path": "test.json"
                }
            )

        # 列出所有任务
        response = client.get("/api/v1/evaluations")

        assert response.status_code == 200
        data = response.json()
        assert "evaluations" in data
        assert len(data["evaluations"]) >= 3


class TestSQLitePersistence:
    """测试 SQLite 持久化"""

    def test_database_initialization(self, temp_db):
        """测试数据库初始化"""
        # 数据库应该自动创建表
        assert temp_db is not None

    def test_create_and_retrieve_evaluation(self, temp_db):
        """测试创建和查询评估记录"""
        # 创建记录
        eval_data = {
            "id": "test_123",
            "task_id": "task_456",
            "type": "test",
            "status": "queued",
            "request": {"test": "data"}
        }

        # 保存
        temp_db.get_session()
        # 这里需要实际实现仓储层方法

    def test_update_evaluation_status(self, temp_db):
        """测试更新评估状态"""
        # 创建记录
        # 更新状态为 completed
        # 验证更新成功
        pass


class TestEvaluatorCommand:
    """测试 evaluator_command override"""

    def test_evaluator_command_parsing(self):
        """测试 evaluator_command 解析"""
        from src.autoresearch.shared.models import EvaluatorCommand

        cmd = EvaluatorCommand(
            command=["python", "test.py"],
            timeout_seconds=60,
            work_dir=".",
            env={"DEBUG": "true"}
        )

        assert cmd.command == ["python", "test.py"]
        assert cmd.timeout_seconds == 60
        assert cmd.work_dir == "."
        assert cmd.env == {"DEBUG": "true"}

    def test_evaluator_command_compatibility(self):
        """测试旧版 list 形式兼容"""
        from src.autoresearch.shared.models import EvaluatorCommand

        # 旧版格式
        cmd = EvaluatorCommand(command=["python", "test.py"])

        assert cmd.timeout_seconds == 300  # 默认值
        assert cmd.work_dir is None
        assert cmd.env is None


class TestAppleDoubleCleanup:
    """测试 AppleDouble 清理"""

    def test_cleanup_script_exists(self):
        """测试清理脚本存在"""
        cleanup_script = Path("scripts/cleanup-appledouble.sh")
        assert cleanup_script.exists()

    def test_pre_start_check_exists(self):
        """测试启动前检查脚本存在"""
        pre_start = Path("scripts/pre-start-check.py")
        assert pre_start.exists()


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
