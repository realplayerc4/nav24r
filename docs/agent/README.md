# Agent 协作系统概述

本项目采用 **Vibe Agent 融合架构**，结合 Multi-Agent 协作系统和 Vibe Coding 方法论。

## 四角色模型

| 角色 | 职责 | 输出文件 |
|------|------|----------|
| 立法者 (Legislator) | 定义规范 | `factor_perception/spec.md` |
| 智库专家 (Knowledge Expert) | 维护知识 | `factor_perception/knowledge.md` |
| 执行官 (Executor) | 落地规范 | `factor_perception/README.md` + 代码 |
| 史官 (Historian) | 记录变更 | `factor_perception/changelog.md` |

## 上下文层次

```
1. CLAUDE.md          → AI行为准则
2. memory-bank/*      → 固定上下文 (项目目标、架构、技术栈)
3. docs/agent/*       → 角色定义
4. factor_perception/* → 模块工作区
```

## 触发规则

- `spec.md` 变更 → 通知执行官、史官
- `memory-bank/` 变更 → 通知所有 Agent
- 代码提交 → 通知史官

## 详细角色定义

参见:
- [立法者](legislator.md)
- [智库专家](knowledge-expert.md)
- [执行官](executor.md)
- [史官](historian.md)
