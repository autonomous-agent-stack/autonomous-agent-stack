goal: 优化代码性能
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 16
max_concurrency: 3
