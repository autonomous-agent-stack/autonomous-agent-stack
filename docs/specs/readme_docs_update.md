# TaskSpec: readme_docs_update

**Agent Type**: Documentation Update  
**Risk Level**: Low (文档修改)  
**Estimated Duration**: 2-5 分钟

## 任务描述

分析项目的安装步骤和配置要求，自动更新 `README.md` 中的安装指南部分。

## 目标

1. 扫描项目中的安装配置文件（`setup.py`, `requirements.txt`, `pyproject.toml`, `Makefile`, `package.json` 等）
2. 分析实际的依赖和安装步骤
3. 对比 `README.md` 中的安装说明
4. 生成更新后的 `README.md` patch
5. 运行验证命令确保步骤正确

## 允许路径

```yaml
allowed_paths:
  - "README.md"
  - "README_CN.md"
  - "README_EN.md"
  - "docs/QUICK_START.md"
  - "docs/INSTALL.md"
  - "docs/setup.md"
  - "INSTALL.md"
  - "SETUP.md"
```

## 禁止路径

```yaml
forbidden_paths:
  - ".git/"
  - ".github/"
  - "config/"
  - "secrets/"
  - ".env"
  - "*.key"
  - "*.pem"
  - "__pycache__/"
  - "node_modules/"
  - ".venv/"
  - "venv/"
  - "dist/"
  - "build/"
```

## 限制条件

```yaml
policy_constraints:
  max_files_changed: 3
  max_lines_per_file: 100
  max_total_lines: 200
  
  require_test_for_modifications: false  # 文档修改不需要测试
  
  allowed_operations:
    - "read_files"
    - "analyze_configs"
    - "write_documentation"
  
  forbidden_operations:
    - "execute_commands"
    - "install_dependencies"
    - "modify_code"
    - "git_operations"
```

## 验证命令

```yaml
validation_commands:
  - name: "检查 README 语法"
    command: "python -m markdown README.md > /dev/null"
    error_on_failure: true
    
  - name: "验证安装步骤可复制粘贴"
    command: "python scripts/verify_readme_install.py"
    error_on_failure: false  # 警告但不阻止
    
  - name: "检查必要文件存在"
    command: "test -f README.md && test -f requirements.txt || test -f setup.py || test -f pyproject.toml"
    error_on_failure: false
```

## Agent Prompt 模板

```python
PROMPT = """你是 AAS 文档补全助手。你的任务是分析项目的安装配置，更新 README.md 中的安装说明。

## 工作流程

1. **扫描项目配置**
   - 查找 setup.py, requirements.txt, pyproject.toml, package.json, Makefile 等配置文件
   - 识别项目类型（Python/Node.js/Go/Rust 等）
   - 提取关键依赖和安装命令

2. **分析当前 README**
   - 读取 README.md 中的安装说明部分
   - 对比配置文件和文档的一致性
   - 识别缺失或过时的信息

3. **生成更新**
   - 保持 README.md 的其他部分不变
   - 只更新安装相关的内容
   - 确保格式一致（Markdown 格式）

## 扫描优先级

1. Python 项目：
   - requirements.txt 或 pyproject.toml → pip install 命令
   - setup.py → python setup.py develop
   - Makefile 中的 install/setup 目标

2. Node.js 项目：
   - package.json → npm install/yarn install
   - package.json 中的 scripts

3. 通用：
   - Dockerfile → docker build 命令
   - docker-compose.yml → docker compose up

## 输出要求

1. **只修改 README.md 的安装部分**
2. **保持其他内容完全不变**
3. **使用清晰的步骤格式**：
   ```bash
   # 步骤 1
   command
   
   # 步骤 2
   command
   ```
4. **添加环境要求说明**（Python 版本、Node 版本等）
5. **包含验证步骤**（如 `make test` 或 `npm test`）

## 禁止操作

- ❌ 不要修改代码文件
- ❌ 不要修改配置文件
- ❌ 不要执行安装命令
- ❌ 不要修改 .git 相关文件
- ❌ 不要添加新文件
- ✅ 只输出 README.md 的 patch

## 审查标准

生成 patch 后，检查：
1. 是否只修改了文档？
2. 安装步骤是否清晰可执行？
3. 是否包含了环境要求？
4. 是否保持了原有格式？
"""
```

## 输入格式

```json
{
  "task_id": "readme_docs_update_001",
  "repo_path": "/path/to/project",
  "target_readme": "README.md",
  "priority": "normal",
  "deadline": "2026-04-09T12:00:00Z"
}
```

## 输出格式

```json
{
  "task_id": "readme_docs_update_001",
  "status": "completed",
  "result": {
    "patch_file": "/path/to/readme.patch",
    "summary": "更新了 README.md 中的安装说明",
    "changes": [
      "添加了 Python 3.11+ 要求",
      "更新了 pip install 命令",
      "添加了验证步骤"
    ],
    "validation": {
      "markdown_syntax": "passed",
      "copy_paste_test": "passed",
      "files_exist": "passed"
    }
  }
}
```

## Promotion 策略

```yaml
promotion_policy:
  requires_approval: true          # 需要人工审批
  auto_create_draft_pr: true       # 自动创建 Draft PR
  draft_pr_branch_prefix: "docs/readme-update"
  
  approval_criteria:
    - "安装步骤可执行"
    - "没有引入语法错误"
    - "保持了原有风格"
    - "没有修改非文档文件"
  
  auto_approve_conditions:
    - max_lines_changed: 50       # 小改动可自动批准
    - validation_all_passed: true
    - trusted_contributor: true
```

## 失败处理

```yaml
failure_handling:
  on_validation_error:
    action: "generate_warning_report"
    continue: false
    retry: false
    
  on_forbidden_path_access:
    action: "immediate_rejection"
    log_security_event: true
    
  on_format_conflict:
    action: "preserve_original_format"
    add_warning: true
```

## 示例场景

### 示例 1：Python 项目

**输入状态**：
- requirements.txt: `requests==2.31.0, flask==3.0.0`
- README.md 安装部分过时

**输出 patch**：
```diff
- ## 安装
- pip install -r requirements.txt
+ ## 安装
+ 
+ ### 环境要求
+ - Python 3.11+
+ 
+ ### 安装步骤
+ ```bash
+ # 克隆仓库
+ git clone <repo_url>
+ cd <repo_name>
+ 
+ # 安装依赖
+ pip install -r requirements.txt
+ 
+ # 或使用开发模式
+ pip install -e .
+ ```
+ 
+ ### 验证安装
+ ```bash
+ python -c "import flask; print(flask.__version__)"
+ ```
```

### 示例 2：Node.js 项目

**输入状态**：
- package.json 存在
- README.md 缺少安装说明

**输出 patch**：
```diff
+ ## 快速开始
+ 
+ ### 环境要求
+ - Node.js 18+
+ 
+ ### 安装
+ ```bash
+ npm install
+ ```
+ 
+ ### 运行
+ ```bash
+ npm start
+ # 或
+ npm run dev
+ ```
```

## 实现优先级

### Phase 1: 基础扫描器（本周）
```python
class ConfigScanner:
    """扫描项目配置文件"""
    
    def scan_python_configs(self) -> dict:
        """扫描 Python 项目配置"""
        configs = {}
        
        if os.path.exists("requirements.txt"):
            configs["requirements"] = self.parse_requirements_txt()
        if os.path.exists("pyproject.toml"):
            configs["pyproject"] = self.parse_pyproject_toml()
        if os.path.exists("setup.py"):
            configs["setup"] = self.parse_setup_py()
        
        return configs
    
    def detect_project_type(self) -> str:
        """检测项目类型"""
        if os.path.exists("requirements.txt") or os.path.exists("setup.py"):
            return "python"
        elif os.path.exists("package.json"):
            return "nodejs"
        elif os.path.exists("go.mod"):
            return "go"
        return "unknown"
```

### Phase 2: README 分析器
```python
class ReadmeAnalyzer:
    """分析现有 README"""
    
    def find_install_section(self) -> tuple:
        """找到安装说明部分的位置"""
        # 返回 (start_line, end_line)
        pass
    
    def extract_install_content(self) -> str:
        """提取现有安装内容"""
        pass
    
    def compare_with_config(self, config: dict) -> dict:
        """对比配置和文档的差异"""
        pass
```

### Phase 3: Patch 生成器
```python
class ReadmePatchGenerator:
    """生成 README patch"""
    
    def generate_patch(
        self, 
        original_readme: str,
        install_section: tuple,
        new_content: str
    ) -> str:
        """生成 unified diff patch"""
        pass
```

### Phase 4: 验证器
```python
class ReadmeValidator:
    """验证生成的 README"""
    
    def validate_markdown_syntax(self) -> bool:
        """验证 Markdown 语法"""
        pass
    
    def validate_install_steps(self) -> bool:
        """验证安装步骤的可执行性"""
        pass
```

## 测试计划

### 单元测试
```bash
tests/test_readme_agent/
├── test_config_scanner.py
├── test_readme_analyzer.py
├── test_patch_generator.py
└── test_validator.py
```

### 集成测试
```bash
# 在测试仓库上运行
make agent-run \
    AEP_AGENT=readme_docs_update \
    AEP_TASK="repo=/path/to/test_repo"
```

### Demo 展示流程
```bash
# 1. 创建测试场景
cd /tmp/test_readme_update
git init
echo "# Test Project" > README.md
echo "flask==3.0.0" > requirements.txt

# 2. 运行 agent
make agent-run \
    AEP_AGENT=readme_docs_update \
    AEP_TASK="repo=/tmp/test_readme_update"

# 3. 查看结果
cat /tmp/readme_update_patch.patch
git apply /tmp/readme_update_patch.patch
cat README.md  # 应该包含更新的安装说明
```

## 成功标准

- [ ] Agent 能正确扫描 Python/Node.js 项目配置
- [ ] 生成的 patch 只包含文档变更
- [ ] 验证命令能捕获明显错误
- [ ] Demo 能在 5 分钟内展示完整流程
- [ ] 代码覆盖率 > 80%

## 下一步

1. 创建 `src/autoresearch/agents/readme_docs_update.py`
2. 实现基础扫描器
3. 在 2-3 个测试仓库上验证
4. 完善 prompt 模板
5. 编写 demo 脚本

---

**预计工作量**: 2-3 天  
**风险等级**: 低（只修改文档）  
**价值**: 快速验证 AAS 管道，展示实际价值
