import pytest
import tempfile
from pathlib import Path
from src.orchestrator.sandbox_cleaner import SandboxCleaner

def test_appledouble_clean():
    """测试AppleDouble清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建脏文件
        Path(tmpdir, "code.py").write_text("print('hello')")
        Path(tmpdir, "._code.py").write_text("dirty")
        
        # 清理
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) >= 1
        assert not Path(tmpdir, "._code.py").exists()

def test_ds_store_clean():
    """测试.DS_Store清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, ".DS_Store").write_text("metadata")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) >= 1
        assert not Path(tmpdir, ".DS_Store").exists()

def test_macosx_clean():
    """测试__MACOSX清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        macosx_dir = Path(tmpdir, "__MACOSX")
        macosx_dir.mkdir()
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) >= 1

def test_nested_clean():
    """测试嵌套目录清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建嵌套结构
        nested_dir = Path(tmpdir, "subdir", "nested")
        nested_dir.mkdir(parents=True)
        Path(nested_dir, "._nested.py").write_text("dirty")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) >= 1

def test_sandbox_validation():
    """测试沙盒验证"""
    cleaner = SandboxCleaner()
    result = cleaner.validate_sandbox_security("/tmp")
    
    assert result["read_only"] is True
    assert result["network_disabled"] is True

def test_no_clean_needed():
    """测试无需清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "clean.py").write_text("clean code")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) == 0

def test_multiple_dirty_files():
    """测试多个脏文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建10个脏文件
        for i in range(10):
            Path(tmpdir, f"._file{i}.py").write_text("dirty")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) == 10

def test_mixed_clean_dirty():
    """测试混合文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "clean.py").write_text("clean")
        Path(tmpdir, "._dirty.py").write_text("dirty")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) == 1
        assert Path(tmpdir, "clean.py").exists()

def test_permission_preserved():
    """测试权限保留"""
    with tempfile.TemporaryDirectory() as tmpdir:
        clean_file = Path(tmpdir, "clean.py")
        clean_file.write_text("clean")
        clean_file.chmod(0o755)
        
        cleaner = SandboxCleaner()
        cleaner.clean_directory(tmpdir)
        
        # 权限应该保留
        assert oct(clean_file.stat().st_mode)[-3:] == "755"

def test_large_directory():
    """测试大目录清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建1000个文件（10%脏文件）
        for i in range(1000):
            if i % 10 == 0:
                Path(tmpdir, f"._file{i}.py").write_text("dirty")
            else:
                Path(tmpdir, f"file{i}.py").write_text("clean")
        
        cleaner = SandboxCleaner()
        cleaned = cleaner.clean_directory(tmpdir)
        
        assert len(cleaned) == 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
