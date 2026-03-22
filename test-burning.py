# 🔥 燃烧测试 #1

```python
# 测试燃烧功能
import unittest

class TestBurning(unittest.TestCase):
    def setUp(self):
        """初始化测试环境"""
        self.burner = TokenBurner()
    
    def test_generate_content(self):
        """测试内容生成"""
        content = self.burner.generate_content()
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 0)
    
    def test_save_file(self):
        """测试文件保存"""
        filename = self.burner.save_file("test content")
        self.assertTrue(os.path.exists(filename))
    
    def test_git_commit(self):
        """测试Git提交"""
        result = self.burner.git_commit("test commit")
        self.assertTrue(result)
    
    def test_git_push(self):
        """测试Git推送"""
        result = self.burner.git_push()
        self.assertTrue(result)
    
    def test_burn_loop(self):
        """测试燃烧循环"""
        # 运行3次测试
        for i in range(3):
            self.burner.burn_once()
        
        # 检查是否创建了文件
        self.assertGreater(self.burner.file_count, 0)

if __name__ == '__main__':
    unittest.main()
```

---

**创建时间**: 2026-03-23 04:52 AM
**状态**: 🔥 **测试代码**
