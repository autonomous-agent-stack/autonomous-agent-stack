import pytest
import tempfile
from pathlib import Path
from src.orchestrator.sandbox_cleaner import SandboxCleaner

def test_appledouble_cleanup():
    """测试AppleDouble文件清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建脏文件
        Path(tmpdir, "code.py").write_text("print('hello')")
        Path(tmpdir, "._code.py").write_text("dirty")
        Path(tmpdir, ".DS_Store").write_text("metadata")
        Path(tmpdir, "__MACOSX").mkdir()
        
        # 清理
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        # 验证
        assert len(cleaned) >= 2  # 至少清理2个文件
        remaining = [f.name for f in Path(tmpdir).glob("*")]
        assert "code.py" in remaining
        assert "._code.py" not in remaining
        assert ".DS_Store" not in remaining

def test_sandbox_security_validation():
    """测试沙盒安全性验证"""
    cleaner = SandboxCleaner()
    result = cleaner.validate_sandbox_security("/tmp")
    
    assert result["read_only"] is True
    assert result["network_disabled"] is True
    assert result["apple_double_cleaned"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
