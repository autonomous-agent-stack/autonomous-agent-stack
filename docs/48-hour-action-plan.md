# 🎯 48 小时关键动作清单

> 执行时间：2026-03-26 12:08 - 2026-03-28 12:08
> 状态：30% 完成（核心功能就绪，待回家执行）

---

## ✅ Day 1（今天，2026-03-26）

### 已完成（户外完成）

- [x] 核心功能 100% 完成
- [x] 多话题路由系统就绪
- [x] 安全审计系统就绪
- [x] Token 脱敏功能就绪
- [x] 零信任方案文档完成
- [x] 自动巡航配置完成

---

### 待执行（回家后，今晚）

#### 1. 实装依赖哈希清单（15 分钟）

**步骤**：
```bash
# 1. 连接到 M1 Mac
ssh iCloud_GZ@<M1的IP>

# 2. 进入项目目录
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 3. 执行零信任加固脚本
bash scripts/zero-trust-dependencies.sh

# 4. 验证
cat requirements.txt.locked.sha256
```

**预期结果**：
- ✅ requirements.txt.locked 生成
- ✅ SHA-256 校验和生成
- ✅ 审计日志记录

---

#### 2. 开启 Docker 网络限制（20 分钟）

**步骤**：
```bash
# 1. 编辑 docker-compose.yml
nano docker-compose.yml

# 2. 添加网络配置
# networks:
#   isolated_network:
#     internal: true

# 3. 重启 Docker 服务
docker-compose down
docker-compose up -d

# 4. 验证网络隔离
docker network inspect isolated_network
```

**预期结果**：
- ✅ 容器无法访问外网
- ✅ 仅允许白名单 API

---

#### 3. 启动自动巡航（5 分钟）

**步骤**：
```bash
# 1. 编辑 .env
nano .env

# 2. 添加巡航配置
AUTO_CRUISE_ENABLED=true
AUTO_CRUISE_INTELLIGENCE_INTERVAL=4h
AUTO_CRUISE_AUDIT_INTERVAL=1h

# 3. 重启 uvicorn
pkill uvicorn
nohup python3 -m uvicorn src.autoresearch.api.main:app --host 0.0.0.0 --port 8000 &

# 4. 验证巡航状态
curl http://127.0.0.1:8000/api/cron/status
```

**预期结果**：
- ✅ Topic 4 每 4 小时自动抓取
- ✅ Topic 3 每 1 小时自动清理

---

## 🚀 Day 2（明天，2026-03-27）

### 上午（10:00-12:00）

#### 4. 第一次业务合拢测试（30 分钟）

**测试场景**：
```
通过手机发送："@助理 分析这张 M1 芯片市场截图并查最新趋势"
（附带一张截图）
```

**预期效果**：
- ✅ Topic 1：指令镜像
- ✅ Topic 2：图片分析
- ✅ Topic 3：清理日志
- ✅ Topic 4：市场情报

**验证步骤**：
1. 在 Telegram 群组发送测试指令
2. 等待 30 秒
3. 检查 4 个 Topic 的输出
4. 记录测试结果

---

### 下午（14:00-16:00）

#### 5. 性能优化（1 小时）

**监控指标**：
```bash
# 查看资源使用
docker stats

# 查看 API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://127.0.0.1:8000/healthz

# 查看日志
tail -f /tmp/uvicorn.log
```

**优化项**：
- 调整定时任务频率（如需）
- 优化数据库查询
- 调整缓存策略

---

#### 6. 文档完善（1 小时）

**待完成文档**：
- [ ] 用户手册（README.md）
- [ ] API 文档（API_DOCS.md）
- [ ] 故障排查指南（TROUBLESHOOTING.md）
- [ ] 部署指南（DEPLOYMENT.md）

---

## 📊 进度跟踪

### 完成度

| 阶段 | 任务 | 预计时间 | 状态 |
|------|------|---------|------|
| **Day 1 上午** | 核心功能 | - | ✅ 100% |
| **Day 1 晚上** | 零信任加固 | 40 分钟 | ⏳ 0% |
| **Day 2 上午** | 业务测试 | 30 分钟 | ⏳ 0% |
| **Day 2 下午** | 优化文档 | 2 小时 | ⏳ 0% |
| **总计** | - | **3 小时 10 分** | **30%** |

---

## 🎯 成功标准

### Day 1 结束

- ✅ 依赖哈希清单生成
- ✅ Docker 网络隔离配置
- ✅ 自动巡航启动
- ✅ Topic 3/4 定期输出

---

### Day 2 结束

- ✅ 第一次业务测试成功
- ✅ 4 个 Topic 分流正常
- ✅ 性能优化完成
- ✅ 文档完善

---

## 🔍 验证清单

### 安全验证

- [ ] `requirements.txt.locked` 存在
- [ ] SHA-256 校验和匹配
- [ ] Docker 容器无外网访问
- [ ] 审计日志定期生成

---

### 功能验证

- [ ] Telegram Bot 响应正常
- [ ] 4 个 Topic 分流正确
- [ ] 自动巡航定时执行
- [ ] WebAuthn 授权可用

---

### 性能验证

- [ ] API 响应时间 < 100ms
- [ ] 内存使用 < 500MB
- [ ] CPU 使用 < 20%（空闲时）
- [ ] 磁盘空间充足（> 10GB）

---

## 📝 备注

### 如果遇到问题

1. **Docker 网络配置失败**
   - 检查 Docker 版本
   - 确认 iptables 规则

2. **自动巡航未启动**
   - 检查 .env 配置
   - 查看 uvicorn 日志

3. **Topic 分流失败**
   - 检查 Bot Token
   - 验证物理 ID 配置

---

**执行进度**：**30%**（核心完成，待回家执行）
**预计完成**：2026-03-27 18:00
**总用时**：~3 小时

---

**创建时间**：2026-03-26 12:08
