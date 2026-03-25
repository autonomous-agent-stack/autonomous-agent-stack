import { NextResponse } from 'next/server'

export async function GET() {
  const parity = {
    overall: 68,
    lastUpdated: new Date().toISOString(),
    categories: [
      {
        name: '核心会话管理',
        priority: 'P0',
        progress: 100,
        features: [
          { name: 'SQLite 持久化', status: 'completed', completion: 100 },
          { name: 'Session CRUD API', status: 'completed', completion: 100 },
          { name: '会话复用机制', status: 'completed', completion: 100 },
        ],
      },
      {
        name: 'Telegram 网关',
        priority: 'P0',
        progress: 100,
        features: [
          { name: 'Webhook 入口', status: 'completed', completion: 100 },
          { name: 'chat_id -> session 映射', status: 'completed', completion: 100 },
          { name: '魔法链接认证', status: 'completed', completion: 100 },
        ],
      },
      {
        name: 'Web 面板安全',
        priority: 'P0',
        progress: 100,
        features: [
          { name: '零信任架构', status: 'completed', completion: 100 },
          { name: 'JWT 验证', status: 'completed', completion: 100 },
          { name: '审计日志', status: 'completed', completion: 100 },
        ],
      },
      {
        name: '运行控制',
        priority: 'P1',
        progress: 75,
        features: [
          { name: 'cancel 命令', status: 'completed', completion: 100 },
          { name: 'retry 命令', status: 'completed', completion: 100 },
          { name: 'task tree 可视化', status: 'in_progress', completion: 50 },
          { name: 'Mermaid 图渲染', status: 'pending', completion: 0 },
        ],
      },
      {
        name: '动态工具执行',
        priority: 'P1',
        progress: 85,
        features: [
          { name: 'Docker 沙盒', status: 'completed', completion: 100 },
          { name: 'AppleDouble 清理', status: 'completed', completion: 100 },
          { name: '资源限制', status: 'in_progress', completion: 70 },
          { name: '网络隔离', status: 'completed', completion: 100 },
        ],
      },
      {
        name: 'P3 生态融合',
        priority: 'P1',
        progress: 50,
        features: [
          { name: 'OpenViking 记忆压缩', status: 'in_progress', completion: 60 },
          { name: 'MiroFish 预测旁路', status: 'in_progress', completion: 40 },
        ],
      },
      {
        name: 'P4 自主集成',
        priority: 'P2',
        progress: 30,
        features: [
          { name: 'Discover API', status: 'in_progress', completion: 40 },
          { name: 'Prototype API', status: 'pending', completion: 20 },
          { name: 'Promote API', status: 'pending', completion: 10 },
        ],
      },
      {
        name: '多智能体并发',
        priority: 'P2',
        progress: 25,
        features: [
          { name: 'Lead Agent 编排', status: 'in_progress', completion: 30 },
          { name: 'Sub-agents 调度', status: 'pending', completion: 20 },
          { name: '上下文隔离', status: 'pending', completion: 25 },
        ],
      },
    ],
    gaps: [
      {
        priority: 'P1',
        feature: 'task tree Mermaid 渲染',
        description: '需要实现 Mermaid 语法解析和渲染',
        estimatedEffort: '2-3 天',
      },
      {
        priority: 'P1',
        feature: '资源限制优化',
        description: 'Docker 容器内存限制需调整为 512MB',
        estimatedEffort: '1 天',
      },
      {
        priority: 'P2',
        feature: 'OpenViking 集成',
        description: '完成记忆压缩 API 的完整实现',
        estimatedEffort: '3-5 天',
      },
      {
        priority: 'P2',
        feature: 'MiroFish 预测闸门',
        description: '实现执行前置信度检查',
        estimatedEffort: '2-3 天',
      },
    ],
  }

  return NextResponse.json(parity)
}
