# requirement-4 保密业务资产存放决策与最佳实践

## 1. 文档定位

这份文档回答的是 requirement-4 的一个现实问题：

- 业务资产是保密的
- 不适合直接放公开仓库
- 也不应该因为方便就随手 commit 到 GitHub

本文档给出：

- 当前推荐方案
- 可选方案对比
- GitHub Organization private repo 是否免费
- requirement-4 的具体落地做法

这份文档讨论的是**资产保管与协作方式**，不是业务规则本身。

---

## 2. 一句话结论

结论很明确：

- **不要用新个人账号来放 requirement-4 原始业务资产**
- **不要把原始 Excel / golden /真实样本直接 commit 到当前代码仓**
- **最佳实践是“代码仓”和“保密资产仓”分离**

对 requirement-4，推荐顺序是：

1. 当前代码仓继续放代码、文档、占位目录、脱敏摘要
2. 原始业务资产放公司受控的私有存储
3. 本地按需把资产注入到 `tests/fixtures/requirement4_*`
4. 注入前先确保这些真实文件不会被 git 跟踪

如果确实要用 GitHub 协作资产：

- 优先用 **GitHub Organization 下独立 private repo**
- 不要用新个人账号做“私人保密仓”

---

## 3. GitHub Organization private repo 免费吗

**可以免费。**

GitHub 官方当前口径是：

- GitHub Free 适用于个人和组织
- 组织在 GitHub Free 下可以使用 **unlimited private repositories**
- 但 private repo 在 Free 方案下是 **limited feature set**

可直接参考：

- [GitHub 文档（中文）：GitHub 的计划](https://docs.github.com/zh/get-started/learning-about-github/githubs-plans)
- [GitHub Docs: GitHub’s plans](https://docs.github.com/get-started/learning-about-github/githubs-plans)
- [GitHub Pricing](https://github.com/pricing)
- [GitHub Docs: About organizations](https://docs.github.com/enterprise-cloud%40latest//organizations/collaborating-with-groups-in-organizations/about-organizations)

这意味着：

- 用 GitHub Organization 建 private repo，本身不是收费门槛
- 但如果你要更强的治理能力，往往要升级到 Team 或更高

补充说明：

- 我查到了 **中文的 GitHub 文档页**，可用来确认 Free / Team / Enterprise 的计划说明
- 我没有查到独立的 **中文 `GitHub Pricing` 价格矩阵页面路径**
- 所以实际价格与功能对比，仍以官方价格页为准：`https://github.com/pricing`

---

## 4. 方案对比

### 方案 A：当前代码仓直接放原始业务资产

不推荐。

原因：

- Git 天生有历史
- clone / fork / 本地副本会扩散
- 一旦误提交，清理成本高

GitHub 官方对删除敏感数据的说明也表明，这类事故通常需要重写历史并协调副本处理：

- [GitHub Docs: Removing sensitive data from a repository](https://docs.github.com/github/authenticating-to-github/removing-sensitive-data-from-a-repository?azure-portal=true)

### 方案 B：新建个人账号，建 private repo 放资产

不推荐。

原因：

- 访问控制绑在个人上
- 交接和审计差
- 离职、换人、丢失 2FA 都会变成治理问题
- 容易形成“个人保密岛”

### 方案 C：GitHub Organization 下独立 private repo 放资产

可以用，但仍然是次优，不是最优。

适合场景：

- 你们确实需要基于 GitHub 做小范围协作
- 需要最小粒度地分配成员权限
- 需要组织级审计和团队访问控制

注意：

- 仓库可见性应优先选 **private**，不是 `internal`
- `internal` 对 enterprise 成员范围更大，不适合最小暴露面场景

相关说明：

- [GitHub Docs: About repositories](https://docs.github.com/enterprise-cloud%40latest/repositories/creating-and-managing-repositories/about-repositories)
- [GitHub Docs: Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility?azure-portal=true)

### 方案 D：代码仓与保密资产仓分离

**这是 requirement-4 的推荐方案。**

做法是：

- GitHub 仓库只放代码、文档、脱敏契约摘要、README、占位目录
- 原始 Excel / golden /真实样本放公司受控私有存储
- 本地运行时按需同步到工作目录
- 同步后确保 git 不跟踪这些真实文件

优点：

- 代码协作与保密资产治理分层
- 误提交风险最低
- requirement-4 的 pilot 与后续 productionization 都更容易治理

---

## 5. requirement-4 的推荐落地方案

对当前仓库，建议直接采用：

### 5.1 仓库里保留的内容

可以放进当前代码仓的内容：

- requirement-4 文档
- fixture 目录结构
- README / 占位说明
- 脱敏后的 `ASSET_READINESS_REVIEW.md`
- 脱敏后的 `CONTRACT_SUMMARY.md`
- 不含敏感原始值的 schema / mapping 摘要

### 5.2 不应放进当前代码仓的内容

不应直接 commit 的内容：

- 原始 Excel 输入文件
- 原始 golden 输出
- 含真实客户 / 订单 / 金额的样本
- 含敏感审批信息的审计材料
- 可逆推出真实业务规则的完整原始资产

### 5.3 资产应存放在哪里

推荐放在公司受控的私有存储中，例如：

- 公司云盘的受控目录
- 受权限控制的文件服务器
- 团队共享但受审计的私有文档空间

要求只有两个：

- 权限可控
- 可审计

---

## 6. 如果一定要用 GitHub，正确姿势是什么

如果你们内部流程必须基于 GitHub 协作，推荐这样做：

### 6.1 用 Organization，不用新个人账号

原因：

- 组织适合团队交接
- 支持团队级访问控制
- 支持组织审计日志

参考：

- [GitHub Docs: About organizations](https://docs.github.com/enterprise-cloud%40latest//organizations/collaborating-with-groups-in-organizations/about-organizations)
- [GitHub Docs: Reviewing the audit log for your organization](https://docs.github.com/articles/reviewing-the-audit-log-for-your-organization)

### 6.2 仓库可见性选 private，不选 internal

原因：

- private 的暴露面最小
- internal 会扩大到 enterprise 成员范围

参考：

- [GitHub Docs: About repositories](https://docs.github.com/enterprise-cloud%40latest/repositories/creating-and-managing-repositories/about-repositories)

### 6.3 访问权限按最小权限分配

GitHub 组织仓库角色从低到高包括：

- Read
- Triage
- Write
- Maintain
- Admin

requirement-4 保密资产仓建议：

- 大部分人只给 `Read`
- 少数维护人给 `Write` 或 `Maintain`
- `Admin` 控制在极少数

参考：

- [GitHub Docs: Repository roles for an organization](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)

### 6.4 把组织审计日志当成必备能力

GitHub 官方说明，组织审计日志可查看：

- 谁做了什么
- 对哪个仓库做的
- 在什么时间做的

参考：

- [GitHub Docs: Reviewing the audit log for your organization](https://docs.github.com/articles/reviewing-the-audit-log-for-your-organization)

### 6.5 不要把 secret scanning 当成业务资产保护方案

原因：

- secret scanning 主要面向 token、key、password 等已知 secret 模式
- 它不是为你的 Excel 业务资产内容而设计的

因此不要误以为“开了 secret scanning 就可以安全上传原始资产”。

参考：

- [GitHub Docs: About secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning)

---

## 7. 当前仓库的特别提醒

**截至当前仓库状态，`.gitignore` 并没有默认忽略 `tests/fixtures/requirement4_*` 里的真实资产文件。**

这意味着：

- 你如果把真实 Excel 直接放进这些目录
- 又没有额外做本地 ignore
- 就存在被误提交的风险

所以 requirement-4 在落真实资产前，必须先做“本地排除”。

---

## 8. 小团队可直接照做的操作建议

### 8.1 最优做法：资产放仓库外

推荐：

- 原始资产放在仓库目录之外
- 运行时按需复制进本地工作目录
- 跑完后清理或继续保存在本地受控目录

优点：

- 不依赖 git ignore 规则是否写对
- 风险最低

### 8.2 如果必须落到仓库里的 fixture 目录

那就至少先在本地加排除规则，不要直接改动全仓 `.gitignore` 作为默认策略。

推荐使用 `.git/info/exclude`，把真实资产排除在当前本地 clone 之外。

示例：

```gitignore
/tests/fixtures/requirement4_contracts/*
!/tests/fixtures/requirement4_contracts/README.md

/tests/fixtures/requirement4_samples/*
!/tests/fixtures/requirement4_samples/README.md

/tests/fixtures/requirement4_golden/*
!/tests/fixtures/requirement4_golden/README.md
```

这样做的目的：

- 保留占位 README
- 排除真实文件
- 不影响文档和目录结构

### 8.3 每次提交前必须做的检查

至少执行：

```bash
git status --short
git check-ignore -v tests/fixtures/requirement4_samples/*
```

如果 `git status` 里还出现真实 Excel / golden 文件，就不要提交。

---

## 9. requirement-4 推荐治理模型

最推荐的治理模型是：

### 代码仓

- 当前 `autonomous-agent-stack`
- 放代码、文档、脱敏摘要、占位 fixture

### 保密资产仓

- 公司私有存储
- 放原始 Excel、golden、真实样本、敏感审计材料

### 本地工作区

- 按需注入 `tests/fixtures/requirement4_*`
- 注入前先确认已做本地排除
- 只在本机做试运行

这套方式最适合 requirement-4 当前的 2 天 pilot 阶段。

---

## 10. 什么时候才考虑单独的 GitHub private asset repo

只有在下面情况同时成立时，才建议认真考虑单独 private repo：

- 资产需要多人版本协作
- 团队已经有明确组织管理者
- 你们愿意做最小权限、审计、分支治理
- 资产仍然适合进入 Git 历史

如果只是“想找个地方先放着”，那不是建新 private asset repo 的好理由。

---

## 11. 误提交后的处理原则

如果真实资产已经误提交到仓库：

1. 先停止继续传播
2. 不要假装删掉工作区文件就等于没事
3. 评估是否已经 push、是否已有 clone / fork / PR
4. 按 GitHub 官方敏感数据清理流程处理

参考：

- [GitHub Docs: Removing sensitive data from a repository](https://docs.github.com/github/authenticating-to-github/removing-sensitive-data-from-a-repository?azure-portal=true)

---

## 12. 最终建议

对 requirement-4，当前推荐方案只有一句话：

**代码进仓，原始资产不进仓；确需 GitHub 协作时，用 Organization private repo，不用新个人账号。**
