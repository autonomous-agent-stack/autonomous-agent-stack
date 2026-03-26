# 🧬 P4 系统级自主代码进化协议

> **创建时间**：2026-03-26 04:29 GMT+8
> **优先级**：最高
> **工作分支**：codex/continue-autonomous-agent-stack
> **目标**：将底座的进化能力从"动态生成临时工具"升级为"自动提交底层代码更新（Auto-PR）"

---

## 🎯 核心目标

实现系统级自主代码进化，让底座能够：
1. 自动分析外部开源包
2. 自动生成分支并编写代码
3. 自动运行测试并修复问题
4. 自动提交 PR 等待人类审批

---

## 📋 任务矩阵

### 1️⃣ C1, C2 [版本控制代理组 (GitOps Agent)] ⏳

**任务**：实现 `RepositoryManager` 服务

**验收标准**：
- ✅ 赋予底座执行 Git 命令的能力
- ✅ 接收到外部开源包分析任务时自动执行：
  1. `git status` 确保工作区干净
  2. `git checkout -b auto-upgrade/{package_name}_{timestamp}` 拉取隔离分支
  3. 编写代码后自动 `git add .`
  4. `git commit -m "feat(auto): integrate {package_name}"`

**实现要点**：
```python
class RepositoryManager:
    async def ensure_clean_workspace(self) -> bool:
        """确保工作区干净"""
        pass
    
    async def create_upgrade_branch(self, package_name: str) -> str:
        """创建升级分支"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"auto-upgrade/{package_name}_{timestamp}"
        # git checkout -b {branch_name}
        return branch_name
    
    async def commit_changes(self, package_name: str) -> str:
        """提交变更"""
        # git add .
        # git commit -m "feat(auto): integrate {package_name}"
        pass
```

---

### 2️⃣ C3, C4 [代码审查与沙盒质检组 (QA/CI Sandbox)] ⏳

**任务**：实现自我测试拦截器

**验收标准**：
- ✅ 新分支生成代码后，在 Docker 沙盒中静默触发 pytest 回归测试
- ✅ **红线要求**：必须前置调用 `AppleDoubleCleaner`
- ✅ 若现有 40+ 测试有任何 Fail，AI 必须基于报错日志进行最多 3 轮自动修复（Self-Correction）
- ✅ 若无法修复，丢弃分支并上报

**实现要点**：
```python
class SelfTestInterceptor:
    async def run_tests_in_sandbox(self, branch_name: str) -> TestResult:
        """在沙盒中运行测试"""
        # 1. 清理 AppleDouble 文件
        await self.apple_double_cleaner.clean()
        
        # 2. 在 Docker 沙盒中运行 pytest
        result = await self.docker_sandbox.run("pytest tests/")
        
        # 3. 如果失败，尝试自动修复（最多3轮）
        if not result.success:
            for attempt in range(3):
                fixed = await self.auto_fix(result.errors)
                if fixed:
                    result = await self.docker_sandbox.run("pytest tests/")
                    if result.success:
                        break
        
        return result
```

---

### 3️⃣ C5, C6 [HITL 通道组 (Webhook & TWA)] ⏳

**任务**：实现 PR 审批卡片与群组通知

**验收标准**：
- ✅ 全量测试通过且代码推送到远端后，通过 Telegram Channel Adapter 向内部白名单群组推送通知
- ✅ **UI 约束**：通知必须极度克制、专业
- ✅ 在浅色 Web 面板新增 `[架构升级 (Upgrades)]` 极简 Tag 栏
- ✅ 提供 Diff（代码差异）预览
- ✅ 配备唯一的 `[Merge to Main]` 触发按钮

**实现要点**：
```python
class PRApprovalChannel:
    async def send_approval_notification(self, pr_info: PRInfo):
        """发送审批通知"""
        # 1. 推送到 Telegram 白名单群组
        await self.telegram_adapter.send_to_whitelist_group(
            f"🆕 架构升级: {pr_info.package_name}\n"
            f"📊 测试: ✅ 全部通过\n"
            f"🔗 PR: {pr_info.url}"
        )
        
        # 2. 更新 Web 面板
        await self.web_panel.add_upgrade_tag({
            "package": pr_info.package_name,
            "diff": pr_info.diff,
            "status": "pending_approval",
            "merge_button": True
        })
```

---

### 4️⃣ D1 [业务安全边界测试组] ⏳

**任务**：编写端到端测试，确保"自我进化"不会破坏现有的玛露品牌调性

**测试逻辑**：
1. 模拟引入一个虚拟的开源包
2. 底座自动写完代码后，运行"玛露 6g 遮瑕膏文案生成"测试
3. 断言底座依然能精准输出"不用调色、遮瑕力强"等专业词汇
4. 确保系统升级不会导致底层 Prompt 遗忘

**实现要点**：
```python
class BusinessSafetyTest:
    async def test_malu_brand_consistency(self):
        """测试玛露品牌调性一致性"""
        # 1. 模拟引入虚拟包
        await self.system.integrate_package("virtual_test_package")
        
        # 2. 生成玛露文案
        result = await self.system.generate_copy(
            product="玛露 6g 遮瑕膏",
            style="professional"
        )
        
        # 3. 断言关键词存在
        assert "不用调色" in result
        assert "遮瑕力强" in result
        assert "专业" in result
        
        # 4. 确保 Prompt 未遗忘
        assert self.system.prompt_integrity_check() is True
```

---

## ⚠️ 工程纪律

### 1. 绝对禁止直接 push 到主分支
```
❌ 禁止：git push origin main
✅ 允许：git push origin auto-upgrade/{package_name}_{timestamp}
```

### 2. 保持代码模块单一职责
```
✅ 纯 Python 封装
✅ 本地 Git 命令
✅ Pytest 调用
❌ 复杂 CI/CD 管道
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│         P4 系统级自主代码进化            │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
   │ C1, C2  │ │ C3, C4  │ │ C5, C6  │
   │ GitOps  │ │ QA/CI   │ │ HITL    │
   │ Agent   │ │ Sandbox │ │ Channel │
   └─────────┘ └─────────┘ └─────────┘
        │           │           │
        │           │           │
   ┌────▼───────────▼───────────▼────┐
   │    D1: 业务安全边界测试组        │
   └──────────────────────────────────┘
```

---

## 📊 实施路线图

### Phase 1: GitOps 基础（1-2天）
- [ ] 实现 `RepositoryManager`
- [ ] 实现分支管理
- [ ] 实现 Git 命令封装

### Phase 2: 测试沙盒（1-2天）
- [ ] 实现 `SelfTestInterceptor`
- [ ] 集成 `AppleDoubleCleaner`
- [ ] 实现自动修复机制

### Phase 3: HITL 通道（1天）
- [ ] 实现 `PRApprovalChannel`
- [ ] 集成 Telegram 通知
- [ ] 实现 Web 面板升级标签

### Phase 4: 安全测试（1天）
- [ ] 实现 `BusinessSafetyTest`
- [ ] 编写端到端测试
- [ ] 验证品牌调性一致性

---

## 🧪 测试策略

### 单元测试
- `test_repository_manager.py`（Git 操作）
- `test_self_test_interceptor.py`（测试拦截）
- `test_pr_approval_channel.py`（PR 通知）

### 集成测试
- `test_p4_integration.py`（端到端流程）
- `test_business_safety.py`（业务安全）

---

## 📝 验收标准

### 功能验收
- ✅ 自动创建隔离分支
- ✅ 自动运行测试（3轮自修复）
- ✅ 自动提交 PR
- ✅ 群组通知
- ✅ Web 面板审批

### 安全验收
- ✅ 禁止直接 push 到 main
- ✅ AppleDouble 清理
- ✅ 品牌调性测试通过
- ✅ Prompt 完整性检查

### 性能验收
- ✅ 测试运行时间 < 5分钟
- ✅ 自动修复成功率 > 80%
- ✅ PR 创建时间 < 1分钟

---

## 🚨 风险点

### 1. Git 冲突
- **缓解**：强制要求工作区干净
- **监控**：冲突检测告警

### 2. 测试失败
- **缓解**：3轮自动修复
- **监控**：失败率统计

### 3. 品牌遗忘
- **缓解**：业务安全测试
- **监控**：Prompt 完整性检查

---

## 📅 时间线

- **2026-03-26 04:29**：协议创建
- **预计完成**：2026-03-29（3天）
- **验收时间**：2026-03-30

---

## 🔗 相关链接

- **仓库**：https://github.com/srxly888-creator/autonomous-agent-stack
- **分支**：codex/continue-autonomous-agent-stack
- **相关协议**：
  - P1: 收尾协议（已完成）
  - P2: 检查点协议（已完成）
  - P3: HITL 协议（已完成）

---

**状态**：⏳ 待实现
**优先级**：🔴 最高
**预计时间**：3天
